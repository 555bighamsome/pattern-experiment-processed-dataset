# Pattern Experiment — Processed Dataset

Processed behavioral data from a pattern-construction experiment (30 participants × 14 trials).
Participants construct 10×10 binary grid patterns by composing primitive operations and reusable **helpers** (saved sub-programs).

---

## 1) Repository Structure

```
data/
  programs_and_helpers.json   ← structured per-participant per-trial programs & helper libraries
  programs_and_helpers.csv    ← flat CSV version (subset of fields)
  participants.csv            ← participant-level summary
  trials.csv                  ← trial-level records (participant × trial)
  steps.csv                   ← step-level process log (one row per construction step)
  helpers_actions.csv         ← helper add/use action log
  helper_definitions.csv      ← helper macro definitions and source tracing
  solution_sequences.csv      ← compact per-trial operation/symbolic sequence
  key_metrics.csv             ← summary metrics by pattern and trial order
  dataset_metadata.json       ← build metadata and row counts
plot_all_participants_v2.py   ← visualization script (generates per-participant PNG figures)
```

**30 participants**, **420 trials** (30 × 14), **1649 steps**, **486 helper definitions**.

---

## 2) Quick Start: `programs_and_helpers.json`

This is the **recommended entry point** for programmatic analysis. It contains every trial's solution program and the full helper library state, structured for easy lookup.

### Loading

```python
import json

with open("data/programs_and_helpers.json") as f:
    data = json.load(f)

# Access: data[participant_index][trial_number]
trial = data["1"]["2"]   # Participant 1, Trial 2
print(trial["program_symbolic"])
# → ["W1 = add(H2, H4)", "W2 = add(square, W1)"]
```

### Record Structure

Each `data[pid][trial]` record contains:

| Field | Type | Description |
|---|---|---|
| `participant_index` | int | Participant ID (1–30) |
| `trial_number` | int | Trial order (1–14) |
| `pattern_id` | int | Target pattern index (1–14) |
| `success` | bool | Whether the participant solved this trial |
| `program_ops` | list[str] | Ordered list of operation names, e.g. `["reflect_h", "add"]` |
| `program_symbolic` | list[str] | Symbolic program, e.g. `["W1 = reflect_h(line_h)", "W2 = add(line_h, W1)"]` |
| `n_steps` | int | Number of steps in the solution |
| `helpers_used_in_solution` | list[str] | Helper IDs invoked in this solution, e.g. `["H2", "H4"]` |
| `helpers_used_definitions` | list[obj] | Full definitions of used helpers (see below) |
| `helpers_created_this_trial` | list[obj] | Helpers saved during this trial |
| `helper_library_size` | int | Cumulative library size after this trial |
| `helper_library` | list[obj] | Full cumulative helper library snapshot |

### Helper object fields

Each helper object (in `helpers_used_definitions`, `helpers_created_this_trial`, `helper_library`) has:

| Field | Type | Description |
|---|---|---|
| `helper_id` | str | Unique ID per participant, e.g. `"H3"` |
| `macro_str` | str | The helper's recipe — a `;`-separated symbolic program, e.g. `"W1 = reflect_h(line_h) ; W2 = add(line_h, W1)"` |
| `created_on_trial` | int | *(only in `helpers_used_definitions`)* Which trial this helper was first created |

### Usage Examples

```python
import json

with open("data/programs_and_helpers.json") as f:
    data = json.load(f)

# Example 1: Get all programs for one participant
for tn in sorted(data["5"].keys(), key=int):
    trial = data["5"][tn]
    print(f"Trial {tn}: {trial['program_symbolic']}  (lib size: {trial['helper_library_size']})")

# Example 2: Count helper reuse across all participants
from collections import Counter
reuse = Counter()
for pid in data:
    for tn in data[pid]:
        for hid in data[pid][tn]["helpers_used_in_solution"]:
            reuse[(pid, hid)] += 1
print("Most reused helpers:", reuse.most_common(10))

# Example 3: Compare helper library growth curves
for pid in ["1", "10", "20"]:
    sizes = [data[pid][str(t)]["helper_library_size"] for t in range(1, 15)]
    print(f"P{pid}: {sizes}")

# Example 4: Extract all unique operations used
all_ops = set()
for pid in data:
    for tn in data[pid]:
        all_ops.update(data[pid][tn]["program_ops"])
print("Operations:", sorted(all_ops))
```

---

## 3) `programs_and_helpers.csv` (Flat Version)

A flat CSV with one row per trial (420 rows). Easier for quick inspection in Excel/R but contains less detail than the JSON.

