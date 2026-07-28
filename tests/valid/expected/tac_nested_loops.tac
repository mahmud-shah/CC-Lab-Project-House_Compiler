; === Three Address Code: tests/valid/tac_nested_loops.mc ===

    i = 1
L1:
    t1 = i <= 3
    ifFalse t1 goto L2
    j = 1
L3:
    t2 = j <= 3
    ifFalse t2 goto L4
    t3 = i * j
    product = t3
    print product
    t4 = j + 1
    j = t4
    goto L3
L4:
    t5 = i + 1
    i = t5
    goto L1
L2:
