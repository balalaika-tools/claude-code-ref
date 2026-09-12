"""Behavioral regression checks for routing, XML integrity and icon portability."""
import copy
import io
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

from icon_assets import package, svg_bytes
from validate_drawio import validate

EXAMPLES = Path(__file__).resolve().parents[1] / 'assets/examples'


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.drawio'
        self.doc = ET.parse(EXAMPLES / 'aws-request-flow.drawio')

    def cell(self, name):
        return self.doc.find(f".//mxCell[@id='{name}']")

    def codes(self):
        self.doc.write(self.path)
        return {i['code'] for i in validate(self.path)}

    def restyle(self, cell, old, new):
        cell.set('style', cell.get('style').replace(old, new))

    def test_examples_pass(self):
        for p in EXAMPLES.glob('*.drawio'):
            self.assertEqual(validate(p), [], p)

    def test_icon_terminal_rejected(self):
        self.cell('flow-1').set('target', 'icon-1')
        self.assertIn('TERMINAL', self.codes())

    def test_boundary_heading_route_rejected_but_body_crossing_allowed(self):
        c = ET.SubElement(self.doc.find('.//root'), 'mxCell', id='test-boundary',
                          parent='1', vertex='1', value='Peer',
                          style='archRole=boundary;verticalAlign=top;align=left;fontSize=14;')
        g = ET.SubElement(c, 'mxGeometry', x='205', y='290', width='55', height='110')
        self.assertIn('ANNOTATION_ROUTE', self.codes())
        g.set('y', '200')
        g.set('height', '200')
        self.assertEqual(self.codes(), set())

    def test_boundary_heading_overlapping_card_rejected(self):
        g = self.cell('card-1').find('mxGeometry')
        c = ET.SubElement(self.doc.find('.//root'), 'mxCell', id='test-boundary',
                          parent='1', vertex='1', value='Peer account',
                          style='archRole=boundary;verticalAlign=top;align=left;fontSize=14;')
        ET.SubElement(c, 'mxGeometry', x=g.get('x'), y=g.get('y'), width='200', height='200')
        self.assertIn('OVERLAP', self.codes())

    def test_wrapped_boundary_heading_route_rejected(self):
        c = ET.SubElement(self.doc.find('.//root'), 'mxCell', id='test-boundary',
                          parent='1', vertex='1', value='External peer platform',
                          style='archRole=boundary;verticalAlign=top;align=left;fontSize=14;')
        ET.SubElement(c, 'mxGeometry', x='205', y='265', width='55', height='140')
        self.assertIn('ANNOTATION_ROUTE', self.codes())

    def test_floating_terminal_rejected(self):
        del self.cell('flow-1').attrib['target']
        self.assertIn('TERMINAL', self.codes())

    def test_card_anchor_inside_rejected(self):
        self.restyle(self.cell('flow-1'), 'entryX=0;', 'entryX=0.2;')
        self.assertIn('ANCHOR', self.codes())

    def test_inward_route_rejected(self):
        g = self.cell('flow-1').find('mxGeometry')
        a = ET.SubElement(g, 'Array', {'as': 'points'})
        ET.SubElement(a, 'mxPoint', x='100', y='305')
        self.assertIn('OUTWARD_STUB', self.codes())
        self.assertIn('CARD_ROUTE', self.codes())

    def test_autoroute_not_silently_passed(self):
        self.restyle(self.cell('flow-1'), 'edgeStyle=none;', 'edgeStyle=orthogonalEdgeStyle;')
        self.assertIn('UNVERIFIED_ROUTE', self.codes())

    def test_diagonal_rejected(self):
        self.restyle(self.cell('flow-1'), 'entryY=0.5;', 'entryY=0.6;')
        self.assertIn('ORTHOGONAL', self.codes())

    def test_intervening_card_rejected(self):
        c = copy.deepcopy(self.cell('card-1'))
        c.set('id', 'obstacle')
        g = c.find('mxGeometry')
        for k, v in dict(x='205', y='285', width='50', height='40').items():
            g.set(k, v)
        self.doc.find('.//root').append(c)
        self.assertIn('CARD_ROUTE', self.codes())

    def test_parallel_gap_rejected(self):
        c = copy.deepcopy(self.cell('flow-1'))
        c.set('id', 'parallel')
        self.restyle(c, 'exitY=0.5;', 'exitY=0.6;')
        self.restyle(c, 'entryY=0.5;', 'entryY=0.6;')
        self.doc.find('.//root').append(c)
        self.assertIn('LINE_GAP', self.codes())

    def test_orphan_legend_rejected(self):
        self.doc.find('.//root').remove(self.cell('badge-1'))
        self.assertIn('STEPS', self.codes())

    def test_standalone_header_icon_clearance(self):
        icon = copy.deepcopy(self.cell('icon-1'))
        icon.set('id', 'header-icon')
        icon.set('parent', '1')
        g = icon.find('mxGeometry')
        g.attrib.update(x='215', y='293', width='24', height='24')
        self.doc.find('.//root').append(icon)
        self.assertIn('ANNOTATION_ROUTE', self.codes())
        g.attrib.update(x='300', y='250')
        self.assertIn('OVERLAP', self.codes())
        g.attrib.update(x='215', y='180')
        self.assertEqual(self.codes(), set())

    def test_badge_nearer_wrong_flow_warns(self):
        geometry = self.cell('badge-1').find('mxGeometry')
        original = dict(geometry.attrib)
        geometry.attrib.update(self.cell('badge-2').find('mxGeometry').attrib)
        self.assertIn('BADGE_ASSOCIATION', self.codes())
        geometry.attrib.update(original)
        self.assertNotIn('BADGE_ASSOCIATION', self.codes())

    def test_badge_can_represent_any_branch_of_same_step(self):
        geometry = self.cell('badge-1').find('mxGeometry')
        geometry.attrib.update(self.cell('badge-2').find('mxGeometry').attrib)
        self.restyle(self.cell('flow-2'), 'archStep=2;', 'archStep=1;')
        self.doc.find('.//root').remove(self.cell('badge-2'))
        self.assertNotIn('BADGE_ASSOCIATION', self.codes())

    def test_visible_legend_number_rejected(self):
        self.cell('legend-badge-1').set('value', '9')
        self.assertIn('BADGE_NUMBER', self.codes())

    def test_missing_sidebar_badge_rejected(self):
        self.doc.find('.//root').remove(self.cell('legend-badge-1'))
        self.assertIn('STEPS', self.codes())

    def test_inconsistent_badge_graphic_rejected(self):
        self.restyle(self.cell('legend-badge-1'), 'strokeColor=#000000;', 'strokeColor=#005A87;')
        self.assertIn('BADGE_STYLE', self.codes())

    def test_neutral_aws_glyph_rejected(self):
        self.doc.find('.//mxGraphModel').set('archProvider', 'neutral')
        self.assertIn('NEUTRAL_PROVIDER', self.codes())

    def test_remote_image_rejected(self):
        self.cell('icon-1').set('style', self.cell('icon-1').get('style') + 'image=https://example.org/icon.svg;')
        self.assertIn('IMAGE_PORTABILITY', self.codes())

    def test_duplicate_id_rejected(self):
        self.cell('card-2').set('id', 'card-1')
        self.assertIn('IDS', self.codes())

    def test_nonfinite_geometry_rejected(self):
        self.cell('card-1').find('mxGeometry').set('x', 'NaN')
        self.assertIn('GEOMETRY', self.codes())

    def test_malformed_xml_rejected(self):
        self.path.write_text('<mxfile>')
        self.assertEqual(validate(self.path)[0]['code'], 'XML')

    def test_legend_optout(self):
        self.doc.find('.//mxGraphModel').set('archLegend', '0')
        r = self.doc.find('.//root')
        for c in list(r):
            if c.get('id', '').startswith(('legend', 'badge')):
                r.remove(c)
        self.assertEqual(self.codes(), set())

    def test_nested_icon_bounds_rejected(self):
        self.cell('icon-1').find('mxGeometry').set('x', '130')
        self.assertIn('CHILD_BOUNDS', self.codes())

    def test_svg_embedding_input(self):
        p = Path(self.temp.name) / 'brand.svg'
        p.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0 L10 10"/></svg>')
        self.assertIn(b'viewBox', svg_bytes(p))
        p.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
        with self.assertRaises(ValueError):
            svg_bytes(p)

    def test_svg_external_reference_rejected(self):
        p = Path(self.temp.name) / 'brand.svg'
        p.write_text('<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.org/logo.svg"/></svg>')
        with self.assertRaises(ValueError):
            svg_bytes(p)

    def test_package_cache_and_traversal(self):
        def response(member):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w') as z:
                z.writestr(member, '<svg/>')
            result = io.BytesIO(buf.getvalue())
            result.url = 'https://example.org/icons.zip'
            return result
        destination = Path(self.temp.name)/'cache'
        with patch('urllib.request.urlopen', return_value=response('icons/service.svg')):
            package('https://example.org/icons.zip', destination)
        self.assertTrue((destination/'package.json').exists())
        self.assertTrue((destination/'icons/service.svg').exists())
        with patch('urllib.request.urlopen', return_value=response('../escape.svg')):
            with self.assertRaises(ValueError):
                package('https://example.org/icons.zip', Path(self.temp.name)/'bad-cache')
        self.assertFalse((Path(self.temp.name)/'escape.svg').exists())


if __name__ == '__main__':
    unittest.main()