| Column | Description |
|---|---|
| `participant_index` | Participant ID |
| `trial_number` | Trial order (1–14) |
| `pattern_id` | Target pattern index |
| `success` | `True`/`False` |
| `n_steps` | Number of solution steps |
| `program_ops` | Pipe-separated operation names, e.g. `reflect_h\|add` |
| `program_symbolic` | Pipe-separated symbolic steps, e.g. `W1 = reflect_h(line_h)\|W2 = add(line_h, W1)` |
| `helpers_used` | Comma-separated helper IDs used |
| `helpers_used_expanded` | Comma-separated `Hk:macro_str` with full recipes |
| `helpers_created_this_trial` | Comma-separated helper IDs created |
| `helper_library_size` | Cumulative library size |

**Note:** The CSV does not include the cumulative `helper_library` snapshot. Use the JSON for full library tracking.

---

## 4) Key Concepts

### Operations (primitives)

The available operations that construct patterns on a 10×10 binary grid:

- `add` — pixel-wise OR (union)
- `subtract` — pixel-wise difference
- `overlap` — pixel-wise AND (intersection)
- `invert` — flip all cells
- `reflect_h` — horizontal reflection
- `reflect_v` — vertical reflection

### Operands

- **Primitives**: built-in base patterns — `line_h`, `line_v`, `diag`, `square`
- **Helpers** (`Hk`): reusable saved sub-programs from the participant's growing library
- **Intermediates** (`Wk`): temporary within-trial results (W1, W2, …), numbered per step

### Symbolic Program

Each trial's solution is a sequence of symbolic expressions:
```
W1 = reflect_h(line_h)          ← step 1: reflect line_h horizontally → save as W1
W2 = add(line_h, W1)            ← step 2: union of line_h and W1 → W2
W3 = add(H4, W2)                ← step 3: uses helper H4 and intermediate W2
```

### Helpers and `macro_str`

A helper is a saved sub-program. Its `macro_str` is the recipe that generates it:
```
"W1 = reflect_h(line_h) ; W2 = add(line_h, W1)"
```
- Steps are separated by ` ; `
- The helper's output is always the **last step's result**
- Helpers persist across trials (cumulative library)
- New helpers can reference earlier helpers via `Hk` symbols

---

## 5) Other Data Files

### `participants.csv`

One row per participant. Summary statistics:
- `n_trials`, `n_success` — trial counts
- `total_steps_success`, `mean_steps_success` — step counts (success trials only)
- `total_time_success_sec`, `mean_time_success_sec` — timing

### `trials.csv`

One row per participant × trial (420 rows):
- Timing: `time_spent_ms`, `time_spent_sec`
- Operation sequence: `sequence_ops_*`, `sequence_steps_*`
- Interaction counts: `helper_add_count`, `helper_use_count`, `preview_count`, `undo_count`
- Target reference: `target_pattern_json` (10×10 grid as JSON array)

### `steps.csv`

One row per construction step (1649 rows):
- Order: `step_index`, `timestamp`, `interval_from_last`
- Operation: `op_fn_raw`, `op_canonical`, `operation_text`
- Operand typing: `operand_*_type` (`primitive` / `helper` / `intermediate` / `none`)
- Symbolic: `output_symbol`, `symbolic_expr`, `symbolic_expr_with_output`
- Grid state: `pattern_after_json` (10×10 grid after this step)

### `helpers_actions.csv`

Log of all helper interactions:
- `action=add` — helper created (includes `pattern_json`: the 10×10 grid output)
- `action=use` — helper invoked in a solution step
- `action=confirm` — preview confirmation events

### `helper_definitions.csv`

One row per unique helper definition (486 rows):
- `helper_id`, `macro_str`, `output_symbol`
- `created_on_trial` — which trial it was first saved

### `solution_sequences.csv`

Compact per-trial summary (420 rows):
- Canonical op sequence + symbolic sequence + `solution_signature`

### `key_metrics.csv`

Aggregated metrics by pattern and trial order.

### `dataset_metadata.json`

Build metadata and row counts for verification.

---

## 6) Visualization Script

**`plot_all_participants_v2.py`** generates one PNG per participant (P01.png … P30.png) showing:

- **Solution row**: Target grid → Step 1 → Step 2 → … → Final grid (10×10 visual grids)
- **Library row**: Helper library grids at each trial, color-coded:
  - 🟢 Green border = newly created this trial
  - 🔴 Red border = used in this trial's solution
- Symbolic annotations and step counts

**Requirements**: Python 3, matplotlib, numpy

```bash
# Run from the repo root (data/ must be in place)
python plot_all_participants_v2.py
# Output: participant_solutions_v2/P01.png ... P30.png
```

---

## 7) Data Provenance

- Source raw export: `experiment_data_v2 (1).json`
- Processing pipeline: `build_reproducible_dataset.py`
- Symbolic and step-level traces preserve all reconstruction-critical information

