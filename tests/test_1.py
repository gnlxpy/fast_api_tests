import pytest

def multiply(x, y):
    if x < 100 and y > 3:
        print(z := x * y)
    else:
        print(z := 0)
    return z

@pytest.mark.parametrize('x, y, expected', [
    (2, 6, 12),
    (10, 4, 40),
    (101, 4, 404),
    (3, 2, 6)
])
def test_multiply(x, y , expected):
    assert multiply(x, y) == expected
