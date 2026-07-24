/* exercises every token class, longest-match cases,
   and both comment styles */
int a; float pi; bool ok;      // declarations
a = 42; pi = 3.14; ok = false;
a = a % 7 * 2 / 1 + 0 - 5;
ok = a <= 1 || a >= 2 && !(a == 3) || a != 4 || a < 5 || a > 6;
if (ok) { print a; } else { print pi; }
while (ok) { a = a - 1; }
