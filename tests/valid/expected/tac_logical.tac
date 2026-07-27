; === Three Address Code: tests/valid/tac_logical.mc ===

    x = 5
    y = 3
    t2 = x > 0
    ifFalse t2 goto L1
    t3 = y < 10
    ifFalse t3 goto L1
    t1 = true
    goto L2
L1:
    t1 = false
L2:
    result = t1
    t4 = result == true
    ifFalse t4 goto L3
    print x
L3:
    t6 = x > 10
    ifTrue t6 goto L4
    t7 = y < 10
    ifTrue t7 goto L4
    t5 = false
    goto L5
L4:
    t5 = true
L5:
    result = t5
    print result
