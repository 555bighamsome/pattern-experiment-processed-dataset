#!/usr/bin/env python3
"""
Experiment 2 Figures — reads from processed CSVs (no raw JSON needed).

Data files expected in ./data/:
  - participants.csv
  - trials.csv  (with JSON columns for pattern data)
  - targets.json
"""

import csv
import json
import math
import os
from collections import Counter, defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Patch


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'figures')
PAPER_PANEL_DIR = os.path.join(OUTPUT_DIR, 'paper_panels')

FILL_COLOR = '#163E78'
GRID_COLOR = '#d9e2ec'
PRIMARY_BLUE = '#173F7A'
SECONDARY_BLUE = '#4F8FBE'
LIGHT_BLUE = '#DCEAF6'
PALE_BLUE = '#EEF5FB'
TEXT_COLOR = '#1F2937'
MUTED_TEXT = '#5B6472'
TARGET_EDGE = '#FF6B00'
ORACLE_EDGE = '#2CA24F'
ORACLE_DERIV_EDGE = '#9B59B6'
FAMILY_EDGE = '#A8B6C8'


# ---------------------------------------------------------------------------
# Data loading (from processed CSVs)
# ---------------------------------------------------------------------------

def load_targets():
    with open(os.path.join(DATA_DIR, 'targets.json'), encoding='utf-8') as f:
        return json.load(f)


