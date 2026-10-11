import pytest
from calculator.calc import add, divide, multiply, subtract


def test_add() -> None:
    assert add(2.0, 3.0) == 5.0
    assert add(-1.0, 1.0) == 0.0


def test_subtract() -> None:
    assert subtract(5.0, 2.0) == 3.0


def test_multiply() -> None:
    assert multiply(3.0, 4.0) == 12.0


def test_divide() -> None:
    assert divide(10.0, 2.0) == 5.0


def test_divide_by_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        divide(5.0, 0.0)
