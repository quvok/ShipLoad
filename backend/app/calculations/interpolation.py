"""Small, guarded numerical primitives.

These utilities are not a vessel stability model. They deliberately refuse to
extrapolate because approved vessel tables define the supported calculation range.
"""
from bisect import bisect_left
from collections.abc import Sequence
import math


class TableRangeError(ValueError):
    """Raised when a query is outside a tabulated domain."""


class InvalidTableError(ValueError):
    """Raised when table points are malformed or ambiguous."""


def linear_interpolate(
    x: float,
    points: Sequence[tuple[float, float]],
) -> float:
    """Interpolate y at x from strictly increasing (x, y) points.

    Exact endpoints are accepted. Extrapolation, duplicate x coordinates,
    non-finite values and tables with fewer than two points are rejected.
    """
    if len(points) < 2:
        raise InvalidTableError("At least two table points are required")

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]

    if any(not _is_finite(value) for value in [x, *xs, *ys]):
        raise InvalidTableError("All coordinates and values must be finite")

    if any(right <= left for left, right in zip(xs, xs[1:])):
        raise InvalidTableError("Table x coordinates must be strictly increasing")

    if x < xs[0] or x > xs[-1]:
        raise TableRangeError(
            f"Query {x} is outside tabulated range [{xs[0]}, {xs[-1]}]"
        )

    index = bisect_left(xs, x)
    if index < len(xs) and xs[index] == x:
        return ys[index]

    left_x, left_y = points[index - 1]
    right_x, right_y = points[index]
    fraction = (x - left_x) / (right_x - left_x)
    return left_y + fraction * (right_y - left_y)


def _is_finite(value: float) -> bool:
    return math.isfinite(value)
