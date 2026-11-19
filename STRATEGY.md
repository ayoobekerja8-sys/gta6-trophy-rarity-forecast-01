# Forecast strategy

The program reads every case file and uses only its recorded timestamps, player counts, trophy rates, target, and release date. Consecutive duplicate reads collapse to their first timestamp. Player growth is modeled as a least-squares line in log players versus log one plus hours since release. When the history has not recorded distinct player counts, a launch-age-based slope prior is used; predicted players are bounded by the latest count and fifty times that count.

For each trophy, observed rates become estimated earner counts. The program fits a saturating logistic curve in log time, selecting its ceiling from a 12-point logarithmic grid. Sparse or constant earner histories use a linear horizon-based fallback. The projected count is bounded by the projected player count, then converted to a median rate. A recorded rate of 100% remains at 100%.

The five forecasts are logistic transforms of the median logit plus normal-score offsets at the requested 5th, 25th, 50th, 75th, and 95th percentiles. Their shared spread combines horizon uncertainty, fit residuals (or a larger fallback allowance), and a prior allowance. Values are rounded to four decimal places and sorted. Dependency caps enforce chapter progression, completion below platinum, and platinum below all other trophies.

The largest uncertainties are future refresh timing and scale: Exophase can update tracked players and rates in discrete jumps, while the practice histories show no movement before a large refresh. Trophy earning behavior over a full week is also not identified by a short launch window, so the fitted curve and fallback are extrapolations rather than direct evidence of a stable long-run pattern.
