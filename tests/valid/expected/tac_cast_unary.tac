; === Three Address Code: tests/valid/tac_cast_unary.mc ===

    x = 7
    t1 = (float) x
    f = t1
    flag = true
    t2 = !flag
    flag = t2
    t3 = -x
    x = t3
    print f
    print flag
    print x
