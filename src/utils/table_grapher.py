__all__ = ["table2graph"]

import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from scipy.interpolate import make_interp_spline
from pathlib import Path

from ..logger import get_logger, log_exceptions

logger = get_logger(__name__)

matplotlib.use("Agg")
plt.rcParams["font.sans-serif"] = ["SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False


def _load_data(data_path: Path) -> tuple[pd.DataFrame, str, list[str]]:
    try:
        data = pd.read_csv(data_path)
    except Exception as e:
        logger.error("Failed to read table: %s", e)
        raise

    cols = data.columns.tolist()
    x_var, *y_vars = cols
    data = data.sort_values(by=x_var) if y_vars else data
    logger.info("Table data loaded: %d rows, %d variables total", len(data), len(cols))
    logger.debug("x variable: %s, y variables: %s", x_var, y_vars)
    return data, x_var, y_vars


def _plot_direct(ax: Axes, x_data: np.ndarray, y_data: np.ndarray, var_name: str) -> None:
    ax.plot(x_data, y_data, "o-", linewidth=2, markersize=6, label=var_name)


def _plot_smooth(ax: Axes, x_data: np.ndarray, y_data: np.ndarray, var_name: str) -> None:
    x_new = np.linspace(x_data.min(), x_data.max(), 300)
    y_smooth = make_interp_spline(x_data, y_data, k=3)(x_new)
    ax.scatter(x_data, y_data, s=30)
    ax.plot(x_new, y_smooth, "-", linewidth=2, label=var_name)


def _plot_linear(ax: Axes, x_data: np.ndarray, y_data: np.ndarray, var_name: str) -> None:
    z = np.polyfit(x_data, y_data, 1)
    ax.scatter(x_data, y_data, s=30)
    ax.plot(x_data, np.poly1d(z)(x_data), "--", linewidth=2, label=f"{var_name} (fit: y={z[0]:.2f}x+{z[1]:.2f})")


_LINE_PLOT_FUNCS = {
    "direct": _plot_direct,
    "smooth": _plot_smooth,
    "linear": _plot_linear,
}


def _plot_single_line(ax: Axes, x_data: np.ndarray, y_data: np.ndarray, var_name: str, mode: str) -> None:
    logger.info("Plotting %s line, mode: %s", var_name, mode)
    plot_fn = _LINE_PLOT_FUNCS.get(mode)
    if plot_fn is None:
        logger.error("Unknown plot mode: %s", mode)
        raise ValueError(f"Unknown plot mode: {mode!r}, available: {list(_LINE_PLOT_FUNCS)}")
    plot_fn(ax, x_data, y_data, var_name)
    logger.info("%s curve plotted", var_name)


def _setup_axes(ax: Axes, x_var: str, y_label: str) -> None:
    ax.set_xlabel(x_var, fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    if ax.get_legend_handles_labels()[0]:
        ax.legend()
    ax.grid(True)
    plt.tight_layout()


def _render_histogram(data: pd.DataFrame, x_var: str) -> list[tuple[plt.Figure, str]]:
    x_data = data[x_var].dropna().values
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(x_data, bins="auto", alpha=0.7, edgecolor="black", label=x_var)
    ax.set_xlabel(x_var, fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()

    logger.info("Histogram rendered for %s", x_var)
    return [(fig, "hist")]


def _render_separate_plot(data: pd.DataFrame, x_var: str, y_vars: list[str], mode: str) -> list[tuple[plt.Figure, str]]:
    x_data = data[x_var].values

    figs = []
    for y_var in y_vars:
        fig, ax = plt.subplots(figsize=(10, 6))
        _plot_single_line(ax, x_data, data[y_var].values, y_var, mode)
        _setup_axes(ax, x_var, y_var)
        figs.append((fig, y_var))
        logger.info("%s - %s rendered", y_var, x_var)
    return figs


def _render_combined_plot(data: pd.DataFrame, x_var: str, y_vars: list[str], mode: str) -> list[tuple[plt.Figure, str]]:
    x_data = data[x_var].values
    fig, ax = plt.subplots(figsize=(10, 6))
    for y_var in y_vars:
        logger.debug("Adding %s to combined plot", y_var)
        _plot_single_line(ax, x_data, data[y_var].values, y_var, mode)
    _setup_axes(ax, x_var, "values")
    logger.info("Combined plot rendered")
    return [(fig, "combined")]


def _render_plot(data: pd.DataFrame, x_var: str, y_vars: list[str], mode: str, plot_together: bool) -> list[tuple[plt.Figure, str]]:
    if not y_vars:
        return _render_histogram(data, x_var)

    plot_fn = _render_combined_plot if plot_together else _render_separate_plot
    return plot_fn(data, x_var, y_vars, mode)


def _save_figures(data_path: Path, figs: list[tuple[plt.Figure, str]], mode: str) -> list[Path]:
    paths = []
    for fig, var_name in figs:
        fig_name = f"{data_path.stem}_hist.png" if var_name == "hist" else f"{data_path.stem}_{mode}_{var_name}.png"
        fig_path = data_path.with_name(fig_name)

        fig.savefig(fig_path, dpi=300)
        paths.append(fig_path)
        logger.info("Image saved to: %s", fig_path.resolve())
        plt.close(fig)
    return paths


@log_exceptions()
def table2graph(data_path: Path, *, mode: str = "smooth", plot_together: bool = False) -> list[Path]:
    """Plot data from a CSV table.

    If the CSV contains multiple columns, it plots line graphs (direct, smooth, or linear).
    If the CSV contains only one column, it plots a frequency distribution histogram.

    Parameters:
        data_path: Path to the CSV file.
        mode: Plotting mode ("direct", "smooth", "linear"). Ignored for single-column CSVs.
        plot_together: Whether to plot all y-variables in a single figure.

    Returns:
        List of paths to generated PNG images.
    """
    logger.info("Processing table: %s, mode: %s, combined: %s", data_path.resolve(), mode, plot_together)
    data, x_var, y_vars = _load_data(data_path)

    figs = _render_plot(data, x_var, y_vars, mode, plot_together)
    paths = _save_figures(data_path, figs, mode)
    logger.info("All images processed")
    return paths
