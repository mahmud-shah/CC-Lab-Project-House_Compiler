; === Three Address Code: tests/valid/tac_while.mc ===

    i = 1
    sum = 0
L1:
    t1 = i <= 5
    ifFalse t1 goto L2
    t2 = sum + i
    sum = t2
    t3 = i + 1
    i = t3
    goto L1
L2:
    print sum
