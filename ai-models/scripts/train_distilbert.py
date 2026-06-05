# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding="utf-8")
"""
DistilBERT Fine-Tuning for Column Semantic Labeling
Uses real column names collected from public datasets (Titanic, UCI Adult, etc.)
Before: zero-shot DistilBERT-MNLI | After: fine-tuned DistilBERT
"""
import os, json, warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report,
    confusion_matrix, ConfusionMatrixDisplay
)
import torch
from torch.utils.data import Dataset
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    TrainingArguments, Trainer,
    pipeline, EarlyStoppingCallback
)

os.makedirs('../evaluation', exist_ok=True)
os.makedirs('../models/distilbert-col-labeling', exist_ok=True)

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

LABEL_MAP = {
    'email':0,'phone':1,'name':2,'date':3,'currency':4,
    'id':5,'address':6,'percentage':7,'numeric':8,'text':9
}
ID2LABEL   = {v:k for k,v in LABEL_MAP.items()}
CLASS_NAMES = list(LABEL_MAP.keys())

# -- 1. Load dataset -------------------------------------------
print("=" * 60)
print("DistilBERT -- Column Semantic Labeling")
print("Dataset: Real column names from public ML datasets")
print("=" * 60)

df = pd.read_csv('../data/raw/real_column_labels.csv')
print(f"\nDataset loaded: {len(df)} unique real column names")
print(f"Classes: {df['label'].value_counts().to_dict()}\n")

texts  = df['column_name'].tolist()
labels = df['label_id'].tolist()

X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.20, random_state=SEED, stratify=labels
)
print(f"Train: {len(X_train)} | Test: {len(X_test)}")

# -- 2. Baseline -- Zero-Shot ----------------------------------
print("\n--- STEP 1: Baseline (Zero-Shot MNLI, no training) ---")
print("Loading typeform/distilbert-base-uncased-mnli...")
zero_shot = pipeline(
    'zero-shot-classification',
    model='typeform/distilbert-base-uncased-mnli',
    device=0 if DEVICE=='cuda' else -1
)

y_pred_base = []
for i, col in enumerate(X_test):
    res  = zero_shot(col, candidate_labels=CLASS_NAMES)
    best = res['labels'][0]
    y_pred_base.append(LABEL_MAP[best])
    if (i+1) % 20 == 0:
        print(f"  Baseline: {i+1}/{len(X_test)} done...")

base_acc = accuracy_score(y_test, y_pred_base)
base_f1  = f1_score(y_test, y_pred_base, average='macro', zero_division=0)
print(f"\nBaseline Zero-Shot:  Accuracy={base_acc*100:.1f}%  Macro-F1={base_f1*100:.1f}%")
print(classification_report(y_test, y_pred_base, target_names=CLASS_NAMES, zero_division=0))

# -- 3. Fine-Tune ---------------------------------------------
print("--- STEP 2: Fine-Tune distilbert-base-uncased ---")

tokenizer = DistilBertTokenizerFast.from_pretrained('distilbert-base-uncased')

class ColDataset(Dataset):
    def __init__(self, texts, labels, tok, max_len=32):
        self.enc    = tok(texts, truncation=True, padding=True, max_length=max_len)
        self.labels = labels
    def __len__(self): return len(self.labels)
    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k,v in self.enc.items()}
        item['labels'] = torch.tensor(self.labels[i])
        return item

X_tr, X_val, y_tr, y_val = train_test_split(X_train, y_train, test_size=0.10, random_state=SEED)
tr_ds  = ColDataset(X_tr,  y_tr,  tokenizer)
val_ds = ColDataset(X_val, y_val, tokenizer)
te_ds  = ColDataset(X_test, y_test, tokenizer)

def compute_metrics(ep):
    preds = np.argmax(ep.predictions, axis=-1)
    return {
        'accuracy': accuracy_score(ep.label_ids, preds),
        'f1_macro': f1_score(ep.label_ids, preds, average='macro', zero_division=0)
    }

ft_model = DistilBertForSequenceClassification.from_pretrained(
    'distilbert-base-uncased', num_labels=10, id2label=ID2LABEL, label2id=LABEL_MAP
)

args = TrainingArguments(
    output_dir='../models/distilbert-col-labeling',
    num_train_epochs=5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_ratio=0.1,
    eval_strategy='epoch',
    save_strategy='epoch',
    load_best_model_at_end=True,
    metric_for_best_model='f1_macro',
    logging_dir='../models/logs',
    logging_steps=5,
    seed=SEED,
    report_to='none'
)

trainer = Trainer(
    model=ft_model, args=args,
    train_dataset=tr_ds, eval_dataset=val_ds,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
)

