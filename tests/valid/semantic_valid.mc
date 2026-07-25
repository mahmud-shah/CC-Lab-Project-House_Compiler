int x;
int y;
float f;
bool flag;
x = 10;
y = 3;
f = 3.14;
flag = true;
f = x;
x = x + y;
x = x - y;
x = x * y;
x = x / y;
x = x % y;
f = f + x;
flag = x > y;
flag = x < y;
flag = x >= y;
flag = x <= y;
flag = flag == true;
flag = flag != false;
flag = flag && true;
flag = flag || false;
flag = !flag;
if (flag == true) {
    int inner;
    inner = x + y;
    print inner;
} else {
    print y;
}
while (x > 0) {
    x = x - 1;
}
print f;
