# Pattern Experiment — Processed Dataset

Processed behavioral data from two pattern-construction experiments.
Participants construct 10×10 binary grid patterns by composing primitive operations and reusable **helpers** (saved sub-programs).

| | Experiment 1 | Experiment 2 |
|---|---|---|
| Participants | 30 | 30 |
| Stimuli | 14 | 16 |
| Trials | 420 | 480 |
| Steps | 1,649 | 2,163 |

See each experiment's README for detailed data documentation:
- **[Experiment 1](experiment1/README.md)** — 30 × 14 trials, symbolic programs, helper library tracking
- **[Experiment 2](experiment2/README.md)** — 30 × 16 trials (pilot), processed behavioral dataset and figures

---

## Repository Structure

```
experiment1/
  README.md                     ← detailed data documentation
  data/
    programs_and_helpers.json   ← structured per-participant per-trial programs & helper libraries
    programs_and_helpers.csv    ← flat CSV version (subset of fields)
    participants.csv            ← participant-level summary
    trials.csv                  ← trial-level records (participant × trial)
    steps.csv                   ← step-level process log (1649 rows)
    helpers_actions.csv         ← helper add/use action log
    helper_definitions.csv      ← helper macro definitions and source tracing
    solution_sequences.csv      ← compact per-trial operation/symbolic sequence
    key_metrics.csv             ← summary metrics by pattern and trial order
    dataset_metadata.json       ← build metadata and row counts
  plot_all_participants_v2.py   ← visualization script (per-participant PNG figures)

experiment2/
  README.md                     ← detailed data documentation
  data/
    participants.csv            ← participant-level summary (30 rows)
    trials.csv                  ← trial-level records with interaction counts (480 rows)
    steps.csv                   ← step-level process log (2163 rows)
    helpers_actions.csv         ← helper interaction log (7561 rows)
    targets.json                ← 16 target patterns (10×10 grids)
    key_metrics.csv             ← by-stimulus success rates and means
    dataset_metadata.json       ← dataset metadata and row counts
  e2_pilot_figures.py           ← visualization script (generates all paper panel figures)
```

---

## Data Provenance

- **Experiment 1**: Source raw export `experiment_data_v2 (1).json`, processed by `build_reproducible_dataset.py`
- **Experiment 2**: Source raw export `experiment2_maindata.json`
- Symbolic and step-level traces preserve all reconstruction-critical information

