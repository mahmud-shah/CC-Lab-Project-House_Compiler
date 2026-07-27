; === Three Address Code: tests/valid/tac_if_else.mc ===

    x = 10
    flag = true
    t1 = flag == true
    ifFalse t1 goto L1
    t2 = x + 1
    x = t2
    print x
    goto L2
L1:
    t3 = x - 1
    x = t3
    print x
L2:
