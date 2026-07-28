; === Three Address Code: tests/valid/tac_complete.mc ===

    x = 10
    y = 3
    sum = 0
    found = false
    flag = true
L1:
    t1 = x > 0
    ifFalse t1 goto L2
    t2 = sum + x
    sum = t2
    t3 = x == y
    ifFalse t3 goto L3
    found = true
L3:
    t4 = x - 1
    x = t4
    goto L1
L2:
    t5 = sum % y
    remainder = t5
    t6 = (float) sum
    avg = t6
    t7 = found == true
    ifFalse t7 goto L4
    print sum
    print avg
    goto L5
L4:
    print remainder
L5:
    t8 = !flag
    flag = t8
    t9 = flag == false
    ifFalse t9 goto L6
    t10 = sum + y
    inner = t10
    print inner
L6:
    print found
