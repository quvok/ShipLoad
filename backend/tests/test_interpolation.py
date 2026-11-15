import pytest

from app.calculations.interpolation import (
    InvalidTableError,
    TableRangeError,
    linear_interpolate,
)


def test_interpolates_between_points() -> None:
    assert linear_interpolate(2.5, [(0.0, 10.0), (5.0, 20.0)]) == 15.0


def test_returns_exact_table_value() -> None:
    assert linear_interpolate(5.0, [(0.0, 10.0), (5.0, 20.0), (10.0, 30.0)]) == 20.0


def test_accepts_endpoints_but_does_not_extrapolate() -> None:
    points = [(1.0, 4.0), (3.0, 8.0)]
    assert linear_interpolate(1.0, points) == 4.0
    assert linear_interpolate(3.0, points) == 8.0
    with pytest.raises(TableRangeError):
        linear_interpolate(0.99, points)
    with pytest.raises(TableRangeError):
        linear_interpolate(3.01, points)


def test_rejects_duplicate_or_unsorted_coordinates() -> None:
    with pytest.raises(InvalidTableError):
        linear_interpolate(1.0, [(0.0, 1.0), (0.0, 2.0)])
    with pytest.raises(InvalidTableError):
        linear_interpolate(1.0, [(2.0, 2.0), (1.0, 1.0)])


def test_rejects_incomplete_and_non_finite_tables() -> None:
    with pytest.raises(InvalidTableError):
        linear_interpolate(1.0, [(1.0, 2.0)])
    with pytest.raises(InvalidTableError):
        linear_interpolate(float("nan"), [(0.0, 1.0), (2.0, 3.0)])