def load_participants():
    # Read participants
    participants_by_uid = {}
    with open(os.path.join(DATA_DIR, 'participants.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            uid = row['participant_uid']
            participants_by_uid[uid] = {
                'id': uid,
                'pid': uid,
                'score': int(row['score']),
                'seq': 'row-wise',
                'time': float(row['total_time_sec']),
                'submission_time': row['submission_time'],
                'trials': {},  # keyed by trial_number, converted to list later
            }

    # Read trials (flat columns)
    with open(os.path.join(DATA_DIR, 'trials.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            uid = row['participant_uid']
            tn = int(row['trial_number'])
            participants_by_uid[uid]['trials'][tn] = {
                'trial': tn,
                'testName': row['test_name'],
                'success': bool(int(row['success'])),
                'stepsCount': int(row['steps_count']),
                'timeSpent': float(row['time_spent_sec']),
                'confirmedHelperSteps': int(row['confirmed_helper_steps']),
                'helperStepRate': float(row['helper_step_rate']),
                'helpersCreated': int(row['helpers_created']),
                'targetPattern': json.loads(row['target_pattern_json']),
                # Populated below from helpers_actions.csv and steps.csv
                'helperPatterns': [],
                'helperAddPatterns': [],
                'confirmedHelperPatterns': [],
                'favoriteActions': [],
            }

    # Read helpers_actions.csv → reconstruct helperPatterns, helperAddPatterns, favoriteActions
    with open(os.path.join(DATA_DIR, 'helpers_actions.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['source'] != 'favorite':
                continue
            uid = row['participant_uid']
            tn = int(row['trial_number'])
            trial = participants_by_uid[uid]['trials'][tn]

            action = row['action']
            pattern_json = row['pattern_json']
            pattern = json.loads(pattern_json) if pattern_json else None

            # Rebuild favoriteActions list
            fa = {'action': action, 'timestamp': int(row['timestamp']) if row['timestamp'] else 0}
            if row['favorite_id']:
                fa['favoriteId'] = row['favorite_id']
            if row['context']:
                fa['context'] = row['context']
            if row['operation']:
                fa['operation'] = row['operation']
            if pattern is not None:
                fa['pattern'] = pattern
            trial['favoriteActions'].append(fa)

            # Rebuild helperAddPatterns (all add events, with dupes)
            if action == 'add' and pattern is not None:
                trial['helperAddPatterns'].append(pattern)

    # Deduplicate add patterns → helperPatterns
    for p in participants_by_uid.values():
        for trial in p['trials'].values():
            seen = set()
            for pat in trial['helperAddPatterns']:
                sig = json.dumps(pat, separators=(',', ':'))
                if sig not in seen:
                    seen.add(sig)
                    trial['helperPatterns'].append(pat)

    # Read steps.csv → reconstruct confirmedHelperPatterns
    with open(os.path.join(DATA_DIR, 'steps.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            helper_json = row['helper_operand_patterns_json']
            if not helper_json:
                continue
            uid = row['participant_uid']
            tn = int(row['trial_number'])
            trial = participants_by_uid[uid]['trials'][tn]
            for pat in json.loads(helper_json):
                sig = json.dumps(pat, separators=(',', ':'))
                existing_sigs = {json.dumps(p, separators=(',', ':'))
                                 for p in trial['confirmedHelperPatterns']}
                if sig not in existing_sigs:
                    trial['confirmedHelperPatterns'].append(pat)

    # Convert trials dict → sorted list
    for p in participants_by_uid.values():
        p['trials'] = sorted(p['trials'].values(), key=lambda t: t['trial'])

    # Sort participants by submission_time (same as original)
    participants = list(participants_by_uid.values())
    participants.sort(key=lambda p: p['submission_time'])
    return participants


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def setup_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 9,
        'axes.labelsize': 10,
        'axes.titlesize': 11,
        'xtick.labelsize': 8,
        'ytick.labelsize': 9,
        'axes.linewidth': 0.8,
        'axes.labelcolor': TEXT_COLOR,
        'xtick.color': TEXT_COLOR,
        'ytick.color': TEXT_COLOR,
        'text.color': TEXT_COLOR,
        'legend.frameon': False,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.08,
    })


def apply_axis_style(ax, grid_axis='y'):
    if grid_axis in ('x', 'both'):
        ax.xaxis.grid(True, color=GRID_COLOR, linestyle='-', linewidth=0.6, alpha=0.7)
    if grid_axis in ('y', 'both'):
        ax.yaxis.grid(True, color=GRID_COLOR, linestyle='-', linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(TEXT_COLOR)
    ax.spines['bottom'].set_color(TEXT_COLOR)
    ax.tick_params(axis='both', width=0.8, length=6, color=TEXT_COLOR)


def add_family_guides(ax, y_min=0, y_max=1):
    family_spans = [
        (0.5, 4.5),
        (4.5, 8.5),
        (8.5, 12.5),
        (12.5, 16.5),
    ]
    for index, (left, right) in enumerate(family_spans):
        if index % 2 == 0:
            ax.axvspan(left, right, color=PALE_BLUE, alpha=0.55, zorder=0)
    for boundary in (4.5, 8.5, 12.5):
        ax.axvline(boundary, color=FAMILY_EDGE, linewidth=1.0, linestyle='--', alpha=0.9, zorder=1)


def add_caption_title(ax, title):
    ax.set_title(title, loc='left', fontweight='bold', fontsize=11, pad=6)


def add_panel_label(fig, label, x=0.012, y=0.988):
    fig.text(
        x,
        y,
        label,
        ha='left',
        va='top',
        fontsize=14,
        fontweight='bold',
        color=TEXT_COLOR,
    )


# ---------------------------------------------------------------------------
# Rendering utilities
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def create_pattern_image(pattern, cell_size=8):
    fill_rgb = hex_to_rgb(FILL_COLOR)
    grid_rgb = hex_to_rgb(GRID_COLOR)
    grid_size = 10
    img_size = grid_size * cell_size + 1
    img = np.ones((img_size, img_size, 3), dtype=np.uint8) * 255

    for row in range(grid_size):
        for col in range(grid_size):
            y1 = row * cell_size + 1
            y2 = (row + 1) * cell_size + 1
            x1 = col * cell_size + 1
            x2 = (col + 1) * cell_size + 1
            if pattern[row][col] == 1:
                img[y1:y2, x1:x2] = fill_rgb

    img[0, :] = grid_rgb
    img[:, 0] = grid_rgb

    for i in range(grid_size + 1):
        pos = i * cell_size
        for j in range(img_size):
            row_above = i - 1 if i > 0 else -1
            row_below = i if i < grid_size else -1
            col_idx = (j - 1) // cell_size if j > 0 else 0
            col_idx = min(col_idx, grid_size - 1)

            draw_h = False
            if row_above >= 0 and pattern[row_above][col_idx] == 0:
                draw_h = True
            if row_below >= 0 and row_below < grid_size and pattern[row_below][col_idx] == 0:
                draw_h = True
            if draw_h and pos < img_size:
                img[pos, j] = grid_rgb

        for j in range(img_size):
            col_left = i - 1 if i > 0 else -1
            col_right = i if i < grid_size else -1
            row_idx = (j - 1) // cell_size if j > 0 else 0
            row_idx = min(row_idx, grid_size - 1)

            draw_v = False
            if col_left >= 0 and pattern[row_idx][col_left] == 0:
                draw_v = True
            if col_right >= 0 and col_right < grid_size and pattern[row_idx][col_right] == 0:
                draw_v = True
            if draw_v and pos < img_size:
                img[j, pos] = grid_rgb

    return img


def patterns_equal(pattern_a, pattern_b):
    return all(
        pattern_a[row][col] == pattern_b[row][col]
        for row in range(10)
        for col in range(10)
    )


def pattern_signature(pattern):
    return json.dumps(pattern, separators=(',', ':'))


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def sem(values):
    if len(values) <= 1:
        return 0.0
    return float(np.std(values, ddof=1) / math.sqrt(len(values)))


def std_dev(values):
    if len(values) <= 1:
        return 0.0
    return float(np.std(values, ddof=1))


def median_iqr(values):
    if not values:
        return 0.0, 0.0, 0.0
    arr = np.asarray(values, dtype=float)
    return (
        float(np.median(arr)),
        float(np.percentile(arr, 25)),
        float(np.percentile(arr, 75)),
    )


# ---------------------------------------------------------------------------
# Figure I/O
# ---------------------------------------------------------------------------

def save_figure(fig, basename, output_dir=None, panel_label=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    if panel_label:
        add_panel_label(fig, panel_label)
    os.makedirs(output_dir, exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(
            os.path.join(output_dir, f'{basename}.{ext}'),
            format=ext,
            bbox_inches='tight',
            facecolor='white',
        )
    plt.close(fig)


def add_thumbnail_strip(fig, patterns, rect, show_codes=True, zoom=0.38, image_y=0.40, label_y=0.86):
    ax = fig.add_axes(rect)
    ax.set_xlim(0.3, len(patterns) + 0.7)
    ax.set_ylim(0, 1)
    ax.axis('off')
    for index, pattern in enumerate(patterns, start=1):
        imagebox = OffsetImage(create_pattern_image(pattern, cell_size=6), zoom=zoom)
        ab = AnnotationBbox(imagebox, (index, image_y), frameon=False, pad=0)
        ax.add_artist(ab)
        if show_codes:
            ax.text(index, label_y, f'S{index:02d}', ha='center', va='bottom', fontsize=7, color=MUTED_TEXT)
    return ax


# ---------------------------------------------------------------------------
# Oracle helpers & derived transforms
# ---------------------------------------------------------------------------

def oracle_helpers():
    return [
        [[1,0,0,0,0,0,0,0,0,1],[0,1,0,0,0,0,0,0,1,0],[0,0,1,0,0,0,0,1,0,0],[0,0,0,1,0,0,1,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,1,0,0,1,0,0,0],[0,0,1,0,0,0,0,1,0,0],[0,1,0,0,0,0,0,0,1,0],[1,0,0,0,0,0,0,0,0,1]],
        [[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0]],
        [[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0],[0,0,0,0,1,1,0,0,0,0]],
        [[1,0,0,0,0,0,0,0,0,0],[1,1,0,0,0,0,0,0,0,0],[1,1,1,0,0,0,0,0,0,0],[1,1,1,1,0,0,0,0,0,0],[1,1,1,1,1,0,0,0,0,0],[1,1,1,1,1,0,0,0,0,0],[1,1,1,1,0,0,0,0,0,0],[1,1,1,0,0,0,0,0,0,0],[1,1,0,0,0,0,0,0,0,0],[1,0,0,0,0,0,0,0,0,0]],
    ]


def oracle_derived_keys():
    """Generate tuple-keys for all invert/reflect transforms of oracle helpers, excluding originals."""
    oracle_keys = {tuple(tuple(c for c in row) for row in p) for p in oracle_helpers()}
    derived = set()
    for oracle in oracle_helpers():
        arr = np.array(oracle)
        inv = 1 - arr
        for t in [inv, np.fliplr(arr), np.flipud(arr), arr.T]:
            key = tuple(tuple(int(c) for c in row) for row in t.tolist())
            if key not in oracle_keys:
                derived.add(key)
    return derived


# ---------------------------------------------------------------------------
# Plot functions (identical to original)
# ---------------------------------------------------------------------------

def plot_accuracy(participants, targets, basename='fig1_accuracy', output_dir=None, panel_label=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    n_participants = len(participants)
    per_trial = [[] for _ in range(16)]
    for participant in participants:
        for trial in participant['trials']:
            per_trial[trial['trial'] - 1].append(1 if trial['success'] else 0)

    means = np.array([np.mean(values) * 100 for values in per_trial])
    errors = np.array([sem(values) * 100 for values in per_trial])
    x = np.arange(1, 17)
    overall_mean = np.mean(means)

    fig = plt.figure(figsize=(7.2, 4.8))
    ax = fig.add_axes((0.08, 0.28, 0.88, 0.58))
    add_family_guides(ax)

    ax.bar(
        x,
        means,
        width=0.68,
        color=SECONDARY_BLUE,
        edgecolor='white',
        linewidth=0.8,
        yerr=errors,
        ecolor=PRIMARY_BLUE,
        capsize=3,
        zorder=3,
    )

    ax.axhline(overall_mean, color=MUTED_TEXT, linestyle='--', linewidth=1.2, alpha=0.7, zorder=4)
    ax.text(16.9, overall_mean, f'M = {overall_mean:.1f}', fontsize=8, color=MUTED_TEXT,
            fontweight='bold', va='center', ha='left', clip_on=False)

    ax.set_title('Accuracy by Trial', fontsize=10, fontweight='bold', loc='left', pad=8)
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_ylim(0, 115)
    ax.set_xlim(0.3, 16.7)
    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_yticks([0, 25, 50, 75, 100])
    apply_axis_style(ax, grid_axis='y')

    add_thumbnail_strip(fig, targets, (0.08, 0.11, 0.88, 0.14), show_codes=False, zoom=0.37, image_y=0.52)
    fig.text(0.08, 0.04, f'Note. Bar heights show mean accuracy; error bars show ±1 SEM. '
             f'Dashed line marks overall M. N = {n_participants}.',
             fontsize=7.5, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig, basename, output_dir=output_dir, panel_label=panel_label)


def plot_accuracy_across_trials(participants, targets, basename='fig6_accuracy_across_trials', output_dir=None, panel_label=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    n_participants = len(participants)
    per_trial = [[] for _ in range(16)]
    for participant in participants:
        for trial in participant['trials']:
            per_trial[trial['trial'] - 1].append(1 if trial['success'] else 0)

    x = np.arange(1, 17)
    means = np.array([np.mean(values) * 100 for values in per_trial])
    errors = np.array([sem(values) * 100 for values in per_trial])
    overall_mean = np.mean(means)

    fig = plt.figure(figsize=(7.2, 4.8))
    ax = fig.add_axes((0.08, 0.28, 0.88, 0.58))
    add_family_guides(ax)

    rng = np.random.default_rng(44)
    for trial_idx, trial_num in enumerate(x):
        values = np.array(per_trial[trial_idx]) * 100
        jitter = rng.normal(0, 0.08, len(values))
        ax.scatter(
            np.full(len(values), trial_num) + jitter,
            values,
            color=LIGHT_BLUE,
            alpha=0.5,
            s=14,
            zorder=1,
        )

    ax.fill_between(x, means - errors, means + errors, color=LIGHT_BLUE, alpha=0.85, zorder=2)
    ax.errorbar(
        x,
        means,
        yerr=errors,
        color=PRIMARY_BLUE,
        linewidth=2.2,
        marker='o',
        markerfacecolor='white',
        markeredgewidth=1.8,
        markersize=5,
        capsize=3,
        zorder=3,
    )

    ax.axhline(overall_mean, color=MUTED_TEXT, linestyle='--', linewidth=1.2, alpha=0.7, zorder=4)
    ax.text(16.9, overall_mean, f'M = {overall_mean:.1f}', fontsize=8, color=MUTED_TEXT,
            fontweight='bold', va='center', ha='left', clip_on=False)

    ax.set_title('Accuracy Across Trials', fontsize=10, fontweight='bold', loc='left', pad=8)
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_xlim(0.3, 16.7)
    ax.set_ylim(0, 115)
    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_yticks([0, 25, 50, 75, 100])
    apply_axis_style(ax, grid_axis='y')

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color=PRIMARY_BLUE, label='Mean ± SEM',
               markerfacecolor='white', markersize=5, markeredgecolor=PRIMARY_BLUE, linewidth=1.5),
        Line2D([0], [0], marker='o', color='w', label='Individual', markerfacecolor=LIGHT_BLUE,
               markersize=5, markeredgecolor=LIGHT_BLUE, alpha=0.6),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=7.5, framealpha=0.9)

    add_thumbnail_strip(fig, targets, (0.08, 0.11, 0.88, 0.14), show_codes=False, zoom=0.37, image_y=0.52)
    fig.text(0.08, 0.04, f'Note. Line shows mean accuracy (±1 SEM band/bars). '
             f'Dots are individual participants. Dashed line marks overall M. N = {n_participants}.',
             fontsize=7.5, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig, basename, output_dir=output_dir, panel_label=panel_label)


def plot_steps_time(participants, targets, basename='fig2_steps_time', output_dir=None, panel_label=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    times = defaultdict(list)
    steps = defaultdict(list)
    for participant in participants:
        for trial in participant['trials']:
            if trial['success']:
                times[trial['trial']].append(trial['timeSpent'])
                steps[trial['trial']].append(trial['stepsCount'])

    # Filter unreasonable time values (>600s = 10 min likely indicates idle/abandoned tab)
    for t in times:
        times[t] = [v for v in times[t] if v <= 600]

    x = np.arange(1, 17)
    n_participants = len(participants)

    # --- Panel A: Time ---
    time_means = np.array([np.mean(times[i]) if times[i] else 0 for i in x])
    time_errors = np.array([sem(times[i]) if times[i] else 0 for i in x])
    time_overall = np.mean(time_means)

    fig_a = plt.figure(figsize=(7.2, 4.8))
    ax_a = fig_a.add_axes((0.08, 0.28, 0.88, 0.58))
    add_family_guides(ax_a)

    rng_a = np.random.default_rng(45)
    for trial_num in x:
        vals = times[trial_num]
        jitter = rng_a.normal(0, 0.08, len(vals))
        ax_a.scatter(np.full(len(vals), trial_num) + jitter, vals,
                     color=LIGHT_BLUE, alpha=0.45, s=12, zorder=1)

    ax_a.fill_between(x, time_means - time_errors, time_means + time_errors, color=LIGHT_BLUE, alpha=0.85, zorder=2)
    ax_a.errorbar(x, time_means, yerr=time_errors, color=PRIMARY_BLUE, linewidth=2.2,
                  marker='o', markerfacecolor='white', markeredgewidth=1.8, markersize=5, capsize=3, zorder=3)

    ax_a.axhline(time_overall, color=MUTED_TEXT, linestyle='--', linewidth=1.2, alpha=0.7, zorder=4)
    ax_a.text(16.9, time_overall, f'M = {time_overall:.0f}s', fontsize=8, color=MUTED_TEXT,
              fontweight='bold', va='center', ha='left', clip_on=False)

    ax_a.set_title('Time Spent by Trial', fontsize=10, fontweight='bold', loc='left', pad=8)
    ax_a.set_ylabel('Time (s)', fontweight='bold')
    ax_a.set_xlim(0.3, 16.7)
    time_all = np.array([v for vals in times.values() for v in vals], dtype=float)
    time_cap = float(np.percentile(time_all, 95)) if len(time_all) else 1.0
    time_cap = max(time_cap, float((time_means + time_errors).max()))
    ax_a.set_ylim(0, time_cap * 1.15)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels([])
    apply_axis_style(ax_a, grid_axis='y')

    from matplotlib.lines import Line2D
    legend_a = [
        Line2D([0], [0], marker='o', color=PRIMARY_BLUE, label='Mean ± SEM',
               markerfacecolor='white', markersize=5, markeredgecolor=PRIMARY_BLUE, linewidth=1.5),
        Line2D([0], [0], marker='o', color='w', label='Individual', markerfacecolor=LIGHT_BLUE,
               markersize=5, markeredgecolor=LIGHT_BLUE, alpha=0.6),
    ]
    ax_a.legend(handles=legend_a, loc='upper right', fontsize=7.5, framealpha=0.9)

    add_thumbnail_strip(fig_a, targets, (0.08, 0.11, 0.88, 0.14), show_codes=False, zoom=0.37, image_y=0.52)
    fig_a.text(0.08, 0.04, f'Note. Line shows mean time spent (±1 SEM band/bars). '
               f'Dots are individual participants. Dashed line marks overall M. '
               f'Successful trials only. N = {n_participants}.',
               fontsize=7.5, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig_a, 'fig2a_time', output_dir=output_dir, panel_label='A' if panel_label else None)

    # --- Panel B: Steps ---
    step_means = np.array([np.mean(steps[i]) if steps[i] else 0 for i in x])
    step_errors = np.array([sem(steps[i]) if steps[i] else 0 for i in x])
    step_overall = np.mean(step_means)

    fig_b = plt.figure(figsize=(7.2, 4.8))
    ax_b = fig_b.add_axes((0.08, 0.28, 0.88, 0.58))
    add_family_guides(ax_b)

    rng_b = np.random.default_rng(46)
    for trial_num in x:
        vals = steps[trial_num]
        jitter = rng_b.normal(0, 0.08, len(vals))
        ax_b.scatter(np.full(len(vals), trial_num) + jitter, vals,
                     color=LIGHT_BLUE, alpha=0.45, s=12, zorder=1)

    ax_b.fill_between(x, step_means - step_errors, step_means + step_errors, color=LIGHT_BLUE, alpha=0.85, zorder=2)
    ax_b.errorbar(x, step_means, yerr=step_errors, color=PRIMARY_BLUE, linewidth=2.2,
                  marker='o', markerfacecolor='white', markeredgewidth=1.8, markersize=5, capsize=3, zorder=3)

    ax_b.axhline(step_overall, color=MUTED_TEXT, linestyle='--', linewidth=1.2, alpha=0.7, zorder=4)
    ax_b.text(16.9, step_overall, f'M = {step_overall:.1f}', fontsize=8, color=MUTED_TEXT,
              fontweight='bold', va='center', ha='left', clip_on=False)

    ax_b.set_title('Steps by Trial', fontsize=10, fontweight='bold', loc='left', pad=8)
    ax_b.set_ylabel('Steps', fontweight='bold')
    ax_b.set_xlim(0.3, 16.7)
    step_all = np.array([v for vals in steps.values() for v in vals], dtype=float)
    step_cap = float(np.percentile(step_all, 95)) if len(step_all) else 1.0
    step_cap = max(step_cap, float((step_means + step_errors).max()))
    ax_b.set_ylim(0, step_cap * 1.15)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels([])
    apply_axis_style(ax_b, grid_axis='y')

    legend_b = [
        Line2D([0], [0], marker='o', color=PRIMARY_BLUE, label='Mean ± SEM',
               markerfacecolor='white', markersize=5, markeredgecolor=PRIMARY_BLUE, linewidth=1.5),
        Line2D([0], [0], marker='o', color='w', label='Individual', markerfacecolor=LIGHT_BLUE,
               markersize=5, markeredgecolor=LIGHT_BLUE, alpha=0.6),
    ]
    ax_b.legend(handles=legend_b, loc='upper right', fontsize=7.5, framealpha=0.9)

    add_thumbnail_strip(fig_b, targets, (0.08, 0.11, 0.88, 0.14), show_codes=False, zoom=0.37, image_y=0.52)
    fig_b.text(0.08, 0.04, f'Note. Line shows mean steps (±1 SEM band/bars). '
               f'Dots are individual participants. Dashed line marks overall M. '
               f'Successful trials only. N = {n_participants}.',
               fontsize=7.5, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig_b, 'fig2b_steps', output_dir=output_dir, panel_label='B' if panel_label else None)


def plot_helper_usage(participants, targets, basename='fig3_helper_usage', output_dir=None, panel_label=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    rates = defaultdict(list)
    for participant in participants:
        for trial in participant['trials']:
            if not trial['success']:
                continue
            rates[trial['trial']].append(trial['helperStepRate'])

    x = np.arange(1, 17)
    means = np.array([np.mean(rates[i]) if rates[i] else 0 for i in x])
    errors = np.array([sem(rates[i]) if rates[i] else 0 for i in x])
    overall_mean = np.mean(means)
    n_participants = len(participants)

    fig = plt.figure(figsize=(7.2, 4.8))
    ax = fig.add_axes((0.08, 0.28, 0.88, 0.58))
    add_family_guides(ax)
    rng = np.random.default_rng(42)
    for index, trial_num in enumerate(x):
        values = rates[trial_num]
        jitter = rng.normal(0, 0.08, len(values))
        ax.scatter(
            np.full(len(values), trial_num) + jitter,
            values,
            color=LIGHT_BLUE,
            alpha=0.5,
            s=14,
            zorder=1,
        )

    ax.fill_between(x, means - errors, means + errors, color=LIGHT_BLUE, alpha=0.85, zorder=2)
    ax.errorbar(
        x,
        means,
        yerr=errors,
        color=PRIMARY_BLUE,
        linewidth=2.2,
        marker='o',
        markerfacecolor='white',
        markeredgewidth=1.8,
        markersize=5,
        capsize=3,
        zorder=3,
    )

    ax.axhline(overall_mean, color=MUTED_TEXT, linestyle='--', linewidth=1.2, alpha=0.7, zorder=4)
    ax.text(16.9, overall_mean, f'M = {overall_mean:.1f}', fontsize=8, color=MUTED_TEXT,
            fontweight='bold', va='center', ha='left', clip_on=False)

    ax.set_title('Helper Use Rate by Trial', fontsize=10, fontweight='bold', loc='left', pad=8)
    ax.set_ylabel('% Steps Using Helper', fontweight='bold')
    ax.set_ylim(0, 110)
    ax.set_xlim(0.3, 16.7)
    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_yticks([0, 25, 50, 75, 100])
    apply_axis_style(ax, grid_axis='y')

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color=PRIMARY_BLUE, label='Mean ± SEM',
               markerfacecolor='white', markersize=5, markeredgecolor=PRIMARY_BLUE, linewidth=1.5),
        Line2D([0], [0], marker='o', color='w', label='Individual', markerfacecolor=LIGHT_BLUE,
               markersize=5, markeredgecolor=LIGHT_BLUE, alpha=0.6),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=7.5, framealpha=0.9)

    add_thumbnail_strip(fig, targets, (0.08, 0.11, 0.88, 0.14), show_codes=False, zoom=0.37, image_y=0.52)
    fig.text(0.08, 0.04, f'Note. Line shows mean helper-assisted step rate (±1 SEM band/bars). '
             f'Dots are individual participants. Dashed line marks overall M. '
             f'Successful trials only. N = {n_participants}.',
             fontsize=7.5, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig, basename, output_dir=output_dir, panel_label=panel_label)


def plot_helper_adds_by_trial(participants, targets, basename='fig7_helper_adds_by_trial', output_dir=None, panel_label=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    adds = defaultdict(list)
    for participant in participants:
        for trial in participant['trials']:
            adds[trial['trial']].append(len(trial['helperAddPatterns']))

    x = np.arange(1, 17)
    means = np.array([np.mean(adds[i]) if adds[i] else 0 for i in x])
    errors = np.array([sem(adds[i]) if adds[i] else 0 for i in x])
    overall_mean = np.mean(means)
    n_participants = len(participants)

    fig = plt.figure(figsize=(7.2, 4.8))
    ax = fig.add_axes((0.08, 0.28, 0.88, 0.58))
    add_family_guides(ax)

    rng = np.random.default_rng(43)
    for index, trial_num in enumerate(x):
        values = np.array(adds[trial_num])
        jitter = rng.normal(0, 0.06, len(values))
        ax.scatter(
            np.full(len(values), trial_num) + jitter,
            values,
            color=LIGHT_BLUE,
            alpha=0.5,
            s=14,
            zorder=1,
        )

    ax.fill_between(x, means - errors, means + errors, color=LIGHT_BLUE, alpha=0.85, zorder=2)
    ax.errorbar(
        x,
        means,
        yerr=errors,
        color=PRIMARY_BLUE,
        linewidth=2.4,
        marker='o',
        markerfacecolor='white',
        markeredgewidth=1.8,
        markersize=5.4,
        capsize=3,
        zorder=3,
    )

    ax.axhline(overall_mean, color=MUTED_TEXT, linestyle='--', linewidth=1.2, alpha=0.7, zorder=4)
    ax.text(16.9, overall_mean, f'M = {overall_mean:.2f}', fontsize=8, color=MUTED_TEXT,
            fontweight='bold', va='center', ha='left', clip_on=False)

    ax.set_title('Helper Adds by Trial', fontsize=10, fontweight='bold', loc='left', pad=8)
    ax.set_ylabel('Number of Helper Adds', fontweight='bold')
    ax.set_xlim(0.3, 16.7)
    ax.set_ylim(0, max(2.5, float((means + errors).max()) + 0.5))
    ax.set_xticks(x)
    ax.set_xticklabels([])
    apply_axis_style(ax, grid_axis='y')

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color=PRIMARY_BLUE, label='Mean ± SEM',
               markerfacecolor='white', markersize=5, markeredgecolor=PRIMARY_BLUE, linewidth=1.5),
        Line2D([0], [0], marker='o', color='w', label='Individual', markerfacecolor=LIGHT_BLUE,
               markersize=5, markeredgecolor=LIGHT_BLUE, alpha=0.6),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=7.5, framealpha=0.9)

    add_thumbnail_strip(fig, targets, (0.08, 0.11, 0.88, 0.14), show_codes=False, zoom=0.37, image_y=0.52)
    fig.text(0.08, 0.04, f'Note. Line shows mean number of helpers added (±1 SEM band/bars). '
             f'Dots are individual participants. Dashed line marks overall M. N = {n_participants}.',
             fontsize=7.5, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig, basename, output_dir=output_dir, panel_label=panel_label)


def plot_helper_distribution(participants, targets, basename='fig4_helper_distribution', output_dir=None, panel_label=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    max_rank = 8
    oracle_keys = {tuple(tuple(cell for cell in row) for row in pattern) for pattern in oracle_helpers()}
    deriv_keys = oracle_derived_keys()

    trial_pattern_users = defaultdict(lambda: defaultdict(set))
    trial_users_with_added_helpers = defaultdict(set)
    pattern_data = {}

    for participant in participants:
        participant_id = participant['id']
        for trial in participant['trials']:
            trial_num = trial['trial']
            if not trial['success']:
                continue
            if trial['helperPatterns']:
                trial_users_with_added_helpers[trial_num].add(participant_id)
            for pattern in trial['helperPatterns']:
                pattern_key = str(pattern)
                trial_pattern_users[trial_num][pattern_key].add(participant_id)
                pattern_data[pattern_key] = pattern

    heatmap = np.zeros((max_rank, 16))
    count_text = np.zeros((max_rank, 16), dtype=int)
    pattern_at_position = {}

    for trial_num in range(1, 17):
        n_users = len(trial_users_with_added_helpers[trial_num])
        if n_users == 0:
            continue
        ranked = sorted(
            trial_pattern_users[trial_num].items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )
        ranked = [(key, users) for key, users in ranked if len(users) > 1][:max_rank]
        for rank, (pattern_key, users) in enumerate(ranked):
            count = len(users)
            heatmap[rank, trial_num - 1] = (count / n_users) * 100
            count_text[rank, trial_num - 1] = count
            pattern_at_position[(rank, trial_num - 1)] = pattern_data[pattern_key]

    fig = plt.figure(figsize=(13.2, 8.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[16, 1], height_ratios=[1.4, 8], wspace=0.04, hspace=0.02)
    ax_top = fig.add_subplot(gs[0, 0])
    ax_main = fig.add_subplot(gs[1, 0])
    ax_cbar = fig.add_subplot(gs[:, 1])
    
    ax_title = fig.add_axes((0.08, 0.92, 0.88, 0.05))
    ax_title.axis('off')
    ax_title.text(0, 0.5, 'Distribution of Helper Patterns by Trial', fontsize=11, fontweight='bold', va='center')

    colors = ['#ffffff', '#e8f1fa', '#c3dbef', '#7cb4d8', '#2d75ad', PRIMARY_BLUE]
    cmap = LinearSegmentedColormap.from_list('helper_dist_blues', colors, N=256)
    im = ax_main.imshow(heatmap, aspect='auto', cmap=cmap, vmin=0, vmax=100, interpolation='nearest')

    for trial_idx in range(16):
        for rank in range(max_rank):
            count = count_text[rank, trial_idx]
            if count == 0:
                continue
            pattern = pattern_at_position[(rank, trial_idx)]
            imagebox = OffsetImage(create_pattern_image(pattern, cell_size=5), zoom=0.34)
            pattern_key = tuple(tuple(cell for cell in row) for row in pattern)

            bboxprops = None
            if patterns_equal(pattern, targets[trial_idx]):
                bboxprops = dict(edgecolor=TARGET_EDGE, linewidth=2.4, facecolor='none')
            elif pattern_key in oracle_keys:
                bboxprops = dict(edgecolor=ORACLE_EDGE, linewidth=2.4, facecolor='none', linestyle='--')
            elif pattern_key in deriv_keys:
                bboxprops = dict(edgecolor=ORACLE_DERIV_EDGE, linewidth=2.4, facecolor='none', linestyle=':')

            if bboxprops is None:
                ab = AnnotationBbox(imagebox, (trial_idx, rank), frameon=False, pad=0, zorder=5)
            else:
                ab = AnnotationBbox(imagebox, (trial_idx, rank), frameon=True, bboxprops=bboxprops, pad=0.05, zorder=5)
            ax_main.add_artist(ab)

            text_color = 'white' if heatmap[rank, trial_idx] > 55 else '#333'
            ax_main.text(trial_idx, rank + 0.42, str(count), ha='center', va='center', fontsize=10, color=text_color, fontweight='bold', zorder=6)

    ax_main.set_xticks(np.arange(16))
    ax_main.set_xticklabels([f'S{i:02d}' for i in range(1, 17)], fontsize=9)
    ax_main.set_yticks(np.arange(max_rank))
    ax_main.set_yticklabels([f'#{i}' for i in range(1, max_rank + 1)], fontsize=10)
    ax_main.set_ylabel('Rank', fontweight='bold')
    ax_main.tick_params(axis='x', top=True, labeltop=True, bottom=False, labelbottom=False)

    for idx in range(17):
        ax_main.axvline(idx - 0.5, color='white', linewidth=1, alpha=0.9)
    for idx in range(max_rank + 1):
        ax_main.axhline(idx - 0.5, color='white', linewidth=1, alpha=0.9)
    for idx in range(1, 4):
        ax_main.axvline(idx * 4 - 0.5, color=FAMILY_EDGE, linewidth=1.4, linestyle='--', alpha=0.95)

    ax_top.set_xlim(-0.5, 15.5)
    ax_top.set_ylim(0, 1)
    ax_top.axis('off')
    for index, pattern in enumerate(targets):
        imagebox = OffsetImage(create_pattern_image(pattern, cell_size=6), zoom=0.32)
        ab = AnnotationBbox(imagebox, (index, 0.5), frameon=True, bboxprops=dict(edgecolor='#333', linewidth=0.8), pad=0.06)
        ax_top.add_artist(ab)

    cbar = fig.colorbar(im, cax=ax_cbar)
    cbar.set_label('Proportion (%)', fontweight='bold')

    legend_handles = [
        Patch(facecolor='none', edgecolor=TARGET_EDGE, linewidth=2, label='Target Pattern'),
        Patch(facecolor='none', edgecolor=ORACLE_EDGE, linewidth=2, linestyle='--', label='Oracle Helper'),
        Patch(facecolor='none', edgecolor=ORACLE_DERIV_EDGE, linewidth=2, linestyle=':', label='Oracle Derived'),
    ]
    ax_main.legend(handles=legend_handles, loc='lower right', fontsize=9, framealpha=0.9)

    n_participants = len(participants)
    fig.text(0.08, 0.005, f'Note. Heatmap shows proportion of helper-using participants who used each pattern. '
             f'Numbers indicate raw user count. Orange = target; green dashed = oracle; purple dotted = oracle derived (invert/reflect). '
             f'Only patterns used by ≥2 participants shown. N = {n_participants}.',
             fontsize=7, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig, basename, output_dir=output_dir, panel_label=panel_label)


def plot_helper_distribution_used(participants, targets, basename='fig4b_helper_distribution_used', output_dir=None, panel_label=None):
    """Like plot_helper_distribution but only includes helpers that were ever click+confirmed across all trials."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    max_rank = 8
    oracle_keys = {tuple(tuple(cell for cell in row) for row in pattern) for pattern in oracle_helpers()}
    deriv_keys = oracle_derived_keys()

    trial_pattern_users = defaultdict(lambda: defaultdict(set))
    trial_users_with_confirmed_helpers = defaultdict(set)
    pattern_data = {}

    # First pass: collect each participant's globally-confirmed pattern signatures
    participant_confirmed_sigs = {}
    for participant in participants:
        confirmed_sigs = set()
        for trial in participant['trials']:
            for pattern in trial.get('confirmedHelperPatterns', []):
                confirmed_sigs.add(pattern_signature(pattern))
        participant_confirmed_sigs[participant['id']] = confirmed_sigs

    # Second pass: for each trial, keep added patterns only if ever confirmed
    for participant in participants:
        participant_id = participant['id']
        confirmed_sigs = participant_confirmed_sigs[participant_id]
        for trial in participant['trials']:
            trial_num = trial['trial']
            if not trial['success']:
                continue
            used_patterns = [p for p in trial['helperPatterns']
                            if pattern_signature(p) in confirmed_sigs]
            if used_patterns:
                trial_users_with_confirmed_helpers[trial_num].add(participant_id)
            for pattern in used_patterns:
                pattern_key = str(pattern)
                trial_pattern_users[trial_num][pattern_key].add(participant_id)
                pattern_data[pattern_key] = pattern

    heatmap = np.zeros((max_rank, 16))
    count_text = np.zeros((max_rank, 16), dtype=int)
    pattern_at_position = {}

    for trial_num in range(1, 17):
        n_users = len(trial_users_with_confirmed_helpers[trial_num])
        if n_users == 0:
            continue
        ranked = sorted(
            trial_pattern_users[trial_num].items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )
        ranked = [(key, users) for key, users in ranked if len(users) > 1][:max_rank]
        for rank, (pattern_key, users) in enumerate(ranked):
            count = len(users)
            heatmap[rank, trial_num - 1] = (count / n_users) * 100
            count_text[rank, trial_num - 1] = count
            pattern_at_position[(rank, trial_num - 1)] = pattern_data[pattern_key]

    fig = plt.figure(figsize=(13.2, 8.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[16, 1], height_ratios=[1.4, 8], wspace=0.04, hspace=0.02)
    ax_top = fig.add_subplot(gs[0, 0])
    ax_main = fig.add_subplot(gs[1, 0])
    ax_cbar = fig.add_subplot(gs[:, 1])

    ax_title = fig.add_axes((0.08, 0.92, 0.88, 0.05))
    ax_title.axis('off')
    ax_title.text(0, 0.5, 'Distribution of Confirmed-Use Helper Patterns by Trial', fontsize=11, fontweight='bold', va='center')

    colors = ['#ffffff', '#e8f1fa', '#c3dbef', '#7cb4d8', '#2d75ad', PRIMARY_BLUE]
    cmap = LinearSegmentedColormap.from_list('helper_dist_blues_used', colors, N=256)
    im = ax_main.imshow(heatmap, aspect='auto', cmap=cmap, vmin=0, vmax=100, interpolation='nearest')

    for trial_idx in range(16):
        for rank in range(max_rank):
            count = count_text[rank, trial_idx]
            if count == 0:
                continue
            pattern = pattern_at_position[(rank, trial_idx)]
            imagebox = OffsetImage(create_pattern_image(pattern, cell_size=5), zoom=0.34)
            pattern_key = tuple(tuple(cell for cell in row) for row in pattern)

            bboxprops = None
            if patterns_equal(pattern, targets[trial_idx]):
                bboxprops = dict(edgecolor=TARGET_EDGE, linewidth=2.4, facecolor='none')
            elif pattern_key in oracle_keys:
                bboxprops = dict(edgecolor=ORACLE_EDGE, linewidth=2.4, facecolor='none', linestyle='--')
            elif pattern_key in deriv_keys:
                bboxprops = dict(edgecolor=ORACLE_DERIV_EDGE, linewidth=2.4, facecolor='none', linestyle=':')

            if bboxprops is None:
                ab = AnnotationBbox(imagebox, (trial_idx, rank), frameon=False, pad=0, zorder=5)
            else:
                ab = AnnotationBbox(imagebox, (trial_idx, rank), frameon=True, bboxprops=bboxprops, pad=0.05, zorder=5)
            ax_main.add_artist(ab)

            text_color = 'white' if heatmap[rank, trial_idx] > 55 else '#333'
            ax_main.text(trial_idx, rank + 0.42, str(count), ha='center', va='center', fontsize=10, color=text_color, fontweight='bold', zorder=6)

    ax_main.set_xticks(np.arange(16))
    ax_main.set_xticklabels([f'S{i:02d}' for i in range(1, 17)], fontsize=9)
    ax_main.set_yticks(np.arange(max_rank))
    ax_main.set_yticklabels([f'#{i}' for i in range(1, max_rank + 1)], fontsize=10)
    ax_main.set_ylabel('Rank', fontweight='bold')
    ax_main.tick_params(axis='x', top=True, labeltop=True, bottom=False, labelbottom=False)

    for idx in range(17):
        ax_main.axvline(idx - 0.5, color='white', linewidth=1, alpha=0.9)
    for idx in range(max_rank + 1):
        ax_main.axhline(idx - 0.5, color='white', linewidth=1, alpha=0.9)
    for idx in range(1, 4):
        ax_main.axvline(idx * 4 - 0.5, color=FAMILY_EDGE, linewidth=1.4, linestyle='--', alpha=0.95)

    ax_top.set_xlim(-0.5, 15.5)
    ax_top.set_ylim(0, 1)
    ax_top.axis('off')
    for index, pattern in enumerate(targets):
        imagebox = OffsetImage(create_pattern_image(pattern, cell_size=6), zoom=0.32)
        ab = AnnotationBbox(imagebox, (index, 0.5), frameon=True, bboxprops=dict(edgecolor='#333', linewidth=0.8), pad=0.06)
        ax_top.add_artist(ab)

    cbar = fig.colorbar(im, cax=ax_cbar)
    cbar.set_label('Proportion (%)', fontweight='bold')

    legend_handles = [
        Patch(facecolor='none', edgecolor=TARGET_EDGE, linewidth=2, label='Target Pattern'),
        Patch(facecolor='none', edgecolor=ORACLE_EDGE, linewidth=2, linestyle='--', label='Oracle Helper'),
        Patch(facecolor='none', edgecolor=ORACLE_DERIV_EDGE, linewidth=2, linestyle=':', label='Oracle Derived'),
    ]
    ax_main.legend(handles=legend_handles, loc='lower right', fontsize=9, framealpha=0.9)

    n_participants = len(participants)
    fig.text(0.08, 0.005, f'Note. Only helpers that were clicked and confirmed at least once across all trials are included. '
             f'Numbers indicate raw user count. Orange = target; green dashed = oracle; purple dotted = oracle derived (invert/reflect). '
             f'Only patterns confirmed by ≥2 participants shown. N = {n_participants}.',
             fontsize=7, color=MUTED_TEXT, va='top', wrap=True)
    save_figure(fig, basename, output_dir=output_dir, panel_label=panel_label)


def plot_helper_population(participants, targets, top_n=20, basename='fig5_helper_population', output_dir=None, panel_label=None, show_title=True, show_rank_label=True):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    oracle_keys = {tuple(tuple(cell for cell in row) for row in pattern) for pattern in oracle_helpers()}
    deriv_keys = oracle_derived_keys()
    target_keys = {tuple(tuple(cell for cell in row) for row in pattern) for pattern in targets}
    pattern_users = defaultdict(set)
    pattern_data = {}

    for participant in participants:
        participant_id = participant['pid']
        participant_patterns_seen = set()
        for trial in participant['trials']:
            for pattern in trial['helperAddPatterns']:
                signature = pattern_signature(pattern)
                participant_patterns_seen.add(signature)
                pattern_data[signature] = pattern
        for signature in participant_patterns_seen:
            pattern_users[signature].add(participant_id)

    if not pattern_users:
        return

    ranked = sorted(
        pattern_users.items(),
        key=lambda item: (-len(item[1]), str(item[0])),
    )[:top_n]
    total_participants = len(participants)
    n = len(ranked)
    counts = np.array([len(users) for _, users in ranked])
    shares = counts / total_participants * 100

    # ── Layout ──
    row_h = 0.32
    fig_h = max(5.0, row_h * n + 2.2)
    fig = plt.figure(figsize=(7.2, fig_h))

    thumb_l, thumb_w = 0.06, 0.07
    dot_l, dot_w = 0.16, 0.78
    bottom = 0.10
    top = 0.92
    ph = top - bottom

    ax = fig.add_axes((dot_l, bottom, dot_w, ph))
    ax_t = fig.add_axes((thumb_l, bottom, thumb_w, ph))

    y = np.arange(n)

    # ── Alternating row bands ──
    for i in range(n):
        if i % 2 == 0:
            ax.axhspan(i - 0.5, i + 0.5, color='#f8f9fa', zorder=0)

    # ── Lollipop: stem + dot ──
    for i, s in enumerate(shares):
        ax.plot([0, s], [i, i], color=PRIMARY_BLUE, linewidth=1.6, solid_capstyle='round', zorder=2)
    ax.scatter(shares, y, s=52, color=PRIMARY_BLUE, edgecolor='white', linewidth=0.8, zorder=3)

    # ── Percentage + count labels ──
    for i, (cnt, s) in enumerate(zip(counts, shares)):
        ax.text(s + 1.5, i, f'{s:.0f}%  ({cnt}/{total_participants})',
                va='center', ha='left', fontsize=7.5, color='#333')

    ax.set_xlim(0, 108)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(['0', '25', '50', '75', '100%'], fontsize=8)
    ax.set_yticks([])
    ax.set_xlabel('Adoption Rate (%)', fontsize=9, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.grid(axis='x', color='#e0e0e0', linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    # ── Thumbnails ──
    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(n - 0.5, -0.5)
    ax_t.axis('off')

    for idx, (sig, users_set) in enumerate(ranked):
        pat = pattern_data[sig]
        pk = tuple(tuple(c for c in row) for row in pat)
        bp = dict(edgecolor='#d1d5db', linewidth=0.6, facecolor='white')
        if pk in target_keys:
            bp = dict(edgecolor=TARGET_EDGE, linewidth=1.6, facecolor='white')
        elif pk in oracle_keys:
            bp = dict(edgecolor=ORACLE_EDGE, linewidth=1.6, facecolor='white', linestyle='--')
        elif pk in deriv_keys:
            bp = dict(edgecolor=ORACLE_DERIV_EDGE, linewidth=1.6, facecolor='white', linestyle=':')
        ib = OffsetImage(create_pattern_image(pat, cell_size=6), zoom=0.40)
        ax_t.add_artist(AnnotationBbox(ib, (0.5, idx), frameon=True, bboxprops=bp, pad=0.05))

    # ── Title ──
    if show_title:
        fig.text(0.06, 0.96, f'Top {top_n} Most-Added Helpers',
                 fontsize=10, fontweight='bold')

    # ── Legend ──
    from matplotlib.lines import Line2D
    leg = [
        Patch(facecolor='white', edgecolor=TARGET_EDGE, lw=1.6, label='Target'),
        Patch(facecolor='white', edgecolor=ORACLE_EDGE, lw=1.6, linestyle='--', label='Oracle'),
        Patch(facecolor='white', edgecolor=ORACLE_DERIV_EDGE, lw=1.6, linestyle=':', label='Oracle Derived'),
    ]
    ax.legend(handles=leg, loc='lower right', fontsize=7.5, framealpha=0.9,
              handlelength=1.2, handletextpad=0.4)

    fig.text(0.06, 0.025, f'Note. Dot position shows adoption rate among {total_participants} participants. '
             f'Orange = target; green dashed = oracle; purple dotted = oracle derived (invert/reflect).',
             fontsize=7, color=MUTED_TEXT, va='top')
    save_figure(fig, basename, output_dir=output_dir, panel_label=panel_label)


def plot_helper_population_used(participants, targets, top_n=20, basename='fig5b_helper_population_used', output_dir=None):
    """Like plot_helper_population but only includes helpers that were actually used in a confirmed step."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    oracle_keys = {tuple(tuple(cell for cell in row) for row in pattern) for pattern in oracle_helpers()}
    deriv_keys = oracle_derived_keys()
    target_keys = {tuple(tuple(cell for cell in row) for row in pattern) for pattern in targets}
    pattern_users = defaultdict(set)
    pattern_data = {}

    for participant in participants:
        participant_id = participant['pid']
        seen = set()
        for trial in participant['trials']:
            for pattern in trial.get('confirmedHelperPatterns', []):
                sig = pattern_signature(pattern)
                seen.add(sig)
                pattern_data[sig] = pattern
        for sig in seen:
            pattern_users[sig].add(participant_id)

    if not pattern_users:
        return

    ranked = sorted(pattern_users.items(), key=lambda item: (-len(item[1]), -sum(sum(r) for r in json.loads(item[0]))))[:top_n]
    total_participants = len(participants)
    n = len(ranked)
    counts = np.array([len(users) for _, users in ranked])
    shares = counts / total_participants * 100

    row_h = 0.32
    fig_h = max(5.0, row_h * n + 2.2)
    fig = plt.figure(figsize=(7.2, fig_h))

    thumb_l, thumb_w = 0.06, 0.07
    dot_l, dot_w = 0.16, 0.78
    bottom = 0.10
    top = 0.92
    ph = top - bottom

    ax = fig.add_axes((dot_l, bottom, dot_w, ph))
    ax_t = fig.add_axes((thumb_l, bottom, thumb_w, ph))

    y = np.arange(n)

    for i in range(n):
        if i % 2 == 0:
            ax.axhspan(i - 0.5, i + 0.5, color='#f8f9fa', zorder=0)

    for i, s in enumerate(shares):
        ax.plot([0, s], [i, i], color=PRIMARY_BLUE, linewidth=1.6, solid_capstyle='round', zorder=2)
    ax.scatter(shares, y, s=52, color=PRIMARY_BLUE, edgecolor='white', linewidth=0.8, zorder=3)

    for i, (cnt, s) in enumerate(zip(counts, shares)):
        ax.text(s + 1.5, i, f'{s:.0f}%  ({cnt}/{total_participants})',
                va='center', ha='left', fontsize=7.5, color='#333')

    ax.set_xlim(0, 108)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(['0', '25', '50', '75', '100%'], fontsize=8)
    ax.set_yticks([])
    ax.set_xlabel('Adoption Rate (%)', fontsize=9, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.grid(axis='x', color='#e0e0e0', linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(n - 0.5, -0.5)
    ax_t.axis('off')

    for idx, (sig, users_set) in enumerate(ranked):
        pat = pattern_data[sig]
        pk = tuple(tuple(c for c in row) for row in pat)
        bp = dict(edgecolor='#d1d5db', linewidth=0.6, facecolor='white')
        if pk in target_keys:
            bp = dict(edgecolor=TARGET_EDGE, linewidth=1.6, facecolor='white')
        elif pk in oracle_keys:
            bp = dict(edgecolor=ORACLE_EDGE, linewidth=1.6, facecolor='white', linestyle='--')
        elif pk in deriv_keys:
            bp = dict(edgecolor=ORACLE_DERIV_EDGE, linewidth=1.6, facecolor='white', linestyle=':')
        ib = OffsetImage(create_pattern_image(pat, cell_size=6), zoom=0.40)
        ax_t.add_artist(AnnotationBbox(ib, (0.5, idx), frameon=True, bboxprops=bp, pad=0.05))

    fig.text(0.06, 0.96, f'Top {top_n} Most-Used Helpers (Confirmed in Steps)',
             fontsize=10, fontweight='bold')

    from matplotlib.lines import Line2D
    leg = [
        Patch(facecolor='white', edgecolor=TARGET_EDGE, lw=1.6, label='Target'),
        Patch(facecolor='white', edgecolor=ORACLE_EDGE, lw=1.6, linestyle='--', label='Oracle'),
        Patch(facecolor='white', edgecolor=ORACLE_DERIV_EDGE, lw=1.6, linestyle=':', label='Oracle Derived'),
    ]
    ax.legend(handles=leg, loc='lower right', fontsize=7.5, framealpha=0.9,
              handlelength=1.2, handletextpad=0.4)

    fig.text(0.06, 0.025, f'Note. Only helpers actually used in confirmed steps. Dot = adoption rate among {total_participants} participants. '
             f'Orange = target; green dashed = oracle; purple dotted = oracle derived (invert/reflect).',
             fontsize=7, color=MUTED_TEXT, va='top')
    save_figure(fig, basename, output_dir=output_dir)


def plot_final_helper_library(participants, targets, basename='fig8_final_helpers', output_dir=None):
    """Render each participant's final helper library as a grid of thumbnails, 3 pages of 10."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    setup_style()
    oracle_keys = {tuple(tuple(c for c in row) for row in p) for p in oracle_helpers()}
    deriv_keys = oracle_derived_keys()
    target_keys = {tuple(tuple(c for c in row) for row in p) for p in targets}

    # Reconstruct final helper library per participant
    participant_helpers = []
    for p in participants:
        helpers = {}  # favoriteId -> pattern
        for t in p['trials']:
            for fa in t.get('favoriteActions', []):
                act = fa.get('action')
                fid = fa.get('favoriteId')
                if act == 'add' and fid and 'pattern' in fa:
                    helpers[fid] = fa['pattern']
                elif act == 'remove' and fid:
                    helpers.pop(fid, None)
        participant_helpers.append({
            'pid': p['pid'],
            'score': p['score'],
            'patterns': list(helpers.values()),
        })

    # Sort by number of helpers descending
    participant_helpers.sort(key=lambda x: len(x['patterns']), reverse=True)

    # 3 pages of 10
    max_cols = 12  # max thumbnails per row
    for page in range(3):
        subset = participant_helpers[page * 10:(page + 1) * 10]
        if not subset:
            break

        n_rows = len(subset)
        row_height = 0.72
        fig_h = max(5.0, row_height * n_rows + 1.8)
        fig = plt.figure(figsize=(8.5, fig_h))

        fig.text(0.04, 0.97, f'Final Helper Libraries  (Page {page + 1}/3)',
                 fontsize=10, fontweight='bold', va='top')

        usable_top = 0.93
        usable_bottom = 0.06
        usable_h = usable_top - usable_bottom
        slot_h = usable_h / n_rows

        for i, ph in enumerate(subset):
            y_center = usable_top - (i + 0.5) * slot_h
            pats = ph['patterns']
            n_pats = len(pats)
            pid_short = ph['pid'][-6:]
            label = f'P{page * 10 + i + 1}  ({n_pats} helpers, score {ph["score"]}/16)'

            # Label on the left
            fig.text(0.04, y_center, label, fontsize=7.5, fontweight='bold',
                     color=PRIMARY_BLUE, va='center', ha='left')

            if n_pats == 0:
                fig.text(0.30, y_center, '(no helpers added)', fontsize=7.5,
                         color=MUTED_TEXT, va='center', style='italic')
                continue

            # Thumbnail row
            thumb_left = 0.22
            thumb_right = 0.97
            thumb_w = thumb_right - thumb_left
            ax = fig.add_axes((thumb_left, y_center - slot_h * 0.38,
                               thumb_w, slot_h * 0.76))
            ax.set_xlim(-0.5, max(max_cols, n_pats) - 0.5)
            ax.set_ylim(-0.5, 0.5)
            ax.axis('off')

            for j, pat in enumerate(pats[:max_cols]):
                pk = tuple(tuple(c for c in row) for row in pat)
                bp = dict(edgecolor='#d1d5db', linewidth=0.5, facecolor='white')
                if pk in target_keys:
                    bp = dict(edgecolor=TARGET_EDGE, linewidth=1.4, facecolor='white')
                elif pk in oracle_keys:
                    bp = dict(edgecolor=ORACLE_EDGE, linewidth=1.4, facecolor='white', linestyle='--')
                elif pk in deriv_keys:
                    bp = dict(edgecolor=ORACLE_DERIV_EDGE, linewidth=1.4, facecolor='white', linestyle=':')
                ib = OffsetImage(create_pattern_image(pat, cell_size=5), zoom=0.35)
                ax.add_artist(AnnotationBbox(ib, (j, 0), frameon=True, bboxprops=bp, pad=0.04))

            if n_pats > max_cols:
                ax.text(max_cols + 0.2, 0, f'+{n_pats - max_cols}', fontsize=7,
                        color=MUTED_TEXT, va='center')

        # Separator lines
        for i in range(1, n_rows):
            y_line = usable_top - i * slot_h
            fig.add_artist(plt.Line2D([0.04, 0.97], [y_line, y_line],
                                      transform=fig.transFigure, color='#e5e7eb',
                                      linewidth=0.5, zorder=0))

        # Legend
        legend_handles = [
            Patch(facecolor='white', edgecolor=TARGET_EDGE, linewidth=1.4, label='Target'),
            Patch(facecolor='white', edgecolor=ORACLE_EDGE, linewidth=1.4, linestyle='--', label='Oracle'),
            Patch(facecolor='white', edgecolor=ORACLE_DERIV_EDGE, linewidth=1.4, linestyle=':', label='Oracle Derived'),
            Patch(facecolor='white', edgecolor='#d1d5db', linewidth=0.5, label='Other'),
        ]
        fig.legend(handles=legend_handles, loc='lower right', fontsize=7.5,
                   framealpha=0.9, bbox_to_anchor=(0.97, 0.005), ncol=4)

        fig.text(0.04, 0.01,
                 f'Note. Sorted by number of helpers (descending). '
                 f'Orange = target; green dashed = oracle; purple dotted = oracle derived. N = {len(participants)}.',
                 fontsize=7, color=MUTED_TEXT, va='top')

        save_figure(fig, f'{basename}_p{page + 1}', output_dir=output_dir)


# ---------------------------------------------------------------------------
# Paper panels export
# ---------------------------------------------------------------------------

def export_paper_panels(participants, targets):
    panel_specs = [
        ('A', plot_accuracy, {'participants': participants, 'targets': targets, 'basename': 'panel_A_accuracy', 'output_dir': PAPER_PANEL_DIR, 'panel_label': 'A'}),
        ('B', plot_steps_time, {'participants': participants, 'targets': targets, 'basename': 'panel_B_steps_time', 'output_dir': PAPER_PANEL_DIR, 'panel_label': 'B'}),
        ('C', plot_helper_usage, {'participants': participants, 'targets': targets, 'basename': 'panel_C_helper_step_rate', 'output_dir': PAPER_PANEL_DIR, 'panel_label': 'C'}),
        ('D', plot_helper_distribution, {'participants': participants, 'targets': targets, 'basename': 'panel_D_helper_distribution', 'output_dir': PAPER_PANEL_DIR, 'panel_label': 'D'}),
        ('E', plot_helper_population, {'participants': participants, 'targets': targets, 'basename': 'panel_E_helper_population', 'output_dir': PAPER_PANEL_DIR, 'panel_label': 'E', 'show_title': False, 'show_rank_label': False}),
        ('F', plot_accuracy_across_trials, {'participants': participants, 'targets': targets, 'basename': 'panel_F_accuracy_across_trials', 'output_dir': PAPER_PANEL_DIR, 'panel_label': 'F'}),
    ]

    for _, plot_fn, kwargs in panel_specs:
        plot_fn(**kwargs)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    participants = load_participants()
    targets = load_targets()
    print(f'Loaded {len(participants)} participants, {len(targets)} targets')
    print(f'Output directory: {OUTPUT_DIR}')

    plot_accuracy(participants, targets)
    plot_accuracy_across_trials(participants, targets)
    plot_steps_time(participants, targets)
    plot_helper_usage(participants, targets)
    plot_helper_adds_by_trial(participants, targets)
    plot_helper_distribution(participants, targets)
    plot_helper_distribution_used(participants, targets)
    plot_helper_population(participants, targets)
    plot_helper_population_used(participants, targets)
    plot_final_helper_library(participants, targets)
    export_paper_panels(participants, targets)

    print('Done — all figures saved.')


if __name__ == '__main__':
    main()
