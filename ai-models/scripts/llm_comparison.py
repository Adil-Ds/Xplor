# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding="utf-8")
"""
Local LLM Model Comparison
Compares models by RAM usage, benchmark scores, and task capabilities.
Highlights Qwen2.5 family against other small/medium/large models.
Saves all outputs to ../evaluation/
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib import colors as mcolors

os.makedirs('../evaluation', exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODEL DATA
# Each entry: name, family, params_B, ram_q4_gb, ram_fp16_gb,
#             mmlu, humaneval, context_k, speed_cpu_tps,
#             tasks, license, hf_id, tier
# ─────────────────────────────────────────────────────────────────────────────
MODELS = [
    # ── Tiny / Ultra-small ────────────────────────────────────────────────
    {
        "name": "SmolLM2-135M",    "family": "SmolLM2",
        "params_B": 0.135,         "ram_q4_gb": 0.3,   "ram_fp16_gb": 0.3,
        "mmlu": 30.1,              "humaneval": 5.4,
        "context_k": 8,            "speed_cpu_tps": 180,
        "tasks": ["chat", "completion"],
        "license": "Apache 2.0",   "hf_id": "HuggingFaceTB/SmolLM2-135M-Instruct",
        "tier": "tiny",
    },
    {
        "name": "SmolLM2-1.7B",    "family": "SmolLM2",
        "params_B": 1.7,           "ram_q4_gb": 1.1,   "ram_fp16_gb": 3.4,
        "mmlu": 48.3,              "humaneval": 21.0,
        "context_k": 8,            "speed_cpu_tps": 55,
        "tasks": ["chat", "completion", "summarization"],
        "license": "Apache 2.0",   "hf_id": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "tier": "small",
    },
    {
        "name": "TinyLlama-1.1B",  "family": "TinyLlama",
        "params_B": 1.1,           "ram_q4_gb": 0.7,   "ram_fp16_gb": 2.2,
        "mmlu": 25.6,              "humaneval": 8.0,
        "context_k": 4,            "speed_cpu_tps": 70,
        "tasks": ["chat", "completion"],
        "license": "Apache 2.0",   "hf_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "tier": "small",
    },
    # ── Qwen2.5 family ────────────────────────────────────────────────────
    {
        "name": "Qwen2.5-0.5B",    "family": "Qwen2.5",
        "params_B": 0.5,           "ram_q4_gb": 0.4,   "ram_fp16_gb": 1.0,
        "mmlu": 45.4,              "humaneval": 28.9,
        "context_k": 32,           "speed_cpu_tps": 140,
        "tasks": ["chat", "code", "completion", "translation"],
        "license": "Apache 2.0",   "hf_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "tier": "tiny",
    },
    {
        "name": "Qwen2.5-1.5B",    "family": "Qwen2.5",
        "params_B": 1.5,           "ram_q4_gb": 1.1,   "ram_fp16_gb": 3.0,
        "mmlu": 60.9,              "humaneval": 37.2,
        "context_k": 32,           "speed_cpu_tps": 60,
        "tasks": ["chat", "code", "completion", "summarization", "translation"],
        "license": "Apache 2.0",   "hf_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "tier": "small",
    },
    {
        "name": "Qwen2.5-3B",      "family": "Qwen2.5",
        "params_B": 3.0,           "ram_q4_gb": 2.0,   "ram_fp16_gb": 6.0,
        "mmlu": 65.6,              "humaneval": 55.5,
        "context_k": 32,           "speed_cpu_tps": 32,
        "tasks": ["chat", "code", "reasoning", "summarization", "translation"],
        "license": "Apache 2.0",   "hf_id": "Qwen/Qwen2.5-3B-Instruct",
        "tier": "small",
    },
    {
        "name": "Qwen2.5-7B",      "family": "Qwen2.5",
        "params_B": 7.0,           "ram_q4_gb": 4.5,   "ram_fp16_gb": 14.0,
        "mmlu": 74.2,              "humaneval": 72.0,
        "context_k": 128,          "speed_cpu_tps": 14,
        "tasks": ["chat", "code", "reasoning", "summarization", "translation", "agents"],
        "license": "Apache 2.0",   "hf_id": "Qwen/Qwen2.5-7B-Instruct",
        "tier": "medium",
    },
    {
        "name": "Qwen2.5-14B",     "family": "Qwen2.5",
        "params_B": 14.0,          "ram_q4_gb": 8.9,   "ram_fp16_gb": 28.0,
        "mmlu": 79.7,              "humaneval": 78.0,
        "context_k": 128,          "speed_cpu_tps": 7,
        "tasks": ["chat", "code", "reasoning", "summarization", "translation", "agents"],
        "license": "Apache 2.0",   "hf_id": "Qwen/Qwen2.5-14B-Instruct",
        "tier": "medium",
    },
    {
        "name": "Qwen2.5-72B",     "family": "Qwen2.5",
        "params_B": 72.0,          "ram_q4_gb": 45.0,  "ram_fp16_gb": 144.0,
        "mmlu": 86.1,              "humaneval": 86.0,
        "context_k": 128,          "speed_cpu_tps": 2,
        "tasks": ["chat", "code", "reasoning", "summarization", "translation", "agents"],
        "license": "Apache 2.0",   "hf_id": "Qwen/Qwen2.5-72B-Instruct",
        "tier": "large",
    },
    # ── Llama 3.x family ──────────────────────────────────────────────────
    {
        "name": "Llama-3.2-1B",    "family": "Llama 3.x",
        "params_B": 1.0,           "ram_q4_gb": 0.7,   "ram_fp16_gb": 2.0,
        "mmlu": 44.7,              "humaneval": 25.0,
        "context_k": 128,          "speed_cpu_tps": 80,
        "tasks": ["chat", "completion", "summarization"],
        "license": "Llama 3",      "hf_id": "meta-llama/Llama-3.2-1B-Instruct",
        "tier": "small",
    },
    {
        "name": "Llama-3.2-3B",    "family": "Llama 3.x",
        "params_B": 3.0,           "ram_q4_gb": 2.0,   "ram_fp16_gb": 6.0,
        "mmlu": 58.0,              "humaneval": 40.0,
        "context_k": 128,          "speed_cpu_tps": 30,
        "tasks": ["chat", "code", "reasoning", "summarization"],
        "license": "Llama 3",      "hf_id": "meta-llama/Llama-3.2-3B-Instruct",
        "tier": "small",
    },
    {
        "name": "Llama-3.1-8B",    "family": "Llama 3.x",
        "params_B": 8.0,           "ram_q4_gb": 4.9,   "ram_fp16_gb": 16.0,
        "mmlu": 68.4,              "humaneval": 62.0,
        "context_k": 128,          "speed_cpu_tps": 12,
        "tasks": ["chat", "code", "reasoning", "summarization", "translation", "agents"],
        "license": "Llama 3",      "hf_id": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "tier": "medium",
    },
    {
        "name": "Llama-3.1-70B",   "family": "Llama 3.x",
        "params_B": 70.0,          "ram_q4_gb": 40.0,  "ram_fp16_gb": 140.0,
        "mmlu": 83.6,              "humaneval": 80.0,
        "context_k": 128,          "speed_cpu_tps": 2,
        "tasks": ["chat", "code", "reasoning", "summarization", "translation", "agents"],
        "license": "Llama 3",      "hf_id": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "tier": "large",
    },
    # ── Phi family (Microsoft) ────────────────────────────────────────────
    {
        "name": "Phi-3.5-mini",    "family": "Phi",
        "params_B": 3.8,           "ram_q4_gb": 2.4,   "ram_fp16_gb": 7.6,
        "mmlu": 69.0,              "humaneval": 59.0,
        "context_k": 128,          "speed_cpu_tps": 25,
        "tasks": ["chat", "code", "reasoning", "summarization"],
        "license": "MIT",          "hf_id": "microsoft/Phi-3.5-mini-instruct",
        "tier": "small",
    },
    {
        "name": "Phi-3-medium",    "family": "Phi",
        "params_B": 14.0,          "ram_q4_gb": 8.4,   "ram_fp16_gb": 28.0,
        "mmlu": 78.0,              "humaneval": 65.0,
        "context_k": 128,          "speed_cpu_tps": 7,
        "tasks": ["chat", "code", "reasoning", "summarization"],
        "license": "MIT",          "hf_id": "microsoft/Phi-3-medium-128k-instruct",
        "tier": "medium",
    },
    # ── Gemma family (Google) ─────────────────────────────────────────────
    {
        "name": "Gemma-2-2B",      "family": "Gemma",
        "params_B": 2.0,           "ram_q4_gb": 1.4,   "ram_fp16_gb": 4.0,
        "mmlu": 52.2,              "humaneval": 36.0,
        "context_k": 8,            "speed_cpu_tps": 40,
        "tasks": ["chat", "completion", "summarization"],
        "license": "Gemma",        "hf_id": "google/gemma-2-2b-it",
        "tier": "small",
    },
    {
        "name": "Gemma-2-9B",      "family": "Gemma",
        "params_B": 9.0,           "ram_q4_gb": 5.5,   "ram_fp16_gb": 18.0,
        "mmlu": 71.3,              "humaneval": 55.0,
        "context_k": 8,            "speed_cpu_tps": 10,
        "tasks": ["chat", "code", "reasoning", "summarization"],
        "license": "Gemma",        "hf_id": "google/gemma-2-9b-it",
        "tier": "medium",
    },
    # ── Mistral family ────────────────────────────────────────────────────
    {
        "name": "Mistral-7B",      "family": "Mistral",
        "params_B": 7.0,           "ram_q4_gb": 4.1,   "ram_fp16_gb": 14.0,
        "mmlu": 63.0,              "humaneval": 41.0,
        "context_k": 32,           "speed_cpu_tps": 15,
        "tasks": ["chat", "code", "summarization", "translation"],
        "license": "Apache 2.0",   "hf_id": "mistralai/Mistral-7B-Instruct-v0.3",
        "tier": "medium",
    },
    {
        "name": "Mixtral-8x7B",    "family": "Mistral",
        "params_B": 46.7,          "ram_q4_gb": 28.0,  "ram_fp16_gb": 90.0,
        "mmlu": 71.0,              "humaneval": 40.2,
        "context_k": 32,           "speed_cpu_tps": 3,
        "tasks": ["chat", "code", "reasoning", "summarization"],
        "license": "Apache 2.0",   "hf_id": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "tier": "large",
    },
]

# Sort by RAM (Q4) for consistent ordering
MODELS.sort(key=lambda x: x["ram_q4_gb"])

# ─────────────────────────────────────────────────────────────────────────────
# COLOR SCHEME
# ─────────────────────────────────────────────────────────────────────────────
FAMILY_COLORS = {
    "Qwen2.5":   "#f59e0b",   # amber  — highlighted
    "Llama 3.x": "#6366f1",   # indigo
    "Phi":       "#10b981",   # emerald
    "Gemma":     "#ec4899",   # pink
    "Mistral":   "#8b5cf6",   # violet
    "TinyLlama": "#64748b",   # slate
    "SmolLM2":   "#94a3b8",   # light slate
}
TIER_COLORS = {"tiny": "#bbf7d0", "small": "#bfdbfe", "medium": "#fde68a", "large": "#fecaca"}

print("=" * 65)
print("Local LLM Comparison — RAM, Performance & Capabilities")
print(f"Total models compared: {len(MODELS)}")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────────────────
# SAVE JSON
# ─────────────────────────────────────────────────────────────────────────────
output = {
    "description": "Local LLM comparison: RAM usage, benchmarks, capabilities",
    "note": "RAM values are estimates for Q4 quantization (GGUF/GPTQ) and FP16. "
            "Benchmark scores sourced from official model cards and open LLM leaderboard. "
            "CPU speed is approximate on a modern mid-range CPU (e.g., Ryzen 5 5600).",
    "models": MODELS,
    "summary": {
        "lowest_ram_q4": min(MODELS, key=lambda x: x["ram_q4_gb"])["name"],
        "best_mmlu_under_4gb": max(
            [m for m in MODELS if m["ram_q4_gb"] < 4.0], key=lambda x: x["mmlu"]
        )["name"],
        "best_mmlu_overall": max(MODELS, key=lambda x: x["mmlu"])["name"],
        "best_efficiency": "Qwen2.5-3B (65.6 MMLU / 2.0GB — highest score-per-GB under 3GB)"
    }
}
with open('../evaluation/local_llm_comparison.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print("\nJSON saved: local_llm_comparison.json")

# ─────────────────────────────────────────────────────────────────────────────
# PLOT 1: RAM Comparison Bar Chart (Q4 vs FP16)
# ─────────────────────────────────────────────────────────────────────────────
names     = [m["name"] for m in MODELS]
ram_q4    = [m["ram_q4_gb"] for m in MODELS]
ram_fp16  = [m["ram_fp16_gb"] for m in MODELS]
families  = [m["family"] for m in MODELS]
bar_colors = [FAMILY_COLORS[f] for f in families]

fig, ax = plt.subplots(figsize=(14, 9))
y = np.arange(len(names))
h = 0.38

b1 = ax.barh(y + h/2, ram_fp16, h, label='FP16 (full precision)', color='#e2e8f0', edgecolor='#94a3b8', linewidth=0.7)
b2 = ax.barh(y - h/2, ram_q4,   h, label='Q4 Quantized (local run)', color=bar_colors, edgecolor='white', linewidth=0.5)

# Value labels
for bar, val in zip(b1, ram_fp16):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}GB', va='center', fontsize=7.5, color='#64748b')
for bar, val, fam in zip(b2, ram_q4, families):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}GB', va='center', fontsize=8,
            fontweight='bold' if fam == 'Qwen2.5' else 'normal',
            color='#1e293b')

# Reference lines
for gb, label, ls in [(4, '4GB RAM', '--'), (8, '8GB RAM', ':'), (16, '16GB RAM', '-.')]:
    ax.axvline(gb, color='#ef4444', linestyle=ls, linewidth=1, alpha=0.6)
    ax.text(gb + 0.1, len(names) - 0.5, label, color='#ef4444', fontsize=7.5, va='top')

ax.set_yticks(y)
ax.set_yticklabels(names, fontsize=9)
ax.set_xlabel('RAM Required (GB)', fontsize=11)
ax.set_title('Local LLM RAM Requirements\nQ4 Quantized (runnable locally) vs FP16 Full Precision',
             fontsize=13, fontweight='bold', pad=12)

# Family legend
family_patches = [mpatches.Patch(color=c, label=f) for f, c in FAMILY_COLORS.items()]
legend1 = ax.legend(handles=family_patches, title='Model Family', loc='lower right',
                    fontsize=8, title_fontsize=9, framealpha=0.9)
ax.add_artist(legend1)
ax.legend(handles=[b1, b2], loc='upper right', fontsize=8)
ax.set_xlim(0, max(ram_fp16) * 1.15)
ax.grid(axis='x', linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig('../evaluation/llm_ram_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot saved: llm_ram_comparison.png")

# ─────────────────────────────────────────────────────────────────────────────
# PLOT 2: MMLU Score vs RAM (Scatter — efficiency frontier)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7))

for m in MODELS:
    fc   = FAMILY_COLORS[m["family"]]
    size = 120 + m["params_B"] * 4
    ax.scatter(m["ram_q4_gb"], m["mmlu"], s=size, color=fc,
               edgecolors='white' if m["family"] != "Qwen2.5" else '#b45309',
               linewidths=2 if m["family"] == "Qwen2.5" else 0.8,
               zorder=3 if m["family"] == "Qwen2.5" else 2, alpha=0.92)
    offset_x = 0.3
    offset_y = 0.8
    ax.annotate(
        m["name"], (m["ram_q4_gb"], m["mmlu"]),
        xytext=(offset_x, offset_y), textcoords='offset points',
        fontsize=7.5,
        fontweight='bold' if m["family"] == "Qwen2.5" else 'normal',
        color='#92400e' if m["family"] == "Qwen2.5" else '#1e293b'
    )

# Efficiency frontier annotation
ax.annotate("Best efficiency zone\n(high MMLU, low RAM)",
            xy=(2.0, 65.6), xytext=(5, 42),
            fontsize=8.5, color='#065f46',
            arrowprops=dict(arrowstyle='->', color='#065f46', lw=1.5),
            bbox=dict(boxstyle='round,pad=0.3', fc='#d1fae5', ec='#065f46', alpha=0.85))

# RAM reference shading
ax.axvspan(0, 4,  alpha=0.06, color='#22c55e', label='< 4GB (most laptops)')
ax.axvspan(4, 16, alpha=0.06, color='#f59e0b', label='4-16GB (gaming PC / workstation)')
ax.axvspan(16, max(ram_q4) * 1.1, alpha=0.06, color='#ef4444', label='> 16GB (high-end workstation)')

family_patches = [mpatches.Patch(color=c, label=f) for f, c in FAMILY_COLORS.items()]
ax.legend(handles=family_patches, title='Family', loc='upper left',
          fontsize=8, title_fontsize=9, framealpha=0.9)

ax.set_xlabel('RAM Required — Q4 Quantized (GB)', fontsize=11)
ax.set_ylabel('MMLU Score (%)', fontsize=11)
ax.set_title('Performance vs RAM — Local LLM Efficiency Comparison\n'
             'Bubble size = parameter count  |  Amber border = Qwen2.5 family',
             fontsize=12, fontweight='bold')
ax.grid(linestyle='--', alpha=0.3)
ax.set_ylim(15, 95)
plt.tight_layout()
plt.savefig('../evaluation/llm_performance_vs_ram.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot saved: llm_performance_vs_ram.png")

# ─────────────────────────────────────────────────────────────────────────────
# PLOT 3: Capabilities heatmap — which model can do what
# ─────────────────────────────────────────────────────────────────────────────
ALL_TASKS = ["chat", "code", "reasoning", "summarization", "translation", "agents"]

fig, ax = plt.subplots(figsize=(13, 9))
matrix = np.zeros((len(MODELS), len(ALL_TASKS)))
for i, m in enumerate(MODELS):
    for j, t in enumerate(ALL_TASKS):
        matrix[i, j] = 1 if t in m["tasks"] else 0

cmap = mcolors.ListedColormap(['#f1f5f9', '#22c55e'])
im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=1)

for i in range(len(MODELS)):
    for j in range(len(ALL_TASKS)):
        ax.text(j, i, '[Y]' if matrix[i, j] else '[ ]',
                ha='center', va='center', fontsize=9,
                color='#166534' if matrix[i, j] else '#94a3b8',
                fontweight='bold' if matrix[i, j] else 'normal')

ax.set_xticks(range(len(ALL_TASKS)))
ax.set_xticklabels([t.upper() for t in ALL_TASKS], fontsize=10, fontweight='bold')
ax.set_yticks(range(len(MODELS)))
yticklabels = []
for m in MODELS:
    label = m["name"]
    if m["family"] == "Qwen2.5":
        label = "* " + label
    yticklabels.append(label)
ax.set_yticklabels(yticklabels, fontsize=9)

# Color Qwen2.5 row labels
for i, m in enumerate(MODELS):
    if m["family"] == "Qwen2.5":
        ax.get_yticklabels()[i].set_color('#b45309')
        ax.get_yticklabels()[i].set_fontweight('bold')

ax.set_title('Supported Tasks by Model\n(* = Qwen2.5 family | [Y] = supported)',
             fontsize=12, fontweight='bold', pad=10)
ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

plt.tight_layout()
plt.savefig('../evaluation/llm_capabilities_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot saved: llm_capabilities_heatmap.png")

# ─────────────────────────────────────────────────────────────────────────────
# PLOT 4: Qwen2.5 family deep-dive — scaling within the family
# ─────────────────────────────────────────────────────────────────────────────
qwen_models = [m for m in MODELS if m["family"] == "Qwen2.5"]
qwen_models.sort(key=lambda x: x["params_B"])

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

qnames  = [m["name"].replace("Qwen2.5-", "") for m in qwen_models]
q_ram   = [m["ram_q4_gb"] for m in qwen_models]
q_mmlu  = [m["mmlu"] for m in qwen_models]
q_heval = [m["humaneval"] for m in qwen_models]
q_spd   = [m["speed_cpu_tps"] for m in qwen_models]
q_ctx   = [m["context_k"] for m in qwen_models]
amber   = "#f59e0b"

# RAM
ax = axes[0]
bars = ax.bar(qnames, q_ram, color=amber, alpha=0.85, edgecolor='#b45309')
for bar, v in zip(bars, q_ram):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
            f'{v}GB', ha='center', fontsize=8.5, fontweight='bold')
ax.set_title('RAM Required\n(Q4 Quantized)', fontweight='bold')
ax.set_ylabel('GB'); ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.set_ylim(0, max(q_ram) * 1.2)

# Benchmarks
ax = axes[1]
x = np.arange(len(qnames)); w = 0.38
b1 = ax.bar(x - w/2, q_mmlu,  w, label='MMLU (%)',      color='#6366f1', alpha=0.85)
b2 = ax.bar(x + w/2, q_heval, w, label='HumanEval (%)', color='#10b981', alpha=0.85)
for bar, v in zip(list(b1)+list(b2), q_mmlu+q_heval):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f'{v:.0f}', ha='center', fontsize=7.5, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(qnames)
ax.set_title('Benchmark Scores\n(MMLU & HumanEval)', fontweight='bold')
ax.legend(fontsize=8); ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.set_ylim(0, 100)

# Speed vs RAM efficiency
ax = axes[2]
sc = ax.scatter(q_ram, q_mmlu, s=[s*2+50 for s in q_spd],
                c=q_spd, cmap='RdYlGn', vmin=0, vmax=160,
                edgecolors='#b45309', linewidths=1.5, zorder=3)
for m, x_v, y_v in zip(qnames, q_ram, q_mmlu):
    ax.annotate(m, (x_v, y_v), xytext=(4, 3), textcoords='offset points', fontsize=8)
plt.colorbar(sc, ax=ax, label='CPU Speed (tokens/sec)')
ax.set_xlabel('RAM (GB, Q4)'); ax.set_ylabel('MMLU Score (%)')
ax.set_title('Qwen2.5: RAM vs Score\n(bubble size = CPU speed)', fontweight='bold')
ax.grid(linestyle='--', alpha=0.3)

plt.suptitle('Qwen2.5 Family — Scaling Analysis (0.5B to 72B)',
             fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('../evaluation/qwen25_family_analysis.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot saved: qwen25_family_analysis.png")

# ─────────────────────────────────────────────────────────────────────────────
# CONSOLE SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 95)
print(f"{'Model':<22} {'Family':<12} {'Params':>7} {'Q4 RAM':>8} {'FP16 RAM':>9} {'MMLU':>6} {'HumanEval':>11} {'Ctx(K)':>7} {'License':<12}")
print("-" * 95)
for m in MODELS:
    marker = " *" if m["family"] == "Qwen2.5" else "  "
    print(f"{m['name']+marker:<22} {m['family']:<12} {m['params_B']:>5.1f}B {m['ram_q4_gb']:>7.1f}GB "
          f"{m['ram_fp16_gb']:>8.1f}GB {m['mmlu']:>5.1f}% {m['humaneval']:>9.1f}%  {m['context_k']:>5}K  {m['license']}")
print("=" * 95)
print("  * = Qwen2.5 family (highlighted)")

print("\n--- BEST PICKS BY RAM BUDGET ---")
budgets = [(2, "< 2GB (low-end laptop / Raspberry Pi)"),
           (4, "< 4GB (standard laptop)"),
           (8, "< 8GB (gaming laptop / mid-range PC)"),
           (16, "< 16GB (workstation)")]
for limit, label in budgets:
    candidates = [m for m in MODELS if m["ram_q4_gb"] < limit]
    if candidates:
        best = max(candidates, key=lambda x: x["mmlu"])
        print(f"  {label}")
        print(f"    Best MMLU: {best['name']} — {best['mmlu']}% MMLU, {best['ram_q4_gb']}GB Q4 RAM")

print("\n--- OUTPUT FILES ---")
for f in ['local_llm_comparison.json','llm_ram_comparison.png',
          'llm_performance_vs_ram.png','llm_capabilities_heatmap.png','qwen25_family_analysis.png']:
    print(f"  ../evaluation/{f}")

print("\n" + "=" * 65)
print("  LLM comparison complete.")
print("=" * 65)
