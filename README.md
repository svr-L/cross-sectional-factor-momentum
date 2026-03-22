# Factor Momentum on Equity Risk-Factor ETFs

An ETF-based implementation of **cross-sectional Factor Momentum** inspired by **Arnott et al. (2020)**, evaluated under a **historical risk-free rate**, **proxy transaction costs**, and **Politis–Romano stationary-bootstrap** robustness checks.

## Project objective

This project studies whether an Arnott-style factor-momentum signal remains attractive when translated from an academic idea into a **tradable ETF implementation**. The notebook currently covers:

* **6–1** and **12–1** cross-sectional factor-momentum signal construction;
* a **monthly rebalancing backtest with next-day implementation and drifting weights between rebalances**;
* realized **gross** and **net-of-costs** performance evaluation;
* historical **daily risk-free** adjustment (default: FRED `DGS3MO`, with `SOFR` optional);
* proxy transaction-cost estimation via **Abdi–Ranaldo (2017)** and **Corwin–Schultz (2012)**;
* **stationary-bootstrap** robustness analysis with the full strategy rebuilt inside each bootstrap sample.

## Data

The notebook supports two data sources:

1. the **original HDF dataset** used in the master project;
2. **Yahoo Finance** OHLC ETF data for a public-data replication.

Public-data ETF mapping:

* `RPV` — Value
* `SIZE` — Size
* `MTUM` — Momentum
* `SPHQ` — Quality
* `SPLV` — Low Volatility

## Main methodological notes

* Signals are observed at the **month-end signal date** and implemented on the **next trading day**.
* Portfolio weights are then **allowed to drift** until the next rebalance.
* Risk-adjusted metrics use a **historical daily risk-free series**, not a fixed zero-rate assumption.
* Transaction costs are estimated from **daily OHLC data** and charged using **drifted pre-trade weights**.
* The stationary bootstrap is applied to the **panel of ETF returns**, and the strategy is rebuilt within each bootstrap sample.

## Latest reported results

All figures below refer to the **common-data backtest sample** from **2013-04-19 to 2026-03-20**.

### Realized backtest metrics — gross

|Strategy|n|CAGR|AnnVol|MxDD|ShR|SoR|Calmar|Ulcer|Martin|
|-|-:|-:|-:|-:|-:|-:|-:|-:|-:|
|MomTop1\_80\_20|3093|0.1243|0.1768|-0.3318|0.6762|1.0630|0.3747|0.0586|1.8921|
|MomTop2\_35\_35|3093|0.1108|0.1652|-0.3681|0.6386|0.9824|0.3010|0.0631|1.5449|
|EW|3093|0.1121|0.1649|-0.3808|0.6467|0.9892|0.2944|0.0625|1.5795|

### Realized backtest metrics — net (Abdi–Ranaldo)

|Strategy|n|CAGR|AnnVol|MxDD|ShR|SoR|Calmar|Ulcer|Martin|
|-|-:|-:|-:|-:|-:|-:|-:|-:|-:|
|MomTop1\_80\_20|3093|0.1201|0.1769|-0.3318|0.6546|1.0285|0.3619|0.0602|1.7738|
|MomTop2\_35\_35|3093|0.1082|0.1654|-0.3681|0.6242|0.9590|0.2940|0.0641|1.4805|
|EW|3093|0.1119|0.1650|-0.3808|0.6453|0.9869|0.2938|0.0626|1.5724|

### Realized backtest metrics — net (Corwin–Schultz)

|Strategy|n|CAGR|AnnVol|MxDD|ShR|SoR|Calmar|Ulcer|Martin|
|-|-:|-:|-:|-:|-:|-:|-:|-:|-:|
|MomTop1\_80\_20|3093|0.1219|0.1769|-0.3318|0.6638|1.0431|0.3673|0.0598|1.8153|
|MomTop2\_35\_35|3093|0.1098|0.1652|-0.3681|0.6330|0.9736|0.2982|0.0633|1.5223|
|EW|3093|0.1120|0.1649|-0.3808|0.6462|0.9884|0.2942|0.0625|1.5773|

### Stationary-bootstrap summary — net CAGR (AR vs CS)

