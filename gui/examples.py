from __future__ import annotations

from collections import OrderedDict


EXAMPLES: OrderedDict[str, str] = OrderedDict(
    {
        "Manual sample": """int x;
int y;
bool flag;

x = 10;
y = 0;
flag = true;

while (x > 0) {
    y = y + x;
    x = x - 1;
}

if (flag == true) {
    print y;
} else {
    print x;
}
""",
        "Expressions and loop": """int i;
int total;
i = 0;
total = 0;

while (i < 10) {
    total = total + i * 2;
    i = i + 1;
}

print total;
""",
        "Nested scopes": """int value;
value = 10;

{
    float average;
    average = value / 2.0;
    print average;
}

if (value >= 10) {
    bool accepted;
    accepted = true;
    print accepted;
} else {
    value = 0;
}
""",
        "Error showcase": """int count;
count = missing + 1;

if (count > 0) {
    int count;
    count = 4
}

print count;
""",
    }
)


DEFAULT_EXAMPLE = next(iter(EXAMPLES))
