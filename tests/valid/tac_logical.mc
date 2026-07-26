int x;
int y;
bool result;
x = 5;
y = 3;
result = x > 0 && y < 10;
if (result == true) {
    print x;
}
result = x > 10 || y < 10;
print result;