print(f"\nFine-tuning on {len(tr_ds)} examples for up to 5 epochs...")
trainer.train()
print("Fine-tuning complete!")
trainer.save_model('../models/distilbert-col-labeling/best')

# -- 4. Evaluate Fine-Tuned ------------------------------------
print("\n--- STEP 3: Evaluate Fine-Tuned Model ---")
preds_out = trainer.predict(te_ds)
y_pred_ft = np.argmax(preds_out.predictions, axis=-1)

ft_acc = accuracy_score(y_test, y_pred_ft)
ft_f1  = f1_score(y_test, y_pred_ft, average='macro', zero_division=0)
print(f"Fine-Tuned:  Accuracy={ft_acc*100:.1f}%  Macro-F1={ft_f1*100:.1f}%")
print(classification_report(y_test, y_pred_ft, target_names=CLASS_NAMES, zero_division=0))

# -- 5. Summary Table ------------------------------------------
base_rep = classification_report(y_test, y_pred_base, target_names=CLASS_NAMES,
                                  output_dict=True, zero_division=0)
ft_rep   = classification_report(y_test, y_pred_ft,   target_names=CLASS_NAMES,
                                  output_dict=True, zero_division=0)

print("\n" + "=" * 68)
print(f"{'Class':<14} {'Baseline F1':>12} {'Fine-Tuned F1':>14} {'Improvement':>13}")
print("-" * 68)
for cls in CLASS_NAMES:
    bf = base_rep[cls]['f1-score'] * 100
    ff = ft_rep[cls]['f1-score']   * 100
    diff = ff - bf
    print(f"{cls:<14} {bf:>12.1f}% {ff:>13.1f}% {diff:>+12.1f}pp")
print("-" * 68)
print(f"{'MACRO AVG':<14} {base_f1*100:>12.1f}% {ft_f1*100:>13.1f}% {(ft_f1-base_f1)*100:>+12.1f}pp")
print(f"{'ACCURACY':<14} {base_acc*100:>12.1f}% {ft_acc*100:>13.1f}% {(ft_acc-base_acc)*100:>+12.1f}pp")
print("=" * 68)

# -- 6. Save JSON ---------------------------------------------
results = {
    'dataset': 'Real column names from public ML datasets (Titanic, UCI Adult, etc.)',
    'dataset_size': len(df),
    'num_classes': 10,
    'baseline': {
        'model': 'typeform/distilbert-base-uncased-mnli (zero-shot)',
        'accuracy_pct': round(base_acc*100, 2),
        'macro_f1_pct': round(base_f1*100,  2),
        'per_class_f1': {c: round(base_rep[c]['f1-score']*100,1) for c in CLASS_NAMES}
    },
    'finetuned': {
        'model': 'distilbert-base-uncased (fine-tuned, 5 epochs)',
        'accuracy_pct': round(ft_acc*100, 2),
        'macro_f1_pct': round(ft_f1*100,  2),
        'per_class_f1': {c: round(ft_rep[c]['f1-score']*100,1) for c in CLASS_NAMES}
    },
    'improvement': {
        'accuracy_pp': round((ft_acc - base_acc)*100, 2),
        'f1_pp':       round((ft_f1  - base_f1) *100, 2),
    }
}
with open('../evaluation/distilbert_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nJSON saved: ../evaluation/distilbert_results.json")

# -- 7. Plots -------------------------------------------------
print("\nGenerating plots...")

# Confusion matrices
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for ax, yp, title in zip(axes,
    [y_pred_base, y_pred_ft],
    ['Zero-Shot Baseline', 'Fine-Tuned DistilBERT']
):
    cm = confusion_matrix(y_test, yp)
    ConfusionMatrixDisplay(cm, display_labels=CLASS_NAMES).plot(
        ax=ax, colorbar=False, cmap='Blues', xticks_rotation=45)
    ax.set_title(title, fontsize=12, fontweight='bold')
plt.suptitle('Confusion Matrix -- Column Semantic Labeling\nBefore vs After Fine-Tuning',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('../evaluation/distilbert_confusion_matrices.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: distilbert_confusion_matrices.png")

# Per-class F1 bar chart
bf_arr = [base_rep[c]['f1-score']*100 for c in CLASS_NAMES]
ff_arr = [ft_rep[c]['f1-score']  *100 for c in CLASS_NAMES]
x = np.arange(len(CLASS_NAMES)); w = 0.35
fig, ax = plt.subplots(figsize=(13, 5))
b1 = ax.bar(x - w/2, bf_arr, w, label='Zero-Shot Baseline', color='#f87171', alpha=0.85)
b2 = ax.bar(x + w/2, ff_arr, w, label='Fine-Tuned DistilBERT', color='#4ade80', alpha=0.85)
for bar in list(b1) + list(b2):
    ax.annotate(f'{bar.get_height():.0f}',
                xy=(bar.get_x()+bar.get_width()/2, bar.get_height()),
                xytext=(0,2), textcoords='offset points',
                ha='center', va='bottom', fontsize=7.5)
ax.set_xticks(x); ax.set_xticklabels(CLASS_NAMES, rotation=30, ha='right')
ax.set_ylim(0, 115); ax.set_ylabel('F1 Score (%)')
ax.set_title('Per-Class F1 Score -- Column Semantic Labeling\nReal Dataset: Column Names from Titanic, UCI Adult, etc.',
             fontweight='bold')
ax.legend(); ax.grid(axis='y', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig('../evaluation/distilbert_per_class_f1.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: distilbert_per_class_f1.png")

# Overall accuracy / F1 bar
fig, ax = plt.subplots(figsize=(7, 5))
cats = ['Accuracy', 'Macro F1']
bv   = [base_acc*100, base_f1*100]
fv   = [ft_acc*100,   ft_f1*100]
xp   = np.arange(2)
b1   = ax.bar(xp - 0.2, bv, 0.4, label='Zero-Shot Baseline',    color='#f87171', alpha=0.85)
b2   = ax.bar(xp + 0.2, fv, 0.4, label='Fine-Tuned DistilBERT', color='#4ade80', alpha=0.85)
for bar in list(b1) + list(b2):
    ax.annotate(f'{bar.get_height():.1f}%',
                xy=(bar.get_x()+bar.get_width()/2, bar.get_height()),
                xytext=(0,3), textcoords='offset points',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_xticks(xp); ax.set_xticklabels(cats, fontsize=12)
ax.set_ylim(0, 115); ax.set_ylabel('Score (%)')
ax.set_title('Overall Performance\nBefore vs After Fine-Tuning', fontweight='bold', fontsize=12)
ax.legend(); ax.grid(axis='y', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig('../evaluation/distilbert_overall_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: distilbert_overall_comparison.png")

# Training curves from log history
log_history = trainer.state.log_history
train_logs  = [x for x in log_history if 'loss' in x and 'eval_loss' not in x]
eval_logs   = [x for x in log_history if 'eval_loss' in x]
if train_logs and eval_logs:
    t_steps  = [x['step']  for x in train_logs]
    t_loss   = [x['loss']  for x in train_logs]
    e_epochs = [x['epoch'] for x in eval_logs]
    e_acc    = [x.get('eval_accuracy',0)*100 for x in eval_logs]
    e_f1     = [x.get('eval_f1_macro',0)*100 for x in eval_logs]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].plot(t_steps, t_loss, color='#6366f1', lw=1.5)
    axes[0].set_title('Training Loss'); axes[0].set_xlabel('Step')
    axes[0].grid(linestyle='--',alpha=0.4)
    axes[1].plot(e_epochs, e_acc, marker='o', color='#f59e0b', lw=2)
    axes[1].set_title('Validation Accuracy (%)'); axes[1].set_xlabel('Epoch')
    axes[1].set_ylim(0,100); axes[1].grid(linestyle='--',alpha=0.4)
    axes[2].plot(e_epochs, e_f1, marker='s', color='#10b981', lw=2)
    axes[2].set_title('Validation Macro F1 (%)'); axes[2].set_xlabel('Epoch')
    axes[2].set_ylim(0,100); axes[2].grid(linestyle='--',alpha=0.4)
    plt.suptitle('DistilBERT Fine-Tuning Progress', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig('../evaluation/distilbert_training_curves.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: distilbert_training_curves.png")

# -- Final Print ----------------------------------------------
print("\n" + "=" * 60)
print("  FINAL RESULTS -- DISTILBERT COLUMN LABELING")
print(f"  Dataset: {results['dataset']}")
print("=" * 60)
print(f"  Zero-Shot Baseline : Accuracy={results['baseline']['accuracy_pct']}%  F1={results['baseline']['macro_f1_pct']}%")
print(f"  Fine-Tuned Model   : Accuracy={results['finetuned']['accuracy_pct']}%  F1={results['finetuned']['macro_f1_pct']}%")
print(f"  Improvement        : +{results['improvement']['accuracy_pp']}pp accuracy  +{results['improvement']['f1_pp']}pp F1")
print("=" * 60)
print("  Model saved: ../models/distilbert-col-labeling/best")
print("  Plots saved: ../evaluation/")
print("=" * 60)
