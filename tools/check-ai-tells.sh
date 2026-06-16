#!/usr/bin/env bash
# check-ai-tells.sh — static linter for AI writing patterns
# Usage: check-ai-tells.sh <file>
# Exit 0 = clean, 1 = issues found, 2 = usage error

set -euo pipefail

if [[ $# -lt 1 || ! -f "$1" ]]; then
  echo "Usage: check-ai-tells.sh <file>" >&2
  exit 2
fi

FILE="$1"
ISSUES=0

# Strip frontmatter and code blocks from input for prose checks
PROSE=$(awk '
  /^---$/ && NR==1 { in_front=1; next }
  /^---$/ && in_front { in_front=0; next }
  in_front { next }
  /^```/ { in_block=!in_block; next }
  !in_block { print }
' "$FILE")

flag() {
  local category="$1"
  local pattern="$2"
  local results
  results=$(echo "$PROSE" | grep -in "$pattern" 2>/dev/null || true)
  if [[ -n "$results" ]]; then
    echo "[$category]"
    while IFS= read -r line; do echo "  $line"; done <<< "$results"
    echo ""
    ISSUES=1
  fi
}

# Case-sensitive variant. The default `flag` uses `grep -in`, which
# treats `[A-Z]` as case-insensitive — that defeats checks that
# specifically look for capital letters (like title-case detection).
# S-11176: previously the title-case heading check ran via flag() and
# every sentence-case heading false-positived because `-i` made the
# upper-case class match any letter.
flag_cs() {
  local category="$1"
  local pattern="$2"
  local results
  results=$(echo "$PROSE" | grep -n "$pattern" 2>/dev/null || true)
  if [[ -n "$results" ]]; then
    echo "[$category]"
    while IFS= read -r line; do echo "  $line"; done <<< "$results"
    echo ""
    ISSUES=1
  fi
}

count_flag() {
  local category="$1"
  local pattern="$2"
  local threshold="$3"
  local count
  count=$(echo "$PROSE" | { grep -o "$pattern" 2>/dev/null || true; } | wc -l | tr -d ' ')
  if [[ "$count" -gt "$threshold" ]]; then
    echo "[$category] found $count in prose (threshold: $threshold)"
    echo ""
    ISSUES=1
  fi
}

echo "=== AI Tell Check: $(basename "$FILE") ==="
echo ""

# ── Negative parallelisms ─────────────────────────────────────────────────────
flag "NEGATIVE PARALLELISM (period form)" \
  "[Tt]hat's not .\+\. [Tt]hat's\|[Tt]his isn't .\+\. [Ii]t's\|[Ii]t's not .\+\. [Ii]t's\|[Nn]ot .\+\. [Ii]t's\|wasn't .\+\. [Ii]t was\|wasn't .\+\. [Tt]hat was\|weren't .\+\. [Tt]hey were\|didn't .\+\. [Ii]t was\|wasn't about .\+\. [Ii]t was"

flag "NEGATIVE PARALLELISM (em dash form)" \
  "^Not .\+ —\|[.] Not .\+ —\|[Ii]t's not .\+ —"

flag "NEGATIVE PARALLELISM (not just/only)" \
  "not just .\+ but\|not only .\+ but also"

# ── Transition filler at sentence start ──────────────────────────────────────
flag "TRANSITION FILLER" \
  "^Additionally,\|^Moreover,\|^Furthermore,\|^Notably,\|[.] Additionally,\|[.] Moreover,\|[.] Furthermore,\|[.] Notably,"

# ── Vocabulary giveaways — classic era ───────────────────────────────────────
flag "VOCABULARY (classic)" \
  "\bdelve\b\|\btapestry\b\|\bpivotal\b\|\bcrucial\b\|\bvibrant\b\|\bintricate\b\|\bmeticulous\b"

flag "VOCABULARY (classic)" \
  "\bfoster\b\|\bgarner\b\|\bbolster\b\|\btestament\b\|\benduring\b\|\bshowcase\b\|\binterplay\b"

flag "VOCABULARY (classic)" \
  "\bserves as\b\|\bstands as\b\|\bmarks a\b\|\brepresents a\b\|\bboasts a\b\|\balign with\b\|\bunderscore\b"

# ── Vocabulary giveaways — newer era ─────────────────────────────────────────
flag "VOCABULARY (newer)" \
  "\brobust\b\|\bgroundbreaking\b\|\brenowned\b\|\bnestled\b\|\bcomprehensive\b"

flag "VOCABULARY (newer)" \
  "diverse array\|in the heart of\|valuable insights\|meaningful impact\|significant contribution"

flag "VOCABULARY (newer)" \
  "\bboasts\b"

# ── Superficial -ing phrase endings ──────────────────────────────────────────
flag "SUPERFICIAL -ING PHRASE" \
  "highlighting its\|underscoring the\|reflecting broader\|showcasing the\|demonstrating the\|fostering a\|contributing to the\|symbolizing its\|emphasizing the importance"

# ── Didactic disclaimers ──────────────────────────────────────────────────────
flag "DIDACTIC DISCLAIMER" \
  "worth noting\|important to note\|important to remember\|crucial to note\|it is crucial\|it is important\|it should be noted"

# ── Vague attributions ────────────────────────────────────────────────────────
flag "VAGUE ATTRIBUTION" \
  "[Ee]xperts argue\|[Ee]xperts say\|[Rr]esearch shows\|[Ss]tudies suggest\|[Ii]ndustry reports\|[Oo]bservers have\|[Ss]ome critics"

# ── Outline-like conclusions ──────────────────────────────────────────────────
flag "OUTLINE CONCLUSION" \
  "[Dd]espite .\+ challenge\|[Dd]espite its success\|[Dd]espite these challenge\|[Ff]uture [Oo]utlook\|[Ff]uture [Pp]rospect\|[Ll]ooking ahead\|[Ii]n conclusion\|[Ii]n summary\|[Oo]verall,"

# ── Title case section headings ───────────────────────────────────────────────
# Detect ## headings where 3+ consecutive words are capitalized (title case).
# S-11176: must use flag_cs (case-sensitive) — the default flag() uses
# `grep -in` which makes `[A-Z]` match any letter, so this previously
# false-positived on every sentence-case heading.
flag_cs "TITLE CASE HEADING" \
  "^##\+ [A-Z][a-z]\+ [A-Z][a-z]\+ [A-Z]"

# ── Banned terms (customize for your own house style) ────────────────────────
# flag "BANNED TERM" "phrases\|you\|never\|want\|to\|see"

# ── Horizontal rule overuse (prose only, code blocks stripped) ───────────────
count_flag "HORIZONTAL RULE (AI section divider)" "^---$" 0

# ── Em dash overuse (prose only, code blocks stripped) ───────────────────────
count_flag "EM DASH OVERUSE" " — " 2

# ── Results ───────────────────────────────────────────────────────────────────
if [[ "$ISSUES" -eq 0 ]]; then
  echo "✅ No AI tells found."
  exit 0
else
  echo "❌ Fix the above before publishing."
  exit 1
fi
