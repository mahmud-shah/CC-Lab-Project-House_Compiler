; === Three Address Code: tests/valid/tac_nested_if.mc ===

    x = 5
    y = 10
    a = true
    b = false
    t1 = x > 0
    ifFalse t1 goto L1
    t2 = y > 0
    ifFalse t2 goto L3
    ifFalse a goto L5
    t4 = !b
    ifFalse t4 goto L5
    t3 = true
    goto L6
L5:
    t3 = false
L6:
    result = t3
    print result
    goto L4
L3:
    ifTrue a goto L7
    ifTrue b goto L7
    t5 = false
    goto L8
L7:
    t5 = true
L8:
    result = t5
    print result
L4:
    goto L2
L1:
    print x
L2:
