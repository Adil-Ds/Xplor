# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding="utf-8")
"""
IsolationForest Training on KDD Cup 1999 (real network intrusion dataset)
Compares against IQR baseline -- produces metrics + plots.
"""
import os, json, warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, average_precision_score,
    precision_recall_curve, confusion_matrix, ConfusionMatrixDisplay
)

os.makedirs('../evaluation', exist_ok=True)
SEED = 42
np.random.seed(SEED)

# -- 1. Load KDD Cup 1999 --------------------------------------
print("=" * 60)
print("IsolationForest -- KDD Cup 1999 Anomaly Detection")
print("=" * 60)

df = pd.read_csv('../data/raw/kddcup99_sa.csv')
print(f"\nDataset: KDD Cup 1999 (SA subset, 10%)")
print(f"  Shape         : {df.shape}")
print(f"  Normal rows   : {(df['is_anomaly']==0).sum():,} ({(df['is_anomaly']==0).mean()*100:.1f}%)")
print(f"  Anomaly rows  : {(df['is_anomaly']==1).sum():,} ({(df['is_anomaly']==1).mean()*100:.1f}%)")

X = df.drop(columns=['is_anomaly']).values
y = df['is_anomaly'].values

# -- 2. Train/Test Split & Scale -------------------------------
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.30, random_state=SEED, stratify=y
)
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
X_te_s  = scaler.transform(X_te)

print(f"\nTrain: {X_tr_s.shape[0]:,} rows | Test: {X_te_s.shape[0]:,} rows")

# -- 3. Baseline -- IQR -----------------------------------------
Q1  = np.percentile(X_tr_s, 25, axis=0)
Q3  = np.percentile(X_tr_s, 75, axis=0)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
dev   = np.maximum(X_te_s - upper, lower - X_te_s)
score_iqr  = dev.max(axis=1)
y_pred_iqr = (score_iqr > 0).astype(int)

iqr_p   = precision_score(y_te, y_pred_iqr, zero_division=0)
iqr_r   = recall_score(y_te,    y_pred_iqr, zero_division=0)
iqr_f1  = f1_score(y_te,        y_pred_iqr, zero_division=0)
iqr_auc = roc_auc_score(y_te,   score_iqr)
iqr_fpr = ((y_pred_iqr==1)&(y_te==0)).sum() / (y_te==0).sum()

print(f"\n[BASELINE] IQR Rule-Based:")
print(f"  Precision : {iqr_p:.4f}")
print(f"  Recall    : {iqr_r:.4f}")
print(f"  F1 Score  : {iqr_f1:.4f}")
print(f"  ROC-AUC   : {iqr_auc:.4f}")
print(f"  FP Rate   : {iqr_fpr:.4f}")

# -- 4. Train IsolationForest ----------------------------------
actual_rate = y_tr.mean()
print(f"\nTraining IsolationForest (contamination={actual_rate:.3f}, n_estimators=100)...")
iso = IsolationForest(
    n_estimators=100,
    contamination=float(actual_rate),
    max_samples='auto',
    random_state=SEED,
    n_jobs=-1
)
iso.fit(X_tr_s)
print("Training complete.")

y_pred_if = (iso.predict(X_te_s) == -1).astype(int)
score_if  = -iso.score_samples(X_te_s)

if_p   = precision_score(y_te, y_pred_if, zero_division=0)
if_r   = recall_score(y_te,    y_pred_if, zero_division=0)
if_f1  = f1_score(y_te,        y_pred_if, zero_division=0)
if_auc = roc_auc_score(y_te,   score_if)
if_fpr = ((y_pred_if==1)&(y_te==0)).sum() / (y_te==0).sum()

print(f"\n[TRAINED] IsolationForest:")
print(f"  Precision : {if_p:.4f}")
print(f"  Recall    : {if_r:.4f}")
print(f"  F1 Score  : {if_f1:.4f}")
print(f"  ROC-AUC   : {if_auc:.4f}")
print(f"  FP Rate   : {if_fpr:.4f}")

# -- 5. Results Table ------------------------------------------
print("\n" + "=" * 60)
print(f"{'Metric':<24} {'IQR Baseline':>14} {'IsolationForest':>15}  {'Improvement':>12}")
print("-" * 60)
rows = [
    ('Precision',          iqr_p,   if_p,   False),
    ('Recall',             iqr_r,   if_r,   False),
    ('F1 Score',           iqr_f1,  if_f1,  False),
    ('ROC-AUC',            iqr_auc, if_auc, False),
    ('False Positive Rate',iqr_fpr, if_fpr, True ),   # lower is better
]
for metric, b, m, lower_better in rows:
    diff = m - b
    better = diff < 0 if lower_better else diff > 0
    arrow = ('+' if diff > 0 else '-')
    mark  = '[OK]' if better else '[--]'
    print(f"{metric:<24} {b:>14.3f} {m:>15.3f}  {arrow}{abs(diff)*100:>5.1f}pp {mark}")
print("=" * 60)

# -- 6. Contamination Sweep ------------------------------------
print("\nRunning contamination parameter sweep...")
contaminations = [0.01, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20]
sw_f1, sw_pr, sw_re, sw_auc = [], [], [], []
for c in contaminations:
    clf = IsolationForest(n_estimators=100, contamination=c, random_state=SEED, n_jobs=-1)
    clf.fit(X_tr_s)
    yp = (clf.predict(X_te_s) == -1).astype(int)
    sc = -clf.score_samples(X_te_s)
    sw_f1.append(f1_score(y_te, yp, zero_division=0))
    sw_pr.append(precision_score(y_te, yp, zero_division=0))
    sw_re.append(recall_score(y_te, yp, zero_division=0))
    sw_auc.append(roc_auc_score(y_te, sc))
    print(f"  contamination={c:.2f} -> F1={sw_f1[-1]:.3f}  AUC={sw_auc[-1]:.3f}")

best_c = contaminations[np.argmax(sw_f1)]
print(f"\nBest contamination by F1: {best_c}")

# -- 7. Save JSON ----------------------------------------------
results = {
    'dataset': 'KDD Cup 1999 (SA subset, 10%)',
    'dataset_size': len(df),
    'anomaly_rate_pct': round(y.mean() * 100, 2),
    'baseline_iqr': {
        'precision': round(iqr_p, 4), 'recall': round(iqr_r, 4),
        'f1': round(iqr_f1, 4), 'roc_auc': round(iqr_auc, 4), 'fp_rate': round(iqr_fpr, 4)
    },
    'isolation_forest': {
        'n_estimators': 100,
        'contamination': round(float(actual_rate), 4),
        'precision': round(if_p, 4), 'recall': round(if_r, 4),
        'f1': round(if_f1, 4), 'roc_auc': round(if_auc, 4), 'fp_rate': round(if_fpr, 4)
    },
    'improvement': {
        'f1_pp':  round((if_f1  - iqr_f1)  * 100, 2),
        'auc_pp': round((if_auc - iqr_auc) * 100, 2),
        'fpr_pp': round((if_fpr - iqr_fpr) * 100, 2),
    },
    'contamination_sweep': {
        'values': contaminations,
        'f1':     [round(v, 4) for v in sw_f1],
        'roc_auc':[round(v, 4) for v in sw_auc],
        'best_contamination': best_c
    }
}
with open('../evaluation/isolation_forest_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nJSON saved: ../evaluation/isolation_forest_results.json")

# -- 8. Plots --------------------------------------------------
print("\nGenerating plots...")

# ROC Curve
fig, ax = plt.subplots(figsize=(7, 6))
for name, scores in [('IQR Baseline', score_iqr), ('IsolationForest (trained)', score_if)]:
    fpr_arr, tpr_arr, _ = roc_curve(y_te, scores)
    auc = roc_auc_score(y_te, scores)
    ax.plot(fpr_arr, tpr_arr, lw=2.5, label=f'{name}  (AUC={auc:.3f})')
ax.plot([0,1],[0,1],'k--',lw=1,alpha=0.5,label='Random')
ax.set_xlabel('False Positive Rate', fontsize=12)
ax.set_ylabel('True Positive Rate', fontsize=12)
ax.set_title('ROC Curve -- KDD Cup 1999\nIQR Baseline vs IsolationForest', fontsize=12, fontweight='bold')
ax.legend(fontsize=10); ax.grid(linestyle='--',alpha=0.4)
plt.tight_layout()
plt.savefig('../evaluation/if_roc_curve.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: if_roc_curve.png")

# Precision-Recall Curve
fig, ax = plt.subplots(figsize=(7, 6))
for name, scores in [('IQR Baseline', score_iqr), ('IsolationForest (trained)', score_if)]:
    p_arr, r_arr, _ = precision_recall_curve(y_te, scores)
    ap = average_precision_score(y_te, scores)
    ax.plot(r_arr, p_arr, lw=2.5, label=f'{name}  (AP={ap:.3f})')
ax.set_xlabel('Recall', fontsize=12); ax.set_ylabel('Precision', fontsize=12)
ax.set_title('Precision-Recall Curve -- KDD Cup 1999', fontsize=12, fontweight='bold')
ax.legend(fontsize=10); ax.grid(linestyle='--',alpha=0.4)
plt.tight_layout()
plt.savefig('../evaluation/if_precision_recall.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: if_precision_recall.png")

# Anomaly Score Distribution
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(score_if[y_te==0], bins=80, alpha=0.55, color='#4ade80', label='Normal',  density=True)
ax.hist(score_if[y_te==1], bins=80, alpha=0.70, color='#f87171', label='Anomaly', density=True)
thresh = np.percentile(score_if, 100*(1 - float(actual_rate)))
ax.axvline(thresh, color='#6366f1', linestyle='--', lw=2, label=f'Decision boundary')
ax.set_xlabel('Anomaly Score (^ = more anomalous)', fontsize=11)
ax.set_ylabel('Density', fontsize=11)
ax.set_title('IsolationForest Anomaly Score Distribution\nKDD Cup 1999', fontsize=12, fontweight='bold')
ax.legend(); ax.grid(linestyle='--',alpha=0.3)
plt.tight_layout()
plt.savefig('../evaluation/if_score_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: if_score_distribution.png")

# Contamination Sweep
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(contaminations, sw_f1,  marker='o', lw=2.5, label='F1 Score',  color='#6366f1')
ax.plot(contaminations, sw_pr,  marker='s', lw=2,   label='Precision', color='#f59e0b')
ax.plot(contaminations, sw_re,  marker='^', lw=2,   label='Recall',    color='#10b981')
ax.axvline(best_c, color='#ef4444', linestyle='--', lw=1.5, label=f'Best F1 @ c={best_c}')
ax.set_xlabel('Contamination Parameter', fontsize=11)
ax.set_ylabel('Score', fontsize=11)
ax.set_title('IsolationForest -- Contamination Sweep\nKDD Cup 1999', fontsize=12, fontweight='bold')
ax.set_ylim(0, 1.05); ax.legend(); ax.grid(linestyle='--',alpha=0.4)
plt.tight_layout()
plt.savefig('../evaluation/if_contamination_sweep.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: if_contamination_sweep.png")

# Confusion Matrices
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, yp, title in zip(axes, [y_pred_iqr, y_pred_if], ['IQR Baseline', 'IsolationForest (Trained)']):
    cm = confusion_matrix(y_te, yp)
    ConfusionMatrixDisplay(cm, display_labels=['Normal','Attack']).plot(ax=ax, colorbar=False, cmap='Blues')
    ax.set_title(title, fontsize=12, fontweight='bold')
plt.suptitle('Confusion Matrix -- KDD Cup 1999', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('../evaluation/if_confusion_matrices.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: if_confusion_matrices.png")

# Bar chart summary
metrics = ['Precision', 'Recall', 'F1', 'ROC-AUC']
iqr_vals = [iqr_p, iqr_r, iqr_f1, iqr_auc]
if_vals  = [if_p,  if_r,  if_f1,  if_auc]
x = np.arange(len(metrics)); w = 0.35
fig, ax = plt.subplots(figsize=(9, 5))
b1 = ax.bar(x - w/2, iqr_vals, w, label='IQR Baseline',           color='#f87171', alpha=0.85)
b2 = ax.bar(x + w/2, if_vals,  w, label='IsolationForest (Trained)', color='#4ade80', alpha=0.85)
for bar in b1 + b2:
    ax.annotate(f'{bar.get_height():.3f}', xy=(bar.get_x()+bar.get_width()/2, bar.get_height()),
                xytext=(0,3), textcoords='offset points', ha='center', va='bottom', fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(metrics, fontsize=11)
ax.set_ylim(0, 1.15); ax.set_ylabel('Score'); ax.legend()
ax.set_title('Performance Comparison -- KDD Cup 1999\nIQR Baseline vs IsolationForest', fontweight='bold')
ax.grid(axis='y', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig('../evaluation/if_metrics_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: if_metrics_comparison.png")

# -- Final Summary ---------------------------------------------
print("\n" + "=" * 60)
print("  FINAL RESULTS -- ISOLATION FOREST (KDD Cup 1999)")
print("=" * 60)
print(f"  {'':24} {'IQR Baseline':>12} {'IsolationForest':>14}")
print(f"  {'-'*52}")
for metric, b, m in [('Precision', iqr_p, if_p), ('Recall', iqr_r, if_r),
                      ('F1 Score', iqr_f1, if_f1), ('ROC-AUC', iqr_auc, if_auc),
                      ('FP Rate (lower=better)', iqr_fpr, if_fpr)]:
    print(f"  {metric:<24} {b:>12.4f} {m:>14.4f}")
print("=" * 60)
print(f"  F1 improvement  : +{results['improvement']['f1_pp']:.2f} pp")
print(f"  AUC improvement : +{results['improvement']['auc_pp']:.2f} pp")
print("=" * 60)
