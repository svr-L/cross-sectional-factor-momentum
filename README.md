# Factor Momentum on Equity Risk-Factor ETFs

A gross implementation of **cross-sectional Factor Momentum** on equity risk-factor ETFs, inspired by **Arnott et al. (2020)** and stress-tested via **Politis–Romano stationary bootstrap**.

## Project objective
This project implements and evaluates a **gross factor-momentum strategy** on equity risk-factor ETFs. The current version focuses on the core block of the research pipeline:

- signal construction for **6–1** and **12–1** cross-sectional factor momentum;
- a **monthly rebalancing backtest implemented correctly**;
- realized performance and risk-adjusted performance metrics;
- **stationary-bootstrap robustness analysis**.

## Data
The notebook supports two data sources:

1. **Original HDF dataset** used in the master project;
2. **Yahoo Finance** ETF data for a lightweight public-data replication.

The public-data tickers used in the notebook are:
- `RPV` — Value
- `SIZE` — Size
- `MTUM` — Momentum
- `SPHQ` — Quality
- `SPLV` — Low Volatility

## Main methodological notes
- The strategy is implemented on a **gross** basis.
- Weights are observed at the **month-end signal date**, entered on the **next trading day**, and then **allowed to drift** until the next rebalance.
- The stationary bootstrap is applied to the **panel of factor-ETF returns**, and the full strategy is rebuilt within each bootstrap sample.

## Latest reported results
### Realized backtest metrics
| Strategy | n | CAGR | AnnVol | MxDD | ShR | SoR | Calmar | Ulcer | Martin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MomTop1_80_20 | 3246 | 0.1403 | 0.1747 | -0.3318 | 0.8394 | 1.3252 | 0.4229 | 0.0573 | 2.4485 |
| MomTop2_35_35 | 3246 | 0.1227 | 0.1629 | -0.3681 | 0.7920 | 1.2233 | 0.3332 | 0.0617 | 1.9889 |
| EW | 3246 | 0.1220 | 0.1624 | -0.3808 | 0.7907 | 1.2130 | 0.3205 | 0.0612 | 1.9953 |

### Stationary-bootstrap summary — CAGR
| Strategy | mean | p05 | p50 | p95 | n |
|---|---:|---:|---:|---:|---:|
| MomTop1_80_20 | 0.1242 | 0.0437 | 0.1248 | 0.2015 | 1000 |
| MomTop2_35_35 | 0.1244 | 0.0486 | 0.1247 | 0.1994 | 1000 |
| EW | 0.1224 | 0.0523 | 0.1235 | 0.1918 | 1000 |

### Stationary-bootstrap summary — Sharpe ratio
| Strategy | mean | p05 | p50 | p95 | n |
|---|---:|---:|---:|---:|---:|
| MomTop1_80_20 | 0.7729 | 0.3163 | 0.7659 | 1.2378 | 1000 |
| MomTop2_35_35 | 0.8101 | 0.3636 | 0.8023 | 1.2933 | 1000 |
| EW | 0.8189 | 0.3774 | 0.8040 | 1.3128 | 1000 |

### Stationary-bootstrap summary — Martin ratio
| Strategy | mean | p05 | p50 | p95 | n |
|---|---:|---:|---:|---:|---:|
| MomTop1_80_20 | 1.6096 | 0.2147 | 1.3577 | 3.8341 | 1000 |
| MomTop2_35_35 | 1.7964 | 0.2934 | 1.5077 | 4.3715 | 1000 |
| EW | 1.8528 | 0.3217 | 1.5575 | 4.5414 | 1000 |

### Stationary-bootstrap summary — Max drawdown
| Strategy | mean | p05 | p50 | p95 | n |
|---|---:|---:|---:|---:|---:|
| MomTop1_80_20 | -0.3462 | -0.5324 | -0.3396 | -0.1795 | 1000 |
| MomTop2_35_35 | -0.3316 | -0.5068 | -0.3431 | -0.1741 | 1000 |
| EW | -0.3231 | -0.4923 | -0.3343 | -0.1657 | 1000 |

## Interpretation
The best realized specification is **MomTop1_80_20**, which achieved **14.0% CAGR**, **0.84 Sharpe ratio**, **2.45 Martin ratio**, and **-33.2% maximum drawdown**. The stationary bootstrap suggests that the edge appears more convincing in **growth terms (CAGR)** than in volatility- or drawdown-adjusted metrics, where the gap versus the equal-weighted benchmark is narrower.

## Planned extensions
The current notebook deliberately stops before the following extensions:

1. **Realistic transaction costs** to move from **gross** to **net** performance;
2. A **risk-managed momentum** overlay *à la* **Barroso and Santa-Clara (2015)** to test whether volatility-managed momentum also improves **factor momentum**.

## Repository structure
```text
.
├── Factor_Momentum_Arnott2020_submission.ipynb
├── README.md
├── requirements.txt
├── .gitignore
└── LICENSE
```

## How to run
1. Create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Open the notebook:
   ```bash
   jupyter notebook Factor_Momentum_Arnott2020_submission.ipynb
   ```
4. In the notebook, choose either:
   - `DATA_SOURCE = "hdf"` and provide your original HDF path, or
   - `DATA_SOURCE = "yahoo"` for the public-data version.

## Reference papers
- Arnott, R., Clements, A., Kalesnik, V., and Linnainmaa, J. (2020). *Factor Momentum*.
- Politis, D. N., and Romano, J. P. (1994). *The Stationary Bootstrap*.
- Barroso, P., and Santa-Clara, P. (2015). *Momentum Has Its Moments*.
