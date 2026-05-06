import numpy as np
import pytest
from pathlib import Path

import src.utils.data_generator as dg


# ---------------------------------------------------------------------------
# generate_data — shape and dtype
# ---------------------------------------------------------------------------
class TestGenerateDataShape:
    @pytest.mark.parametrize("n", [2, 10, 100, 1000])
    def test_correct_length(self, n: int) -> None:
        data = dg.generate_data(mean=0.0, width=10.0, n=n, variance=4.0)
        assert data.shape == (n,)

    def test_returns_float64(self) -> None:
        data = dg.generate_data(mean=0.0, width=10.0, n=50, variance=4.0)
        assert data.dtype == np.float64

    def test_2d_shape(self) -> None:
        data = dg.generate_data(mean=10.0, width=20.0, n=100, variance=9.0, dimension=2, slope=2.0, intercept=5.0, r_squared=0.9, decimals=None)
        assert data.shape == (100, 2)


# ---------------------------------------------------------------------------
# generate_data — exact statistics (before rounding)
# ---------------------------------------------------------------------------
class TestGenerateDataExactStats:
    def test_exact_mean_and_variance(self) -> None:
        data = dg.generate_data(mean=10.0, width=20.0, n=1000, variance=9.0, decimals=2)
        assert abs(data.mean() - 10.0) < 0.02
        assert abs(data.var(ddof=0) - 9.0) < 0.1

    def test_no_rounding_guarantees_exact_stats(self) -> None:
        data = dg.generate_data(mean=5.0, width=8.0, n=500, variance=4.0, decimals=None)
        assert abs(data.mean() - 5.0) < 1e-10
        assert abs(data.var(ddof=0) - 4.0) < 1e-10


# ---------------------------------------------------------------------------
# generate_data — width constraint
# ---------------------------------------------------------------------------
class TestGenerateDataWidth:
    def test_all_values_within_width(self) -> None:
        data = dg.generate_data(mean=100.0, width=10.0, n=200, variance=4.0)
        half = 10.0 / 2.0
        assert data.min() >= 100.0 - half
        assert data.max() <= 100.0 + half

    def test_width_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="width must be > 0"):
            dg.generate_data(mean=42.0, width=0.0, n=100, variance=1.0)


# ---------------------------------------------------------------------------
# generate_data — rounding
# ---------------------------------------------------------------------------
class TestGenerateDataRounding:
    def test_round_to_integers(self) -> None:
        data = dg.generate_data(mean=0.0, width=10.0, n=200, variance=4.0, decimals=0)
        assert np.all(data == np.round(data))

    def test_round_to_two_decimals(self) -> None:
        data = dg.generate_data(mean=5.0, width=8.0, n=200, variance=2.0, decimals=2)
        assert np.allclose(data, np.round(data, 2))


# ---------------------------------------------------------------------------
# generate_data — distributions
# ---------------------------------------------------------------------------
class TestGenerateDataDistributions:
    def test_normal(self) -> None:
        data = dg.generate_data(mean=0.0, width=6.0, n=500, variance=1.0, distribution="normal")
        assert len(data) == 500
        assert abs(data.mean()) < 0.05
        assert abs(data.var(ddof=0) - 1.0) < 0.2

    def test_uniform(self) -> None:
        data = dg.generate_data(mean=0.0, width=6.0, n=500, variance=1.0, distribution="uniform")
        assert len(data) == 500
        assert abs(data.mean()) < 0.05
        assert abs(data.var(ddof=0) - 1.0) < 0.2

    def test_invalid_distribution_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown distribution"):
            dg.generate_data(mean=0.0, width=10.0, n=50, variance=4.0, distribution="poisson")


# ---------------------------------------------------------------------------
# generate_data — reproducibility
# ---------------------------------------------------------------------------
class TestGenerateDataReproducibility:
    def test_same_seed_gives_same_result(self) -> None:
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        data1 = dg.generate_data(mean=10.0, width=20.0, n=100, variance=4.0, rng=rng1)
        data2 = dg.generate_data(mean=10.0, width=20.0, n=100, variance=4.0, rng=rng2)
        np.testing.assert_array_equal(data1, data2)

    def test_different_seed_gives_different_result(self) -> None:
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(99)
        data1 = dg.generate_data(mean=10.0, width=20.0, n=100, variance=4.0, rng=rng1)
        data2 = dg.generate_data(mean=10.0, width=20.0, n=100, variance=4.0, rng=rng2)
        assert not np.array_equal(data1, data2)


# ---------------------------------------------------------------------------
# generate_data — edge cases
# ---------------------------------------------------------------------------
class TestGenerateDataEdgeCases:
    def test_n_must_be_greater_than_one(self) -> None:
        with pytest.raises(ValueError, match="n must be > 1"):
            dg.generate_data(mean=7.0, width=100.0, n=1, variance=1.0)

    def test_large_variance_small_width(self) -> None:
        data = dg.generate_data(mean=0.0, width=2.0, n=100, variance=100.0)
        assert len(data) == 100
        assert abs(data.var(ddof=0) - 100.0) < 5.0

    def test_very_large_n(self) -> None:
        data = dg.generate_data(mean=50.0, width=30.0, n=5000, variance=25.0)
        assert len(data) == 5000
        assert abs(data.mean() - 50.0) < 0.05

    @pytest.mark.parametrize("variance", [0.0, -1.0])
    def test_variance_must_be_positive(self, variance: float) -> None:
        with pytest.raises(ValueError, match="variance must be positive"):
            dg.generate_data(mean=0.0, width=10.0, n=50, variance=variance)


