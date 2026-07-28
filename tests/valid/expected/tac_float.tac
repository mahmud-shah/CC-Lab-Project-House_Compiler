; === Three Address Code: tests/valid/tac_float.mc ===

    n = 4
    x = 3.14
    y = 2.71
    t1 = x + y
    result = t1
    t2 = result * x
    result = t2
    t3 = (float) n
    x = t3
    print result
    print x
