# Pattern Experiment — Processed Dataset Release

This folder contains the **share-ready processed dataset** for the human experiment.
The package is intentionally data-only (no bundled analysis scripts).

## 1) Files Included in This Release

All files are under `data/`:

- `participants.csv` — participant-level summary
- `trials.csv` — trial-level records (`participant × trial`)
- `steps.csv` — step-level process log (one row per construction step)
- `helpers_actions.csv` — helper add/use action log
- `helper_definitions.csv` — helper macro definition and source tracing
- `solution_sequences.csv` — compact per-trial operation/symbolic sequence
- `key_metrics.csv` — summary metrics by pattern and trial order
- `dataset_metadata.json` — build metadata and row counts

Current metadata snapshot (`dataset_metadata.json`):

- `n_participants`: 30
- `n_trials_rows`: 420
- `n_steps_rows`: 1649
- `n_helpers_rows`: 4713
- `n_helper_definitions`: 486
- `n_solution_sequences`: 420

## 2) Intended Use

- Behavioral analysis at participant/trial/step level
- Helper creation/use analysis
- Solution-sequence comparison and clustering
- Reproduction of human-data analyses from processed tables

## 3) Data Provenance

- Source raw export: `experiment_data_v2 (1).json`
- Processing pipeline: `build_reproducible_dataset.py`
- Core property: symbolic and step-level traces preserve reconstruction-critical information

## 4) Core Conventions

### Identifiers and granularity

- `participant_uid`: canonical participant ID across files
- `trial_number`: trial order (`1..14`)
- `pattern_id`: target pattern index (`1..14`)

### Success filtering

- `success` is encoded as `0/1`
- Some analyses are all-trials, others are success-only

### Symbol conventions (`•`, `Hk`, `Wk`)

- `•` in operation text is a UI placeholder (input slot), not missing data
- `Hk` = helper symbol (saved pattern in helper library)
- `Wk` = intermediate symbol (within-trial temporary result)
- Prefer symbolic fields (for example `symbolic_expr`) over raw `operation_text` for modeling

## 5) Minimal Data Dictionary

### `participants.csv`

- `n_trials`, `n_success`
- `total_steps_success`, `mean_steps_success`
- `total_time_success_sec`, `mean_time_success_sec`

### `trials.csv`

- Timing: `time_spent_ms`, `time_spent_sec`
- Sequence: `sequence_ops_*`, `sequence_steps_*`
- Interaction counts: `helper_add_count`, `helper_use_count`, `preview_count`, `undo_count`, `button_click_count`
- Target reference: `target_pattern_json`

### `steps.csv`

- Order: `step_index`, `timestamp`, `interval_from_last`
- Operation: `op_fn_raw`, `op_canonical`, `operation_text`
- Operand typing: `operand_*_type` (`primitive/helper/intermediate/none`)
- Symbolic fields: `output_symbol`, `symbolic_expr`, `symbolic_expr_with_output`
- Replay field: `pattern_after_json`

### `helpers_actions.csv`

- `action=add` (helper created), `action=use` (helper used), `action=confirm` (preview confirm logs)
- Helper fields when available: `helper_id`, `pattern_key`, `pattern_json`, `timestamp`

### `solution_sequences.csv`

- Compact per-trial summary for fast sequence analysis
- Includes canonical op sequence + symbolic sequence + `solution_signature`

## 6) Quick Start (Python)

Run from inside `dataset_release/`:

```python
import pandas as pd

trials = pd.read_csv('data/trials.csv')
steps = pd.read_csv('data/steps.csv')
helpers = pd.read_csv('data/helpers_actions.csv')

# Success rate by trial number
print(trials.groupby('trial_number')['success'].mean())
```

## 7) Recommended Analysis Paths

1. Trial-level outcomes and timing: `trials.csv`
2. Process-level modeling/replay: `steps.csv`
3. Helper dynamics: `helpers_actions.csv` + `helper_definitions.csv`
4. Fast sequence mining: `solution_sequences.csv`

## 8) Maintenance and Script Updates

- This release remains a data-focused package.
- Analysis scripts and figure-generation scripts are maintained and updated continuously in the project workspace.
- If script or schema changes affect this release format, the README and metadata will be updated accordingly.

