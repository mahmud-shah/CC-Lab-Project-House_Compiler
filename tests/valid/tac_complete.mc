int x;
int y;
int sum;
int remainder;
float avg;
bool found;
bool flag;
x = 10;
y = 3;
sum = 0;
found = false;
flag = true;
while (x > 0) {
    sum = sum + x;
    if (x == y) {
        found = true;
    }
    x = x - 1;
}
remainder = sum % y;
avg = sum;
if (found == true) {
    print sum;
    print avg;
} else {
    print remainder;
}
flag = !flag;
if (flag == false) {
    int inner;
    inner = sum + y;
    print inner;
}
print found;