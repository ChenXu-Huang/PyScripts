import pytest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from unittest.mock import patch, MagicMock
from matplotlib.axes import Axes

import src.utils.table_grapher as tg


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame({
        "theta": [1.0, 2.0, 3.0, 4.0],
        "C1": [1.0, 4.0, 9.0, 16.0],
        "C2": [1.0, 8.0, 27.0, 64.0],
    })
    file_path = tmp_path / "test_data.csv"
    df.to_csv(file_path, index=False)
    return file_path


@pytest.fixture()
def single_col_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame({"value": [1.2, 2.5, 3.8, 4.1, 2.3, 5.0, 3.3, 1.8]})
    file_path = tmp_path / "single_col.csv"
    df.to_csv(file_path, index=False)
    return file_path


@pytest.fixture()
def sample_data() -> tuple[pd.DataFrame, str, list[str]]:
    df = pd.DataFrame({
        "theta": [1.0, 2.0, 3.0, 4.0],
        "C1": [1.0, 4.0, 9.0, 16.0],
        "C2": [1.0, 8.0, 27.0, 64.0],
    })
    return df, "theta", ["C1", "C2"]


@pytest.fixture()
def single_col_data() -> tuple[pd.DataFrame, str, list[str]]:
    df = pd.DataFrame({"value": [1.2, 2.5, 3.8, 4.1, 2.3, 5.0, 3.3, 1.8]})
    return df, "value", []


@pytest.fixture()
def mock_axes() -> tuple[plt.Figure, Axes]:
    fig, ax = plt.subplots()
    return fig, ax


# ---------------------------------------------------------------------------
# _load_data
# ---------------------------------------------------------------------------
class TestLoadData:
    def test_success_and_columns_extracted(self, sample_csv: Path) -> None:
        data, x_var, y_vars = tg._load_data(sample_csv)
        assert isinstance(data, pd.DataFrame)
        assert x_var == "theta"
        assert set(y_vars) == {"C1", "C2"}
        assert data[x_var].is_monotonic_increasing
        assert list(data[x_var]) == [1.0, 2.0, 3.0, 4.0]

    def test_exception_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(Exception):
            tg._load_data(tmp_path / "not_exist.csv")

    def test_single_column_histogram_mode(self, single_col_csv: Path) -> None:
        data, x_var, y_vars = tg._load_data(single_col_csv)
        assert x_var == "value"
        assert y_vars == []
        assert len(data) == 8


# ---------------------------------------------------------------------------
# _plot_direct
# ---------------------------------------------------------------------------
class TestPlotDirect:
    def test_line_properties_and_data(self, mock_axes) -> None:
        fig, ax = mock_axes
        x_data = np.array([1.0, 2.0, 3.0])
        y_data = np.array([2.0, 4.0, 6.0])

        tg._plot_direct(ax, x_data, y_data, "linear")

        lines = ax.get_lines()
        assert len(lines) == 1
        line = lines[0]
        assert line.get_label() == "linear"
        assert line.get_linewidth() == 2
        assert np.allclose(line.get_xdata(), x_data)
        assert np.allclose(line.get_ydata(), y_data)

        plt.close(fig)

    def test_data_length(self, mock_axes) -> None:
        fig, ax = mock_axes
        tg._plot_direct(ax, np.array([1.0, 2.0]), np.array([1.0, 2.0]), "var")
        assert len(ax.get_lines()[0].get_xdata()) == 2
        plt.close(fig)


# ---------------------------------------------------------------------------
# _plot_smooth
# ---------------------------------------------------------------------------
class TestPlotSmooth:
    def test_produces_line_with_300_points(self, mock_axes) -> None:
        fig, ax = mock_axes
        x_data = np.array([1.0, 2.0, 3.0, 4.0])
        y_data = np.array([1.0, 4.0, 9.0, 16.0])

        tg._plot_smooth(ax, x_data, y_data, "curve")

        lines = ax.get_lines()
        assert len(lines) >= 1
        xdata, _ = lines[-1].get_data()
        assert len(xdata) == 300

        plt.close(fig)


