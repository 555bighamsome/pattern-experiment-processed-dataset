# Experiment 2 (Pilot) — Processed Dataset

**30 participants × 16 stimuli = 480 trials, 2163 steps.**

Participants construct 10×10 binary grid patterns by composing primitive operations and reusable **helpers** (saved sub-programs).

---

## Data Files

### `participants.csv`

One row per participant (30 rows):

| Column | Description |
|---|---|
| `participant_uid` | Unique participant identifier |
| `participant_index` | Sequential index (1–30) |
| `score` | Number of successful trials (out of 16) |
| `n_trials` | Total trials completed |
| `total_time_sec` | Total time across all trials (seconds) |
| `mean_time_per_trial_sec` | Average time per trial |
| `submission_time` | Submission timestamp |

### `trials.csv`

One row per participant × trial (480 rows). Flat columns with interaction counts:

| Column | Description |
|---|---|
| `participant_uid` | Participant identifier |
| `participant_index` | Sequential index (1–30) |
| `trial_number` | Trial order (1–16) |
| `test_name` | Stimulus name (e.g. `Stimuli-01`) |
| `success` | 1 = solved, 0 = failed |
| `steps_count` | Number of construction steps |
| `time_spent_sec` | Time spent (seconds) |
| `confirmed_helper_steps` | Steps that used a helper operand |
| `helper_step_rate` | Percentage of steps using helpers (0–100) |
| `helpers_created` | Number of unique helpers created this trial |
| `helper_add_count` | Number of helper add events |
| `helper_remove_count` | Number of helper remove events |
| `helper_click_count` | Number of helper click events |
| `preview_confirm_count` | Number of preview confirmations |
| `preview_cancel_count` | Number of preview cancellations |
| `undo_count` | Number of undo actions |
| `primitive_usage_count` | Number of primitive operand uses in steps |
| `helper_usage_count` | Number of helper operand uses in steps |
| `workspace_reuse_count` | Number of workspace/intermediate reuses in steps |
| `target_pattern_json` | JSON: 10×10 target pattern for this trial |

### `steps.csv`

One row per construction step (2163 rows). Ordered by participant → trial → step index:

| Column | Description |
|---|---|
| `participant_uid` | Participant identifier |
| `participant_index` | Sequential index (1–30) |
| `trial_number` | Trial order (1–16) |
| `success` | 1 = trial was solved, 0 = failed |
| `step_index` | Step order within trial (0-based) |
| `step_id` | Original step identifier |
| `timestamp` | Step timestamp (ms) |
| `interval_from_last` | Time since previous step (ms) |
| `op_fn` | Raw operation function name |
| `op_canonical` | Canonical operation name |
| `operation_text` | Human-readable operation description |
| `operand_a_type` | Type of first operand (`primitive`/`helper`/`intermediate`/`none`) |
| `operand_b_type` | Type of second operand (`primitive`/`helper`/`intermediate`/`none`) |
| `operand_input_type` | Type of input operand (for unary operations) |
| `helper_operand_patterns_json` | JSON: 10×10 grid patterns of helper operands used in this step (empty if no helpers) |
| `pattern_after_json` | JSON: 10×10 grid state after this step |

### `helpers_actions.csv`

Log of all helper/favorite interactions (7561 rows):

| Column | Description |
|---|---|
| `participant_uid` | Participant identifier |
| `participant_index` | Sequential index (1–30) |
| `trial_number` | Trial order (1–16) |
| `success` | 1 = trial was solved, 0 = failed |
| `source` | Event source: `favorite` or `preview` |
| `action` | Action type: `add`, `remove`, `click`, `confirm`, `cancel` |
| `timestamp` | Event timestamp (ms) |
| `favorite_id` | Helper/favorite ID (for add/click events) |
| `context` | Action context (e.g. event source detail) |
| `operation` | Operation that produced the helper (for add events) |
| `pattern_json` | JSON: 10×10 grid pattern of the helper (for add/click events) |

### `targets.json`

Array of 16 target patterns (10×10 binary grids), indexed 0–15.

### `key_metrics.csv`

By-stimulus summary: success rate, mean steps, mean time.

### `dataset_metadata.json`

Row counts and build metadata for verification.

---

## Loading Example

```python
import csv, json

# Load trials with interaction counts
trials = []
with open("data/trials.csv") as f:
    for row in csv.DictReader(f):
        row['success'] = bool(int(row['success']))
        row['steps_count'] = int(row['steps_count'])
        row['time_spent_sec'] = float(row['time_spent_sec'])
        row['target_pattern'] = json.loads(row['target_pattern_json'])
        trials.append(row)

# Load helper add patterns from helpers_actions.csv
from collections import defaultdict
helper_adds = defaultdict(list)
with open("data/helpers_actions.csv") as f:
    for row in csv.DictReader(f):
        if row['action'] == 'add' and row['pattern_json']:
            key = (row['participant_uid'], int(row['trial_number']))
            helper_adds[key].append(json.loads(row['pattern_json']))

# Load confirmed helper patterns from steps.csv
confirmed = defaultdict(list)
with open("data/steps.csv") as f:
    for row in csv.DictReader(f):
        if row['helper_operand_patterns_json']:
            key = (row['participant_uid'], int(row['trial_number']))
            for pat in json.loads(row['helper_operand_patterns_json']):
                confirmed[key].append(pat)
```

---

## Visualization

**`e2_pilot_figures.py`** generates publication-ready figures from the processed CSVs:

| Figure | Description |
|---|---|
| Panel A | Accuracy by stimulus (bar chart with SEM) |
| Panel B | Time and steps by stimulus (line plots with individual dots) |
| Panel C | Helper use rate by stimulus |
| Panel D | Helper distribution heatmap (ranked patterns per trial, with oracle/target marking) |
| Panel E | Top 20 most-added helpers (lollipop chart) |
| Panel F | Accuracy across trials (line with individual dots) |
| Helper adds | Helper add counts by stimulus |
| Confirmed-use | Confirmed helper use distribution |
| Most-used | Top 20 most-used helpers |
| Final libraries | Per-participant final helper library state |

Oracle helpers (X diagonal, vertical bar, cross, left triangle) and their transforms (invert, h_flip, v_flip, transpose) are highlighted with colored borders:
- 🟢 Green = oracle helper
- 🟣 Purple = oracle-derived (transform of an oracle)
- 🟠 Orange = target pattern

```bash
python e2_pilot_figures.py
# Output: figures/ and figures/paper_panels/
```

**Requirements**: Python 3, matplotlib, numpy

---

## Data Provenance

- Source raw export: `experiment2_maindata.json`
- Step-level traces and helper action logs preserve all reconstruction-critical information
