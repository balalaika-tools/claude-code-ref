#!/usr/bin/env bash
# Guards against drift between the copies of the note-maker and note-reviewer skills.
#
# Layout: each skill is self-contained — it carries the house style at
# references/how-we-write-notes.md and reaches it by that relative path, so nothing depends
# on where the skill is installed. Three trees hold a copy, and all three are byte-identical:
#
#   resources/.claude/skills/   canonical (edit here)
#   resources/.agents/skills/   Codex mirror
#   .claude/skills/             this project's active install
#
# Usage: scripts/check-note-skills-sync.sh    (run from anywhere; exits non-zero on drift)

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

CANON_TREE="resources/.claude/skills"
MIRRORS=("resources/.agents/skills" ".claude/skills")
SKILLS=(note-maker note-reviewer)
STYLE="references/how-we-write-notes.md"

fail=0
note() { printf '  %-6s %s\n' "$1" "$2"; }

# --- 1. Each mirror is a byte-for-byte copy of the canonical skill directory -------------
for skill in "${SKILLS[@]}"; do
  echo "$skill/ (whole directory)"
  canon="$CANON_TREE/$skill"
  if [[ ! -d $canon ]]; then note FAIL "$canon — missing"; fail=1; continue; fi
  for tree in "${MIRRORS[@]}"; do
    target="$tree/$skill"
    if [[ ! -d $target ]]; then note FAIL "$target — missing"; fail=1; continue; fi
    if out=$(diff -r -x '.DS_Store' "$canon" "$target" 2>&1) && [[ -z $out ]]; then
      note ok "$target"
    else
      note DRIFT "$target"
      printf '%s\n' "$out" | sed 's/^/           /' | head -12
      fail=1
    fi
  done
done

# --- 2. The house style is one document, not two that happen to share a name -------------
# Both skills carry it; if they disagree, notes get audited against a standard they weren't
# written to — the exact failure this layout exists to prevent.
echo "house style identical across skills"
ref_canon="$CANON_TREE/${SKILLS[0]}/$STYLE"
if [[ ! -f $ref_canon ]]; then
  note FAIL "$ref_canon — missing"; fail=1
else
  while IFS= read -r f; do
    [[ $f == "$ref_canon" ]] && continue
    if diff -q "$ref_canon" "$f" >/dev/null 2>&1; then note ok "$f"; else note DRIFT "$f"; fail=1; fi
  done < <(find . -path ./.git -prune -o -name 'how-we-write-notes.md' -print | sed 's|^\./||' | sort)
fi

# --- 3. Every skill is self-contained: it ships the style and points at it correctly -----
echo "self-containment"
for tree in "$CANON_TREE" "${MIRRORS[@]}"; do
  for skill in "${SKILLS[@]}"; do
    d="$tree/$skill"
    [[ -d $d ]] || continue
    [[ -f "$d/$STYLE" ]] || { note FAIL "$d — no $STYLE"; fail=1; }
    # Every pointer must be the plain in-skill path — an escaping ../ breaks the skill
    # the moment it's installed anywhere else, which is the bug this layout retired.
    pointers=$(grep -o '[^`]*how-we-write-notes[^`]*\.md' "$d/SKILL.md" 2>/dev/null | sort -u)
    if [[ -z $pointers ]]; then
      note FAIL "$d/SKILL.md — never references the house style"; fail=1
    elif bad=$(printf '%s\n' "$pointers" | grep -v "^$STYLE\$") && [[ -n $bad ]]; then
      note FAIL "$d/SKILL.md — pointer must be plain '$STYLE', found: $(printf '%s' "$bad" | tr '\n' ' ')"; fail=1
    else
      note ok "$d"
    fi
  done
done

echo
if (( fail )); then
  echo "DRIFT DETECTED — re-sync the mirrors from the canonical tree:"
  for skill in "${SKILLS[@]}"; do
    for tree in "${MIRRORS[@]}"; do
      echo "  rsync -a --delete $CANON_TREE/$skill/ $tree/$skill/"
    done
  done
  exit 1
fi
echo "note-maker and note-reviewer are in sync across all three trees."