# ---------------------------------------------------------------------------
# _plot_linear
# ---------------------------------------------------------------------------
class TestPlotLinear:
    def test_produces_line_with_equation_label(self, mock_axes) -> None:
        fig, ax = mock_axes
        x_data = np.array([1.0, 2.0, 3.0])
        y_data = np.array([2.0, 4.0, 6.0])

        tg._plot_linear(ax, x_data, y_data, "line")

        lines = ax.get_lines()
        assert len(lines) >= 1
        assert any("fit:" in line.get_label() for line in lines)

        plt.close(fig)

    def test_fitting_data_length(self, mock_axes) -> None:
        fig, ax = mock_axes
        x_data = np.array([1.0, 2.0, 3.0, 4.0])
        y_data = np.array([1.0, 2.0, 3.0, 4.0])

        tg._plot_linear(ax, x_data, y_data, "fit")

        xdata, _ = ax.get_lines()[0].get_data()
        assert len(xdata) == 4

        plt.close(fig)


# ---------------------------------------------------------------------------
# _plot_single_line
# ---------------------------------------------------------------------------
class TestPlotSingleLine:
    @pytest.mark.parametrize("mode,x,y", [
        ("direct", np.array([1.0, 2.0, 3.0]),         np.array([1.0, 4.0, 9.0])),
        ("smooth", np.array([1.0, 2.0, 3.0, 4.0]),    np.array([1.0, 4.0, 9.0, 16.0])),
        ("linear", np.array([1.0, 2.0, 3.0, 4.0]),    np.array([2.0, 4.0, 6.0, 8.0])),
    ])
    def test_valid_modes_produce_lines(self, mock_axes, mode, x, y) -> None:
        fig, ax = mock_axes
        tg._plot_single_line(ax, x, y, "var", mode)
        assert len(ax.get_lines()) >= 1
        plt.close(fig)

    def test_invalid_mode_raises(self, mock_axes) -> None:
        fig, ax = mock_axes
        with pytest.raises(ValueError, match="Unknown plot mode"):
            tg._plot_single_line(ax, np.array([1.0, 2.0]), np.array([1.0, 2.0]), "test", "invalid")
        plt.close(fig)


# ---------------------------------------------------------------------------
# _setup_axes
# ---------------------------------------------------------------------------
class TestSetupAxes:
    def test_labels_and_grid(self, mock_axes) -> None:
        fig, ax = mock_axes
        tg._setup_axes(ax, "x_var", "y_label")
        assert ax.get_xlabel() == "x_var"
        assert ax.get_ylabel() == "y_label"
        assert len(ax.get_xgridlines()) > 0
        plt.close(fig)

    def test_legend_added(self, mock_axes) -> None:
        fig, ax = mock_axes
        tg._plot_direct(ax, np.array([1.0, 2.0]), np.array([1.0, 2.0]), "test")
        tg._setup_axes(ax, "x", "y")
        assert ax.get_legend() is not None
        plt.close(fig)


# ---------------------------------------------------------------------------
# _render_histogram
# ---------------------------------------------------------------------------
class TestRenderHistogram:
    def test_returns_hist_figure(self, single_col_data) -> None:
        data, x_var, _ = single_col_data
        figs = tg._render_histogram(data, x_var)

        assert isinstance(figs, list)
        assert len(figs) == 1
        fig, name = figs[0]
        assert name == "hist"
        plt.close(fig)

    def test_histogram_has_bars(self, single_col_data) -> None:
        data, x_var, _ = single_col_data
        figs = tg._render_histogram(data, x_var)
        fig, _ = figs[0]
        ax = fig.axes[0]

        assert len(ax.patches) > 0

        plt.close(fig)

    def test_axis_labels(self, single_col_data) -> None:
        data, x_var, _ = single_col_data
        figs = tg._render_histogram(data, x_var)
        fig, _ = figs[0]
        ax = fig.axes[0]

        assert ax.get_xlabel() == x_var
        assert ax.get_ylabel() == "Frequency"

        plt.close(fig)


