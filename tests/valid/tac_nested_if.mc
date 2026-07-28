int x;
int y;
bool a;
bool b;
bool result;
x = 5;
y = 10;
a = true;
b = false;
if (x > 0) {
    if (y > 0) {
        result = a && !b;
        print result;
    } else {
        result = a || b;
        print result;
    }
} else {
    print x;
}