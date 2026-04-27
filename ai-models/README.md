# AI Models

## Owner: Mareeha Nadeem (DS-33)

## Structure

```
ai-models/
├── data/
│   ├── raw/              # Raw datasets (git-ignored)
│   └── processed/        # Processed datasets (git-ignored)
├── notebooks/
│   ├── 01_anomaly_detection.ipynb    # Isolation Forest + LSTM
│   ├── 02_data_quality_classifier.ipynb  # distilBERT fine-tuning
│   ├── 03_nl_query_model.ipynb       # T5-small fine-tuning
│   └── 04_risk_score_regressor.ipynb # XGBoost training
├── models/               # Saved model files (git-ignored — use DVC or releases)
├── scripts/
│   ├── train_anomaly.py
│   ├── train_quality.py
│   ├── train_nlquery.py
│   └── train_risk.py
├── evaluation/           # Metrics, plots, reports
└── requirements.txt
```

## Model Info

| Model | Algorithm | Dataset |
|---|---|---|
| Anomaly Detection | IF + LSTM | KDD Cup '99 / NSL-KDD |
| Data Quality Classifier | distilBERT | Synthetic dirty/clean pairs |
| NL Query | T5-small | WikiSQL + Spider |
| Risk Score Regressor | XGBoost | Auto-generated per-file |

## Rules

- **Clear notebook outputs** before committing (`Kernel → Restart & Clear Output`).
- Save trained models as GitHub Release assets, not committed files.