# ---------------------------------------------------------------------------
# generate_data — 2-D mode (X, Y with exact R²)
# ---------------------------------------------------------------------------
class TestGenerateData2D:
    def test_exact_slope_and_intercept(self) -> None:
        data = dg.generate_data(
            mean=10.0,
            width=20.0,
            n=500,
            variance=9.0,
            dimension=2,
            slope=2.0,
            intercept=5.0,
            r_squared=0.9,
            decimals=None,
            rng=np.random.default_rng(42),
        )
        slope_est, intercept_est = np.polyfit(data[:, 0], data[:, 1], 1)
        assert abs(slope_est - 2.0) < 1e-10
        assert abs(intercept_est - 5.0) < 1e-10

    def test_exact_r_squared(self) -> None:
        data = dg.generate_data(
            mean=10.0,
            width=20.0,
            n=500,
            variance=9.0,
            dimension=2,
            slope=2.0,
            intercept=5.0,
            r_squared=0.9,
            decimals=None,
            rng=np.random.default_rng(42),
        )
        y_pred = 2.0 * data[:, 0] + 5.0
        ss_res = np.sum((data[:, 1] - y_pred) ** 2)
        ss_tot = np.sum((data[:, 1] - data[:, 1].mean()) ** 2)
        r2 = 1 - ss_res / ss_tot
        assert abs(r2 - 0.9) < 1e-10

    def test_r_squared_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="r_squared must be in"):
            dg.generate_data(mean=0.0, width=10.0, n=50, variance=4.0, dimension=2, slope=1.0, intercept=0.0, r_squared=0.0)

    def test_r_squared_greater_than_one(self) -> None:
        with pytest.raises(ValueError, match="r_squared must be in"):
            dg.generate_data(mean=0.0, width=10.0, n=50, variance=4.0, dimension=2, slope=1.0, intercept=0.0, r_squared=1.5)

    def test_decimals_y_different_from_decimals(self) -> None:
        data = dg.generate_data(
            mean=0.0, width=10.0, n=200, variance=4.0, dimension=2, slope=1.0, intercept=0.0, r_squared=0.95, decimals=2, decimals_y=0
        )
        assert np.allclose(data[:, 0], np.round(data[:, 0], 2))
        assert np.all(data[:, 1] == np.round(data[:, 1]))

    def test_default_decimals_y(self) -> None:
        data = dg.generate_data(mean=0.0, width=10.0, n=200, variance=4.0, dimension=2, slope=1.0, intercept=0.0, r_squared=0.95, decimals=2)
        assert np.allclose(data[:, 0], np.round(data[:, 0], 2))
        assert np.allclose(data[:, 1], np.round(data[:, 1], 2))

    def test_2d_export_csv_header(self, tmp_path: Path) -> None:
        csv = tmp_path / "out2d.csv"
        dg.generate_data(mean=0.0, width=10.0, n=10, variance=4.0, dimension=2, slope=1.0, intercept=0.0, r_squared=0.95, decimals=None, csv_path=csv)
        content = csv.read_text(encoding="utf-8")
        assert content.splitlines()[0] == "x,y"

    def test_2d_reproducibility(self) -> None:
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        data1 = dg.generate_data(
            mean=10.0, width=20.0, n=100, variance=4.0, dimension=2, slope=2.0, intercept=5.0, r_squared=0.9, decimals=None, rng=rng1
        )
        data2 = dg.generate_data(
            mean=10.0, width=20.0, n=100, variance=4.0, dimension=2, slope=2.0, intercept=5.0, r_squared=0.9, decimals=None, rng=rng2
        )
        np.testing.assert_array_equal(data1, data2)


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
class TestSummary:
    def test_summary_1d(self) -> None:
        data = dg.generate_data(mean=5.0, width=10.0, n=50, variance=4.0, decimals=2)
        s = dg.summary(data)
        assert "mean=" in s and "std=" in s and "var=" in s and "range=[" in s
        assert "(2-D)" not in s

    def test_summary_2d(self) -> None:
        data = dg.generate_data(mean=5.0, width=10.0, n=50, variance=4.0, dimension=2, slope=1.0, intercept=0.0, r_squared=0.95, decimals=2)
        s = dg.summary(data)
        assert "X:" in s and "Y:" in s and "(2-D)" in s


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------
class TestExportCSV:
    def test_basic_export(self, tmp_path: Path) -> None:
        csv = tmp_path / "out.csv"
        dg.generate_data(mean=0.0, width=10.0, n=3, variance=4.0, decimals=None, rng=np.random.default_rng(0), csv_path=csv)
        content = csv.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        assert lines[0] == "x"
        assert len(lines[1:]) == 3

    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        csv = tmp_path / "out.csv"
        dg.generate_data(mean=0.0, width=10.0, n=2, variance=1.0, decimals=None, rng=np.random.default_rng(0), csv_path=csv)
        assert csv.resolve().exists()


# ---------------------------------------------------------------------------
# _SAMPLERS registry
# ---------------------------------------------------------------------------
class TestSamplerRegistry:
    def test_built_in_samplers_registered(self) -> None:
        assert "normal" in dg._SAMPLER_FUNCS
        assert "uniform" in dg._SAMPLER_FUNCS

    def test_add_and_use_custom_sampler(self) -> None:

        def _sample_all_zero(n: int, std_target: float, width: float, rng: np.random.Generator) -> np.ndarray:
            return np.full(n, 0.0, dtype=np.float64)

        dg._SAMPLER_FUNCS["_test_zero"] = _sample_all_zero

        data = dg.generate_data(mean=5.0, width=10.0, n=20, variance=1.0, distribution="_test_zero")
        assert len(data) == 20
        assert np.allclose(data, 5.0)
