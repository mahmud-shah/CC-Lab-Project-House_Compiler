int a;
float b;
bool c;
a = 5;
b = 3.14;
c = true;
if (c == true) {
    int inner1;
    inner1 = a;
    {
        bool deep;
        deep = false;
    }
}
while (a > 0) {
    int counter;
    counter = a;
    a = a - 1;
}
print a;