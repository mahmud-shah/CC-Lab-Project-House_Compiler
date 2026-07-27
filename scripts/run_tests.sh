set -u
MCC=build/mcc
pass=0; fail=0

check() {
    if [ "$2" -eq 0 ]; then
        pass=$((pass+1)); printf 'PASS  %s\n' "$1"
    else
        fail=$((fail+1)); printf 'FAIL  %s\n' "$1"
    fi
}

# Valid programs:
for f in tests/valid/*.mc examples/*.mc; do
    [ -e "$f" ] || continue
    "$MCC" "$f" > /dev/null 2> /tmp/err.$$
    ok=$?
    [ -s /tmp/err.$$ ] && ok=1
    check "valid    $f" $ok
done

# Invalid programs:
for dir in tests/invalid/lexical tests/invalid/syntax tests/invalid/semantic; do
    for f in "$dir"/*.mc; do
        [ -e "$f" ] || continue
        base=$(basename "$f" .mc)
        golden="$dir/expected/$base.err"
        "$MCC" "$f" > /dev/null 2> /tmp/err.$$
        rc=$?
        ok=1
        if [ $rc -eq 1 ] && [ -f "$golden" ] && \
           diff -q /tmp/err.$$ "$golden" > /dev/null 2>&1; then
            ok=0
        fi
        check "invalid  $f" $ok
    done
done

# TAC golden output check
for f in tests/valid/tac_*.mc; do
    [ -e "$f" ] || continue
    base=$(basename "$f" .mc)
    golden="tests/valid/expected/$base.tac"
    "$MCC" "$f" --tac > /tmp/tac.$$ 2>/dev/null
    ok=1
    if [ -f "$golden" ] && diff -q /tmp/tac.$$ "$golden" > /dev/null 2>&1; then
        ok=0
    fi
    check "tac      $f" $ok
done

rm -f /tmp/err.$$ /tmp/tac.$$
echo "----------------------------------------"
echo "$pass passed, $fail failed"
[ $fail -eq 0 ]