# ---------------------------------------------------------------------------
# _render_separate_plot
# ---------------------------------------------------------------------------
class TestRenderSeparatePlot:
    def test_returns_one_figure_per_var_with_correct_names(self, sample_data) -> None:
        data, x_var, y_vars = sample_data
        figs = tg._render_separate_plot(data, x_var, y_vars, "direct")

        assert isinstance(figs, list)
        assert len(figs) == len(y_vars)
        assert set(var for _, var in figs) == set(y_vars)

        for fig, _ in figs:
            plt.close(fig)

    @pytest.mark.parametrize("mode", ["direct", "smooth", "linear"])
    def test_all_modes(self, sample_data, mode) -> None:
        data, x_var, y_vars = sample_data
        figs = tg._render_separate_plot(data, x_var, y_vars, mode)
        assert len(figs) == len(y_vars)
        for fig, _ in figs:
            plt.close(fig)


# ---------------------------------------------------------------------------
# _render_combined_plot
# ---------------------------------------------------------------------------
class TestRenderCombinedPlot:
    def test_single_figure_named_combined_with_all_lines(self, sample_data) -> None:
        data, x_var, y_vars = sample_data
        figs = tg._render_combined_plot(data, x_var, y_vars, "direct")

        assert len(figs) == 1
        fig, name = figs[0]
        assert name == "combined"
        assert len(fig.axes[0].get_lines()) >= len(y_vars)

        plt.close(fig)

    @pytest.mark.parametrize("mode", ["direct", "smooth", "linear"])
    def test_all_modes(self, sample_data, mode) -> None:
        data, x_var, y_vars = sample_data
        figs = tg._render_combined_plot(data, x_var, y_vars, mode)
        assert len(figs) == 1
        plt.close(figs[0][0])


# ---------------------------------------------------------------------------
# _render_plot
# ---------------------------------------------------------------------------
class TestRenderPlot:
    @pytest.mark.parametrize("mode", ["direct", "smooth", "linear"])
    @pytest.mark.parametrize("plot_together", [True, False])
    def test_modes_and_combinations(self, sample_data, mode, plot_together) -> None:
        data, x_var, y_vars = sample_data
        figs = tg._render_plot(data, x_var, y_vars, mode=mode, plot_together=plot_together)

        if plot_together:
            assert len(figs) == 1
            assert figs[0][1] == "combined"
        else:
            assert len(figs) == len(y_vars)
            assert [var_name for _, var_name in figs] == y_vars

        for fig, _ in figs:
            plt.close(fig)

    def test_invalid_mode(self, sample_data) -> None:
        data, x_var, y_vars = sample_data
        with pytest.raises(ValueError, match="Unknown plot mode"):
            tg._render_plot(data, x_var, y_vars, mode="unknown_mode", plot_together=False)

    def test_histogram_path_for_single_column(self, single_col_data) -> None:
        data, x_var, y_vars = single_col_data
        figs = tg._render_plot(data, x_var, y_vars, mode="smooth", plot_together=False)

        assert len(figs) == 1
        fig, name = figs[0]
        assert name == "hist"
        plt.close(fig)


