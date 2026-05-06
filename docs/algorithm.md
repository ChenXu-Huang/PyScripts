# Data Generator Algorithm

## Overview

The data generator produces synthetic datasets with **exact statistical properties**
using reverse-boundary rejection sampling. It supports two modes:

- **1-D mode** — generates a single variable _X_ with a specified mean, variance,
  range width, and distribution shape.
- **2-D mode** — generates a pair _(X, Y)_ where _Y = aX + b + noise_,
  with an exact coefficient of determination _R²_.

---

## 1-D mode — reverse-boundary rejection sampling

Goal: generate _n_ values with exactly the requested mean and variance, bounded
within a given width, while controlling the distribution shape.

### Step 1 — reverse truncation boundary in standard space

Because the data will later be scaled by _√variance_, the width constraint must
be pre-scaled into the standard normal space (mean = 0, variance = 1):

```
R_std = (width / 2) / √variance
```

The acceptance interval in standard space is _[−R_std, +R_std]_.

### Step 2 — rejection sampling

Generate candidates from the chosen base distribution and keep those that fall
within _[−R_std, +R_std]_. Repeat until exactly _n_ values are collected.

**Supported samplers:**

- **normal** — standard normal _N(0,1)_ with rejection
- **uniform** — direct uniform draw over _[−R_std, +R_std]_

### Step 3 — standardisation (error removal)

The raw accepted values have a sample mean _M_sample_ and sample standard
deviation _S_sample_ that differ from 0 and 1 due to truncation and randomness.
Remove these errors by z-score normalisation:

```
x_std[i] = (x_accepted[i] - M_sample) / S_sample
```

After this step, the data has **exactly** mean = 0 and variance = 1.

> **Note:** this slightly stretches or squeezes the data, so individual values
> may minutely exceed the original _±R_std_ boundary. This is a necessary
> trade-off for exact downstream statistics.

### Step 4 — target transformation

Map the standardised data to the desired mean and variance:

```
x_target[i] = x_std[i] · √variance + mean
```

At this point (before rounding), the sample mean and variance are **exactly**
the requested values (within floating-point precision).

### Step 5 — rounding (discretisation)

**decimals >= 0** — `numpy.round(data, decimals)`.

**decimals = None** — no rounding, keeps full precision.

Rounding introduces a small error in the statistics. If the rounded values are
used for downstream calculations (such as the 2-D mode), the actual moments
of _X_final_ should be recomputed first.

### Edge cases

- **n** must be > 1, otherwise `ValueError`.
- **width** must be > 0, otherwise `ValueError`.
- **variance** must be > 0, otherwise `ValueError`.

---

## 2-D mode — orthogonal noise injection

Builds on the 1-D output and generates a second variable _Y_ that is linearly
related to _X_ with an exact _R²_.

### Stage 1 — generate X

Use the 1-D algorithm above to produce the rounded array _X_final_.

### Stage 2 — recompute actual statistics of X_final

Because rounding alters the moments, the **actual** sample statistics must be
recalculated before building Y:

```
X̄_real  = mean(X_final)
Var(X_real) = variance(X_final)
```

All subsequent calculations **must** use _Var(X_real)_, not the original input
_variance_, otherwise the target _R²_ will be incorrect.

### Stage 3 — generate orthogonal noise E

1. Draw _n_ i.i.d. standard normal samples: _E_raw ∼ N(0, 1)_.
2. Centre the noise: _E₁[i] = E_raw[i] − mean(E_raw)_.
3. Compute the linear regression slope of _E₁_ against _X_final_:

   ```
   m_err = Σ((X_final[i] − X̄_real) · E₁[i]) / Σ((X_final[i] − X̄_real)²)
   ```

4. Remove the linear dependency to obtain perfectly orthogonal noise:

   ```
   E_perfect[i] = E₁[i] − m_err · (X_final[i] − X̄_real)
   ```

5. Compute the variance of the purified noise: _Var(E_perfect)_.

### Stage 4 — R² injection and synthetic Y

1. Compute the variance of the ideal (noiseless) linear component:

   ```
   Var(Y_ideal) = a² · Var(X_real)
   ```

2. Derive the noise scaling factor _k_ from the target _R²_:

   ```
   k = √(Var(Y_ideal) · (1 − R²) / (Var(E_perfect) · R²))
   ```

3. Synthesise the continuous Y array:

   ```
   Y_raw[i] = a · X_final[i] + b + k · E_perfect[i]
   ```

At this point, a linear regression of _Y_raw_ on _X_final_ will recover
**exactly** the specified slope _a_, intercept _b_, and _R²_ (within
floating-point precision).

### Stage 5 — round Y

Round _Y_raw_ to the specified number of decimal places.

- **decimals_y >= 0** — `numpy.round(Y_raw, decimals_y)`.
- **decimals_y = None** — uses the same value as `decimals`.

---

## API

- **`generate_data(...)`** — returns `np.ndarray` of shape `(n,)` for 1-D
  or `(n, 2)` for 2-D. Generates the dataset and exports it to CSV.
- **`summary(data)`** — returns `str`, a formatted summary with mean, std,
  var, and range for the array.

---

## Parameter reference

### Shared (1-D and 2-D)

- **n** — number of data points (must be > 1).
- **mean** — target arithmetic mean of X.
- **width** — total range width of X (must be > 0).
- **variance** — target variance of X (must be > 0).
- **distribution** — base distribution shape: `"normal"` or `"uniform"`.
- **decimals** — decimal places for rounding X; `>= 0` rounds, `None` skips.
- **rng** — NumPy `Generator` for reproducibility.
- **csv_path** — export path for CSV output.
- **dimension** — `1` for 1-D array, `2` for 2-D array.

### 2-D only

- **slope** — linear coefficient _a_.
- **intercept** — linear intercept _b_.
- **r_squared** — target coefficient of determination _R²_ in (0, 1].
- **decimals_y** — decimal places for rounding Y; `None` uses same as `decimals`.
