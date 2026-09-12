#!/usr/bin/env python3
"""Cache an SVG package, register provenance, or emit a draw.io embedded image URI."""
import argparse
import base64
import hashlib
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MAX_DOWNLOAD = 150 * 1024 * 1024
MAX_EXPANDED = 300 * 1024 * 1024


def stamp():
    return datetime.now(timezone.utc).isoformat()


def svg_bytes(path):
    raw = Path(path).read_bytes()
    if len(raw) > 5*1024*1024 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('SVG too large or contains DTD/entities')
    root = ET.fromstring(raw)
    if root.tag.rsplit('}', 1)[-1] != 'svg':
        raise ValueError('Not an SVG')
    allowed = {'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon',
               'defs', 'linearGradient', 'radialGradient', 'stop', 'clipPath', 'mask', 'title', 'desc', 'use'}
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] not in allowed:
            raise ValueError('Unsupported SVG element: ' + node.tag)
        for key, value in node.attrib.items():
            key = key.rsplit('}', 1)[-1].lower()
            if key.startswith('on') or key == 'style' or (key == 'href' and not value.startswith('#')):
                raise ValueError('External/active or unsupported SVG attribute')
            if re.search(r'url\(\s*["\']?(?!#)', value, re.I) and 'url(' in value.lower():
                # Only exact local fragment paint references are supported.
                if not re.fullmatch(r'url\(#[\w.-]+\)', value):
                    raise ValueError('External or unsupported SVG paint reference')
    return raw


def package(url, destination):
    if not url.startswith('https://'):
        raise ValueError('Package URL must be HTTPS')
    if destination.exists():
        raise ValueError('Destination already exists; reuse cache or choose a new directory')
    with urllib.request.urlopen(url, timeout=60) as response:
        if not response.url.startswith('https://'):
            raise ValueError('Redirect left HTTPS')
        data = response.read(MAX_DOWNLOAD+1)
    if len(data) > MAX_DOWNLOAD:
        raise ValueError('Package exceeds download limit')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = [i for i in archive.infolist() if i.filename.lower().endswith('.svg') and not i.is_dir()]
        if not entries or sum(i.file_size for i in entries) > MAX_EXPANDED or len(entries) > 20000:
            raise ValueError('Empty or oversized SVG package')
        seen = set()
        for entry in entries:
            p = PurePosixPath(entry.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in entry.filename or ':' in entry.filename or p in seen:
                raise ValueError('Unsafe/duplicate archive member')
            seen.add(p)
        destination.mkdir(parents=True)
        for entry in entries:
            out = destination / entry.filename
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(archive.read(entry))
    (destination/'package.json').write_text(json.dumps(dict(source=url, retrieved=stamp(), sha256=hashlib.sha256(data).hexdigest(), svg_count=len(entries)), indent=2)+'\n')
    return f'Cached {len(entries)} SVGs in {destination}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('package')
    p.add_argument('url')
    p.add_argument('destination', type=Path)
    p = sub.add_parser('register')
    p.add_argument('svg', type=Path)
    p.add_argument('--name', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--license-note', required=True)
    p.add_argument('--catalog', required=True, type=Path)
    p = sub.add_parser('embed')
    p.add_argument('svg', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'package':
            print(package(args.url, args.destination))
        else:
            raw = svg_bytes(args.svg)
            if args.command == 'embed':
                args.output.write_text('data:image/svg+xml,' + base64.b64encode(raw).decode() + '\n')
                print(args.output)
            else:
                import os
                catalog = json.loads(args.catalog.read_text()) if args.catalog.exists() else {}
                catalog[args.name] = dict(path=os.path.relpath(args.svg.resolve(), args.catalog.parent.resolve()),
                                          source=args.source, registered=stamp(), sha256=hashlib.sha256(raw).hexdigest(),
                                          license_note=args.license_note)
                args.catalog.parent.mkdir(parents=True, exist_ok=True)
                args.catalog.write_text(json.dumps(catalog, indent=2)+'\n')
                print(args.catalog)
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
        print(f'Icon asset error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