# ---------------------------------------------------------------------------
# _save_figures
# ---------------------------------------------------------------------------
class TestSaveFigures:
    def test_saves_with_correct_paths_and_closes_all(self, tmp_path) -> None:
        data_path = tmp_path / "source_data.csv"
        mock_fig1, mock_fig2 = MagicMock(), MagicMock()
        figs = [(mock_fig1, "C1"), (mock_fig2, "C2")]

        with patch("src.utils.table_grapher.plt.close") as mock_close:
            tg._save_figures(data_path, figs, mode="smooth")  # type: ignore[arg-type]

        mock_fig1.savefig.assert_called_once()
        assert mock_fig1.savefig.call_args[0][0] == tmp_path / "source_data_smooth_C1.png"
        mock_fig2.savefig.assert_called_once()
        assert mock_fig2.savefig.call_args[0][0] == tmp_path / "source_data_smooth_C2.png"
        assert mock_close.call_count == 2

    def test_filename_contains_mode(self, tmp_path) -> None:
        mock_fig = MagicMock()
        with patch("src.utils.table_grapher.plt.close"):
            tg._save_figures(tmp_path / "test.csv", [(mock_fig, "var")], mode="direct")
        assert "direct" in mock_fig.savefig.call_args[0][0].name

    def test_closes_all_figures(self, tmp_path) -> None:
        figs = [(MagicMock(), f"v{i}") for i in range(3)]
        with patch("src.utils.table_grapher.plt.close") as mock_close:
            tg._save_figures(tmp_path / "test.csv", figs, mode="smooth")  # type: ignore[arg-type]
        assert mock_close.call_count == 3

    def test_histogram_filename(self, tmp_path) -> None:
        mock_fig = MagicMock()
        with patch("src.utils.table_grapher.plt.close"):
            tg._save_figures(tmp_path / "data.csv", [(mock_fig, "hist")], mode="linear")
        saved_path = mock_fig.savefig.call_args[0][0]
        assert saved_path.name == "data_hist.png"
        assert "linear" not in saved_path.name


# ---------------------------------------------------------------------------
# table2graph
# ---------------------------------------------------------------------------
class TestTable2Graph:
    @patch("src.utils.table_grapher._save_figures")
    @patch("src.utils.table_grapher._render_plot")
    @patch("src.utils.table_grapher._load_data")
    def test_success_calls_pipeline(self, mock_load, mock_render, mock_save, tmp_path: Path) -> None:
        target_csv = tmp_path / "test.csv"
        mock_load.return_value = ("mock_df", "x", ["y"])
        mock_render.return_value = [("mock_fig", "y")]

        tg.table2graph(target_csv, mode="linear", plot_together=True)

        mock_load.assert_called_once_with(target_csv)
        mock_render.assert_called_once_with("mock_df", "x", ["y"], "linear", True)
        mock_save.assert_called_once_with(target_csv, [("mock_fig", "y")], "linear")

    @patch("src.utils.table_grapher._load_data")
    def test_exception_propagation(self, mock_load, tmp_path: Path) -> None:
        mock_load.side_effect = Exception("Simulated Load Error")
        with pytest.raises(Exception, match="Simulated Load Error"):
            tg.table2graph(tmp_path / "test.csv")

    @pytest.mark.parametrize("mode", ["direct", "smooth", "linear"])
    @pytest.mark.parametrize("plot_together", [True, False])
    def test_all_mode_combinations(self, tmp_path: Path, mode, plot_together) -> None:
        csv_file = tmp_path / "test.csv"
        pd.DataFrame({"x": [1, 2, 3, 4], "y": [1, 4, 9, 16]}).to_csv(csv_file, index=False)
        with patch("src.utils.table_grapher._save_figures"):
            tg.table2graph(csv_file, mode=mode, plot_together=plot_together)

    def test_default_parameters(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        pd.DataFrame({"x": [1, 2, 3, 4], "y": [1, 4, 9, 16]}).to_csv(csv_file, index=False)
        with patch("src.utils.table_grapher._save_figures"):
            tg.table2graph(csv_file)

    def test_single_column_triggers_histogram(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "single.csv"
        pd.DataFrame({"value": [1.2, 2.5, 3.8]}).to_csv(csv_file, index=False)
        with patch("src.utils.table_grapher._save_figures") as mock_save:
            tg.table2graph(csv_file)
        saved_name = mock_save.call_args[0][1][0][1]
        assert saved_name == "hist"

    def test_histogram_ignores_mode(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "single.csv"
        pd.DataFrame({"x": [1.0, 2.0, 3.0]}).to_csv(csv_file, index=False)
        with patch("src.utils.table_grapher._save_figures") as mock_save:
            tg.table2graph(csv_file, mode="linear")
        saved_name = mock_save.call_args[0][1][0][1]
        assert saved_name == "hist"