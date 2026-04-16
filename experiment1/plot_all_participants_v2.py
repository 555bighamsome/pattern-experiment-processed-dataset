#!/usr/bin/env python3
"""
Generate one PNG per participant showing:
  - Top section per trial: Target → Step1 → Step2 → ... → Final  (10×10 grids)
  - Bottom section per trial: current helper library as small grids
  - Symbolic annotations, helper usage/creation markers

Output: participant_solutions_v2/P01.png ... P30.png
"""

import csv, json, os, re
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import ListedColormap
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
STEPS_CSV   = "dataset_release/data/steps.csv"
TRIALS_CSV  = "dataset_release/data/trials.csv"
HELPERS_CSV = "dataset_release/data/helpers_actions.csv"
PH_JSON     = "dataset_release/data/programs_and_helpers.json"
OUT_DIR     = "participant_solutions_v2"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load data ────────────────────────────────────────────────────────────────
with open(PH_JSON) as f:
    ph_data = json.load(f)

# Target patterns
targets = {}
with open(TRIALS_CSV) as f:
    for row in csv.DictReader(f):
        pid, tn = int(row["participant_index"]), int(row["trial_number"])
        targets[(pid, tn)] = json.loads(row["target_pattern_json"])

# Step-level pattern snapshots
step_patterns = {}
with open(STEPS_CSV) as f:
    for row in csv.DictReader(f):
        pid, tn, si = int(row["participant_index"]), int(row["trial_number"]), int(row["step_index"])
        key = (pid, tn)
        if key not in step_patterns:
            step_patterns[key] = []
        step_patterns[key].append({
            "si": si,
            "sym": row.get("symbolic_expr_with_output", ""),
            "pat": json.loads(row["pattern_after_json"]),
        })
for k in step_patterns:
    step_patterns[k].sort(key=lambda x: x["si"])

# Helper pattern grids: (participant_index, helper_id) -> 10×10 grid
helper_grids = {}
with open(HELPERS_CSV) as f:
    for row in csv.DictReader(f):
        if row["action"] == "add" and row.get("pattern_json", ""):
            pid = int(row["participant_index"])
            hid = row["helper_id"]
            helper_grids[(pid, hid)] = json.loads(row["pattern_json"])

participants = sorted(ph_data.keys(), key=int)
N_TRIALS = 14

# ── Drawing helpers ──────────────────────────────────────────────────────────
grid_cmap = ListedColormap(["#ffffff", "#2d3436"])

