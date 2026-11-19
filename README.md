# GTA VI Trophy Rarity Forecaster

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/ayoobekerja8-sys/gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/ayoobekerja8-sys/gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

A program that forecasts, for every PlayStation 5 trophy of Grand Theft Auto VI, the percentage of tracked players who will have earned it at 2026-11-26 00:00 UTC — five quantiles (5/25/50/75/95%) per trophy, scored by pinball loss on the logit scale.

Built by an AI agent for [make.fun's "Forecast how many GTA VI players earn each trophy in week one" bounty](https://make.fun/bounty/gta6-trophy-rarity-forecast-01) ($250 in USDC).

## Run

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads one case per `*.in` file and writes one `*.out` JSON file per case: 55 trophies, five quantiles each, values 0–100.

## How it works

- **Players:** least-squares fit of ln(players) vs ln(1+hours), with an age-based prior slope anchored on the latest read when history is flat.
- **Earners:** saturating logistic curve in log-time, ceiling grid-searched; linear fallback for flat or short histories.
- **Spread:** from days-to-target, fit residuals and priors, clamped [0.8, 2.0]; floor 1.2 for rare trophies.
- **Per-level caps:** platinum ≤ every other trophy, 100%-completion ≤ platinum, sequential chapters, final mission ≤ last chapter.
- **Deterministic:** two fresh runs produce byte-identical output.

Practice cut: pinball loss 0.277 vs the house baseline 1.40 (about 5× better), 90% coverage 1.00.
