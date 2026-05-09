"""Data generator — generate truncated random datasets with exact statistics."""

__all__ = ["generate_data", "summary"]

import numpy as np
from pathlib import Path
from typing import Any

from ..logger import get_logger, log_exceptions

logger = get_logger(__name__)


def _sample_normal(n: int, std_target: float, width: float, rng: np.random.Generator) -> np.ndarray:
    """Rejection-samples from a truncated standard normal distribution."""
    R = (width / 2.0) / std_target
    accepted: list[float] = []
    while len(accepted) < n:
        x = rng.normal(0.0, 1.0)
        if -R <= x <= R:
            accepted.append(x)
    return np.array(accepted, dtype=np.float64)


def _sample_uniform(n: int, std_target: float, width: float, rng: np.random.Generator) -> np.ndarray:
    """Samples directly from a uniform distribution bounded by ±R."""
    R = (width / 2.0) / std_target
    return rng.uniform(-R, R, size=n)


_SAMPLER_FUNCS = {
    "normal": _sample_normal,
    "uniform": _sample_uniform,
}


def _round_data(data: np.ndarray, decimals: int | None) -> np.ndarray:
    return np.round(data, decimals) if decimals is not None else data


def _orthogonal_noise(x: np.ndarray, x_mean: float, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    n = len(x)
    E_raw = rng.normal(0.0, 1.0, size=n)
    E1 = E_raw - E_raw.mean()
    dx = x - x_mean
    m_err = np.dot(dx, E1) / np.dot(dx, dx)
    E_perfect = E1 - m_err * dx
    return E_perfect, E_perfect.var(ddof=0)


def _export_csv(data: np.ndarray, path: str | Path, fmt: str = "%.10g") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "x,y" if data.ndim == 2 else "x"
    np.savetxt(path, data, delimiter=",", header=header, comments="", fmt=fmt)
    logger.info("Data exported to: %s", path.resolve())
    return path.resolve()


def summary(data: np.ndarray) -> str:
    def _format_dim(d: np.ndarray, name: str = "") -> str:
        return f"{name} mean={d.mean():.6f}, std={d.std(ddof=0):.6f}, var={d.var(ddof=0):.6f}, range=[{d.min():.6f}, {d.max():.6f}]"

    if data.ndim == 2:
        return f"Generated {len(data)} points (2-D):\n  X: {_format_dim(data[:, 0])}\n  Y: {_format_dim(data[:, 1])}"
    return f"Generated {len(data)} points: {_format_dim(data)}"


def _generate_random(
    n: int,
    mean: float,
    width: float,
    variance: float,
    distribution: str,
    decimals: int | None,
    rng: np.random.Generator,
) -> np.ndarray:
    std_target = np.sqrt(variance)

    sampler = _SAMPLER_FUNCS.get(distribution)
    if sampler is None:
        raise ValueError(f"Unknown distribution: {distribution!r}. Available: {sorted(_SAMPLER_FUNCS)}")
    data = sampler(n=n, std_target=std_target, width=width, rng=rng)

    M_sample, S_sample = data.mean(), data.std(ddof=0)
    data_std = data if S_sample == 0 else (data - M_sample) / S_sample
    return _round_data(data_std * std_target + mean, decimals)


def _generate_linear(
    x: np.ndarray,
    decimals: int | None,
    rng: np.random.Generator,
    *,
    slope: float,
    intercept: float,
    r_squared: float,
    decimals_y: int | None = None,
) -> np.ndarray:
    if not 0 < r_squared <= 1:
        raise ValueError(f"r_squared must be in (0, 1], got {r_squared}")

    E_perfect, E_var = _orthogonal_noise(x, x.mean(), rng)

    var_y_ideal = slope * slope * x.var(ddof=0)
    k = np.sqrt(var_y_ideal * (1.0 - r_squared) / (E_var * r_squared))
    y_raw = slope * x + intercept + k * E_perfect

    dec_y = decimals if decimals_y is None else decimals_y
    y = _round_data(y_raw, dec_y)
    return np.column_stack((x, y))


@log_exceptions()
def generate_data(
    n: int,
    mean: float,
    width: float,
    variance: float,
    *,
    distribution: str = "normal",
    decimals: int | None = 0,
    rng: np.random.Generator | None = None,
    csv_path: str | Path | None = None,
    dimension: int = 1,
    **kwargs: Any,
) -> np.ndarray:
    """Generate a dataset with the specified statistics.

    Uses the algorithm described in ``docs/algorithm.md``.
    The returned array has *exactly* the requested mean and variance
    before rounding.

    When *dimension* is 2, also generates *Y = slope · X + intercept + noise*
    with an exact coefficient of determination *r_squared*.

    Parameters:
        n: Number of data points to generate (must be > 1).
        mean: Target arithmetic mean.
        width: Total range width of the output data (must be > 0).
        variance: Target variance.
        distribution: Name of a registered sampler (e.g. ``"normal"``,
                      ``"uniform"``). See ``_SAMPLER_FUNCS``.
        decimals: Decimal places for rounding (``0`` = integers,
                  ``None`` = no rounding).
        rng: Optional NumPy random generator.
        csv_path: Export path for the CSV file (header ``"x"``
                  for 1-D, ``"x,y"`` for 2-D). ``None`` (default) skips export.
        dimension (int): ``1`` (default) for a 1-D array; ``2`` for a 2-D array
                         with columns ``(X, Y)``.
        slope (float): Linear coefficient *a* for Y generation (2-D only).
        intercept (float): Linear intercept *b* for Y generation (2-D only).
        r_squared (float): Target *R²* in *(0, 1]* for Y generation (2-D only).
        decimals_y (int | None): Decimal places for rounding Y (2-D only). ``None``
                                (default) uses the same value as *decimals*.

    Returns:
        NumPy array of shape ``(n,)`` for 1-D or ``(n, 2)`` for 2-D.
    """
    if n <= 1:
        raise ValueError(f"n must be > 1, got {n}")
    if width <= 0:
        raise ValueError(f"width must be > 0, got {width}")
    if variance <= 0:
        raise ValueError(f"variance must be positive, got {variance}")

    rng = rng or np.random.default_rng()
    x = _generate_random(n, mean, width, variance, distribution, decimals, rng)
    result = _generate_linear(x, decimals, rng, **kwargs) if dimension == 2 else x

    if csv_path is not None:
        _export_csv(result, csv_path)

    logger.info("%s", summary(result))
    return result