def draw_grid(ax, grid, border_color=None, border_width=1.5):
    arr = np.array(grid)
    ax.imshow(arr, cmap=grid_cmap, vmin=0, vmax=1, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(border_width if border_color else 0.3)
        spine.set_color(border_color if border_color else "#ccc")

def draw_grid_small(ax, grid, border_color=None, border_width=1.0):
    """Same but expects smaller axes."""
    draw_grid(ax, grid, border_color, border_width)

# ── Generate figures ─────────────────────────────────────────────────────────
for pid_str in participants:
    pid = int(pid_str)
    print(f"Generating P{pid:02d}...")

    # Pre-compute sizes
    max_steps = 0
    max_lib = 0
    for tn in range(1, N_TRIALS + 1):
        steps = step_patterns.get((pid, tn), [])
        max_steps = max(max_steps, len(steps))
        trial_data = ph_data[pid_str].get(str(tn), {})
        max_lib = max(max_lib, trial_data.get("helper_library_size", 0))

    # Layout: each trial gets 2 sub-rows: (solution grids) + (library grids)
    # Width: enough for max(1+max_steps, max_lib) grids + text
    n_sol_cols = 1 + max_steps  # target + steps
    n_lib_cols = max(max_lib, 1)
    total_cols = max(n_sol_cols, n_lib_cols)

    # Figure size
    row_height_sol = 1.1   # solution row
    row_height_lib = 0.65  # library row
    row_height_gap = 0.15
    per_trial_h = row_height_sol + row_height_lib + row_height_gap
    fig_h = N_TRIALS * per_trial_h + 1.2
    fig_w = max(total_cols * 0.82 + 3.5, 14)

    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.suptitle(f"Participant {pid} — Solution Process & Helper Library",
                 fontsize=14, fontweight="bold", y=0.998)

    # Height ratios: for each trial -> [solution_row, lib_row, gap]
    height_ratios = []
    for _ in range(N_TRIALS):
        height_ratios.extend([row_height_sol, row_height_lib, row_height_gap])
    # remove last gap
    height_ratios = height_ratios[:-1]

    gs_main = gridspec.GridSpec(len(height_ratios), 1,
                                figure=fig, height_ratios=height_ratios,
                                hspace=0, left=0.01, right=0.99,
                                top=0.975, bottom=0.015)

    for tn in range(1, N_TRIALS + 1):
        trial_data = ph_data[pid_str].get(str(tn), {})
        steps = step_patterns.get((pid, tn), [])
        tgt = targets.get((pid, tn), [[0]*10]*10)
        success = trial_data.get("success", False)
        sym_prog = trial_data.get("program_symbolic", [])
        helpers_used = set(trial_data.get("helpers_used_in_solution", []))
        helpers_created = set(h["helper_id"] for h in trial_data.get("helpers_created_this_trial", []))
        lib = trial_data.get("helper_library", [])
        lib_size = trial_data.get("helper_library_size", 0)
        pattern_id = trial_data.get("pattern_id", tn)

        row_base = (tn - 1) * 3  # index into height_ratios

        # ── Solution row ─────────────────────────────────────
        gs_sol = gridspec.GridSpecFromSubplotSpec(
            1, total_cols + 2,  # +2 for text at right
            subplot_spec=gs_main[row_base],
            wspace=0.08)

        # Target
        ax_tgt = fig.add_subplot(gs_sol[0, 0])
        draw_grid(ax_tgt, tgt, border_color="#0984e3", border_width=2)
        ax_tgt.set_title(f"T{tn} P{pattern_id}", fontsize=7, color="#0984e3",
                         fontweight="bold", pad=2)

        # Steps
        for si, step in enumerate(steps):
            ax_s = fig.add_subplot(gs_sol[0, 1 + si])
            is_final = (si == len(steps) - 1)
            bc = "#00b894" if (is_final and success) else ("#e17055" if is_final else None)
            bw = 2 if is_final else 1
            draw_grid(ax_s, step["pat"], border_color=bc, border_width=bw)
            sym_short = step["sym"]
            if len(sym_short) > 25:
                sym_short = sym_short[:23] + "…"
            ax_s.set_title(sym_short, fontsize=5, color="#555", pad=1)

        # Text summary at right
        ax_txt = fig.add_subplot(gs_sol[0, total_cols:total_cols + 2])
        ax_txt.axis("off")
        status = "✓" if success else "✗"
        txt_lines = [f"{status} {len(steps)} steps"]
        for i, s in enumerate(sym_prog):
            s_fmt = re.sub(r'\b(H\d+)\b', r'[\1]', s)
            txt_lines.append(f" {i+1}. {s_fmt}")
        if helpers_used:
            txt_lines.append(f"Used: {', '.join(sorted(helpers_used))}")
        if helpers_created:
            txt_lines.append(f"New: {', '.join(sorted(helpers_created))}")
        ax_txt.text(0.0, 0.5, "\n".join(txt_lines), transform=ax_txt.transAxes,
                    fontsize=5, fontfamily="monospace", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#f8f9fa", ec="#ddd", lw=0.4))

        # ── Library row ──────────────────────────────────────
        gs_lib = gridspec.GridSpecFromSubplotSpec(
            1, total_cols + 2,
            subplot_spec=gs_main[row_base + 1],
            wspace=0.08)

        # Label
        ax_lab = fig.add_subplot(gs_lib[0, 0])
        ax_lab.axis("off")
        ax_lab.text(0.5, 0.5, f"Lib({lib_size})", fontsize=6, ha="center", va="center",
                    fontweight="bold", color="#636e72", transform=ax_lab.transAxes)

        # Helper grids
        for hi, h in enumerate(lib):
            hid = h["helper_id"]
            col = 1 + hi
            if col >= total_cols + 2:
                break
            ax_h = fig.add_subplot(gs_lib[0, col])
            hgrid = helper_grids.get((pid, hid))
            if hgrid:
                is_new = hid in helpers_created
                is_used = hid in helpers_used
                if is_new:
                    bc, bw = "#55efc4", 1.8
                elif is_used:
                    bc, bw = "#d63031", 1.8
                else:
                    bc, bw = "#ccc", 0.5
                draw_grid_small(ax_h, hgrid, border_color=bc, border_width=bw)
                ax_h.set_title(hid, fontsize=4, color="#d63031" if is_used else ("#00b894" if is_new else "#999"), pad=1)
            else:
                ax_h.axis("off")
                ax_h.text(0.5, 0.5, hid, fontsize=4, ha="center", va="center",
                          transform=ax_h.transAxes, color="#999")

        # Hide remaining library cols
        for ci in range(1 + len(lib), total_cols + 2):
            ax_e = fig.add_subplot(gs_lib[0, ci])
            ax_e.axis("off")

    # Legend
    legend_patches = [
        mpatches.Patch(facecolor="#fff", edgecolor="#0984e3", linewidth=2, label="Target"),
        mpatches.Patch(facecolor="#fff", edgecolor="#00b894", linewidth=2, label="Final (success)"),
        mpatches.Patch(facecolor="#fff", edgecolor="#e17055", linewidth=2, label="Final (fail)"),
        mpatches.Patch(facecolor="#55efc4", edgecolor="#55efc4", label="Library: new this trial"),
        mpatches.Patch(facecolor="#fff", edgecolor="#d63031", linewidth=2, label="Library: used in solution"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=5, fontsize=6.5,
               frameon=True, fancybox=True, bbox_to_anchor=(0.5, 0.001))

    out_path = os.path.join(OUT_DIR, f"P{pid:02d}.png")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

print(f"\nDone! {len(participants)} figures in {OUT_DIR}/")