|Estimator|Strategy|mean|p05|p50|p95|n|
|-|-|-:|-:|-:|-:|-:|
|AR|MomTop1\_80\_20|0.1151|0.0346|0.1147|0.1957|1000|
|AR|MomTop2\_35\_35|0.1169|0.0452|0.1162|0.1929|1000|
|AR|EW|0.1180|0.0467|0.1176|0.1893|1000|
|CS|MomTop1\_80\_20|0.1182|0.0379|0.1176|0.1991|1000|
|CS|MomTop2\_35\_35|0.1186|0.0467|0.1181|0.1940|1000|
|CS|EW|0.1182|0.0468|0.1178|0.1895|1000|

### Stationary-bootstrap summary — net Sharpe ratio (AR vs CS)

|Estimator|Strategy|mean|p05|p50|p95|n|
|-|-|-:|-:|-:|-:|-:|
|AR|MomTop1\_80\_20|0.6716|0.2309|0.6693|1.1251|1000|
|AR|MomTop2\_35\_35|0.7228|0.2841|0.7051|1.2241|1000|
|AR|EW|0.7401|0.2895|0.7272|1.2457|1000|
|CS|MomTop1\_80\_20|0.6875|0.2464|0.6834|1.1422|1000|
|CS|MomTop2\_35\_35|0.7320|0.2977|0.7144|1.2312|1000|
|CS|EW|0.7410|0.2910|0.7280|1.2471|1000|

### Stationary-bootstrap summary — net Martin ratio (AR vs CS)

|Estimator|Strategy|mean|p05|p50|p95|n|
|-|-|-:|-:|-:|-:|-:|
|AR|MomTop1\_80\_20|1.3337|0.1231|1.0682|3.4735|1000|
|AR|MomTop2\_35\_35|1.5647|0.2158|1.2680|4.0746|1000|
|AR|EW|1.6399|0.2201|1.3523|4.2474|1000|
|CS|MomTop1\_80\_20|1.3894|0.1396|1.1200|3.5364|1000|
|CS|MomTop2\_35\_35|1.6006|0.2239|1.3126|4.1242|1000|
|CS|EW|1.6434|0.2214|1.3557|4.2523|1000|

## Interpretation

The best **realized** specification is **MomTop1\_80\_20**. In-sample, it outperforms the equal-weighted benchmark both **gross** and **net of proxy transaction costs**. However, once **historical risk-free adjustment**, **transaction-cost proxies**, and **stationary-bootstrap robustness checks** are introduced, the edge becomes materially weaker.

The evidence is therefore more consistent with a **theory-to-implementation gap** than with a clearly robust tradable alpha: the Arnott-style factor-momentum signal looks attractive in the realized sample, but its ETF-based implementation does **not** deliver clearly robust **net-of-costs** outperformance in bootstrap distributions, especially on **Sharpe** and **Martin** ratios.

## Current conclusions

* **Realized sample:** `MomTop1\\\_80\\\_20` remains the strongest specification.
* **Net-of-costs realized sample:** both AR and CS still leave `MomTop1\\\_80\\\_20` ahead of EW.
* **Bootstrap robustness:** once dependence-aware resampling and proxy trading frictions are accounted for, the strategy's advantage weakens materially.
* **Estimator sensitivity:** AR is somewhat more punitive than CS, but both estimators imply the same broad conclusion.

## Planned extensions

The current notebook already includes proxy transaction costs and historical risk-free adjustment. The next planned extension is:

1. a **risk-managed momentum overlay** *à la* **Barroso and Santa-Clara (2015)**, to test whether volatility-managed momentum improves this ETF-based factor-momentum implementation.

## Repository structure

```text
.
├── Factor\_Momentum.ipynb
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
   jupyter notebook Factor\_Momentum.ipynb
   ```

4. In the notebook, choose either:

   * `DATA\\\_SOURCE = "hdf"`, or
   * `DATA\\\_SOURCE = "yahoo"` for the public-data version.
5. Choose the risk-free proxy:

   * `RF\\\_SOURCE = "DGS3MO"` (default), or
   * `RF\\\_SOURCE = "SOFR"`.

## References

* Arnott, R., Clements, A., Kalesnik, V., and Linnainmaa, J. (2020). *Factor Momentum*.
* Politis, D. N., and Romano, J. P. (1994). *The Stationary Bootstrap*.
* Corwin, S. A., and Schultz, P. (2012). *A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices*.
* Abdi, F., and Ranaldo, A. (2017). *A Simple Estimation of Bid-Ask Spreads from Daily Close, High, and Low Prices*.
* Barroso, P., and Santa-Clara, P. (2015). *Momentum Has Its Moments*.

