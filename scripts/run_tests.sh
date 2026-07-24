#!/usr/bin/env bash
# ============================================================================
# MiniLang regression runner.
#   - valid programs must exit 0 and produce no diagnostics
#   - invalid programs must exit 1 and their diagnostics must match the
#     frozen golden output in the sibling expected/ directory
# Grows automatically as test files are added; no registration needed.
# ============================================================================
set -u
MCC=build/mcc
pass=0; fail=0

check() {  # $1 = description, $2 = ok flag (0 ok)
  if [ "$2" -eq 0 ]; then pass=$((pass+1)); printf 'PASS  %s\n' "$1"
  else fail=$((fail+1)); printf 'FAIL  %s\n' "$1"; fi
}

for f in tests/valid/*.mc examples/*.mc; do
  [ -e "$f" ] || continue
  "$MCC" "$f" > /dev/null 2> /tmp/err.$$
  ok=$?
  [ -s /tmp/err.$$ ] && ok=1
  check "valid    $f (exit 0, no diagnostics)" $ok
done

for dir in tests/invalid/lexical tests/invalid/syntax tests/invalid/semantic; do
  for f in "$dir"/*.mc; do
    [ -e "$f" ] || continue
    base=$(basename "$f" .mc)
    golden="$dir/expected/$base.err"
    "$MCC" "$f" > /dev/null 2> /tmp/err.$$
    rc=$?
    ok=1
    if [ $rc -eq 1 ] && [ -f "$golden" ] && diff -q /tmp/err.$$ "$golden" > /dev/null; then ok=0; fi
    check "invalid  $f (exit 1, diagnostics match golden)" $ok
  done
done

rm -f /tmp/err.$$
echo "----------------------------------------"
echo "$pass passed, $fail failed"
[ $fail -eq 0 ]
