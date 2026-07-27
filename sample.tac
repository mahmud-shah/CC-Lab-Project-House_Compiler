; === Three Address Code: examples/sample.mc ===

    x = 10
    y = 0
    flag = true
L1:
    t1 = x > 0
    ifFalse t1 goto L2
    t2 = y + x
    y = t2
    t3 = x - 1
    x = t3
    goto L1
L2:
    t4 = flag == true
    ifFalse t4 goto L3
    print y
    goto L4
L3:
    print x
L4:
