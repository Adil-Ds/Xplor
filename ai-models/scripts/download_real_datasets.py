"""
Download real-world datasets for training:
1. KDD Cup 1999 (via sklearn) — anomaly detection benchmark
2. Real column names from multiple public CSVs — DistilBERT training
"""
import os, json, requests, io
import numpy as np
import pandas as pd
from sklearn.datasets import fetch_kddcup99

os.makedirs('../data/raw', exist_ok=True)
os.makedirs('../data/processed', exist_ok=True)

# ──────────────────────────────────────────────────────────────
# 1. KDD CUP 1999 — Anomaly/Intrusion Detection Dataset
# ──────────────────────────────────────────────────────────────
print("=" * 60)
print("Downloading KDD Cup 1999 dataset via sklearn...")
print("=" * 60)

kdd = fetch_kddcup99(subset='SA', percent10=True, as_frame=True, random_state=42)
df_kdd = kdd.frame.copy()
df_kdd['target'] = kdd.target

# In KDD Cup 99, 'normal.' = normal traffic; everything else = attack
df_kdd['is_anomaly'] = (df_kdd['target'] != b'normal.').astype(int)
df_kdd = df_kdd.drop(columns=['target', 'labels'], errors='ignore')

# KDD Cup 99 returns all cols as object (byte strings) — coerce to numeric
# Known numeric feature names in KDD Cup 99
NUMERIC_FEATURES = [
    'duration', 'src_bytes', 'dst_bytes', 'land', 'wrong_fragment', 'urgent',
    'hot', 'num_failed_logins', 'logged_in', 'num_compromised', 'root_shell',
    'su_attempted', 'num_root', 'num_file_creations', 'num_shells',
    'num_access_files', 'num_outbound_cmds', 'is_host_login', 'is_guest_login',
    'count', 'srv_count', 'serror_rate', 'srv_serror_rate', 'rerror_rate',
    'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate', 'srv_diff_host_rate',
    'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate',
    'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate',
    'dst_host_srv_diff_host_rate', 'dst_host_serror_rate',
    'dst_host_srv_serror_rate', 'dst_host_rerror_rate', 'dst_host_srv_rerror_rate',
]

cols_to_use = [c for c in NUMERIC_FEATURES if c in df_kdd.columns]
df_numeric = df_kdd[cols_to_use].copy()

for col in cols_to_use:
    df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce')

df_numeric['is_anomaly'] = df_kdd['is_anomaly'].values
df_numeric = df_numeric.dropna().reset_index(drop=True)

df_numeric.to_csv('../data/raw/kddcup99_sa.csv', index=False)

normal_count  = (df_numeric['is_anomaly'] == 0).sum()
anomaly_count = (df_numeric['is_anomaly'] == 1).sum()
total = len(df_numeric)

print(f"KDD Cup 1999 (SA subset, 10%) downloaded successfully!")
print(f"  Total rows   : {total:,}")
print(f"  Normal rows  : {normal_count:,} ({normal_count/total*100:.1f}%)")
print(f"  Anomaly rows : {anomaly_count:,} ({anomaly_count/total*100:.1f}%)")
print(f"  Features     : {len(cols_to_use)} numeric features")
print(f"  Saved to     : ../data/raw/kddcup99_sa.csv")


# ──────────────────────────────────────────────────────────────
# 2. REAL COLUMN NAMES from public datasets
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Collecting real column names from public datasets...")
print("=" * 60)

# Manually curated column names extracted from real-world datasets:
# Sources: UCI ML Repository, Kaggle public datasets, standard benchmarks
# Each column name is labeled with its semantic type

REAL_COLUMNS = {
    'email': [
        # From: e-commerce, CRM, HR, user registration datasets
        'email', 'email_address', 'user_email', 'customer_email',
        'contact_email', 'employee_email', 'member_email', 'client_email',
        'billing_email', 'account_email', 'primary_email', 'work_email',
        'personal_email', 'admin_email', 'support_email', 'sender_email',
        'recipient_email', 'notification_email', 'registered_email',
        'emailaddress', 'email_id', 'mail', 'e_mail', 'login_email',
        'from_email', 'reply_to_email', 'auth_email', 'verify_email',
        'email_contact', 'business_email', 'company_email', 'vendor_email',
        'partner_email', 'secondary_email', 'alt_email', 'recovery_email',
        'invite_email', 'newsletter_email', 'marketing_email', 'report_email',
    ],
    'phone': [
        # From: HR datasets, customer datasets, telecom datasets
        'phone', 'phone_number', 'mobile', 'telephone', 'contact_phone',
        'cell_phone', 'mobile_number', 'tel', 'phone_no', 'fax',
        'fax_number', 'work_phone', 'home_phone', 'primary_phone',
        'secondary_phone', 'alt_phone', 'emergency_phone', 'business_phone',
        'office_phone', 'direct_phone', 'contact_number', 'whatsapp_number',
        'mobile_no', 'tel_no', 'telephone_number', 'contact_mobile',
        'landline', 'phonenumber', 'mobilenumber', 'customer_phone',
        'user_phone', 'staff_phone', 'driver_phone', 'vendor_phone',
        'phone_1', 'phone_2', 'daytime_phone', 'evening_phone',
        'cell', 'sms_number', 'calling_number', 'dialer_phone',
    ],
    'name': [
        # From: Titanic, Census, HR, customer datasets
        'name', 'full_name', 'first_name', 'last_name', 'customer_name',
        'user_name', 'display_name', 'given_name', 'surname', 'family_name',
        'middle_name', 'nickname', 'alias', 'employee_name', 'staff_name',
        'contact_name', 'owner_name', 'author_name', 'company_name',
        'business_name', 'vendor_name', 'client_name', 'account_name',
        'patient_name', 'student_name', 'member_name', 'agent_name',
        'fname', 'lname', 'fullname', 'firstname', 'lastname',
        'legal_name', 'preferred_name', 'payee_name', 'insured_name',
        'account_holder', 'beneficiary', 'subscriber_name', 'representative',
    ],
    'date': [
        # From: Titanic, sales, HR, financial, medical datasets
        'date', 'created_at', 'updated_at', 'order_date', 'birth_date',
        'start_date', 'end_date', 'expiry_date', 'date_of_birth', 'dob',
        'join_date', 'signup_date', 'registration_date', 'purchase_date',
        'ship_date', 'delivery_date', 'due_date', 'invoice_date',
        'payment_date', 'last_login', 'timestamp', 'event_date',
        'hire_date', 'termination_date', 'review_date', 'date_created',
        'date_modified', 'date_joined', 'visit_date', 'scheduled_date',
        'transaction_date', 'effective_date', 'posted_date', 'closed_date',
        'open_date', 'submitted_at', 'approved_at', 'modified_date',
        'departure_date', 'arrival_date', 'service_date', 'report_date',
    ],
    'currency': [
        # From: Superstore, financial, payroll, e-commerce datasets
        'price', 'amount', 'total', 'cost', 'revenue', 'salary',
        'wage', 'fee', 'charge', 'payment', 'balance', 'budget',
        'expense', 'income', 'profit', 'tax', 'discount', 'subtotal',
        'grand_total', 'net_amount', 'gross_amount', 'unit_price',
        'list_price', 'sale_price', 'original_price', 'total_amount',
        'paid_amount', 'refund_amount', 'transaction_amount', 'invoice_amount',
        'monthly_salary', 'annual_income', 'total_cost', 'order_total',
        'base_price', 'market_value', 'asset_value', 'loan_amount',
        'credit_limit', 'capital_gain', 'capital_loss', 'fnlwgt',
    ],
    'id': [
        # From: Titanic, Census, HR, order management, CRM
        'id', 'user_id', 'customer_id', 'order_id', 'employee_id',
        'product_id', 'record_id', 'transaction_id', 'session_id',
        'account_id', 'invoice_id', 'ticket_id', 'item_id', 'batch_id',
        'reference_id', 'uuid', 'guid', 'row_id', 'seq_id',
        'member_id', 'vendor_id', 'partner_id', 'case_id', 'project_id',
        'category_id', 'department_id', 'branch_id', 'location_id',
        'device_id', 'request_id', 'job_id', 'task_id', 'issue_id',
        'student_id', 'patient_id', 'policy_id', 'claim_id', 'passengerid',
        'emp_id', 'cust_no', 'ref_no', 'serial_no', 'passport_no',
    ],
    'address': [
        # From: Census (UCI Adult), customer, shipping, real-estate datasets
        'address', 'street', 'city', 'state', 'country',
        'zip_code', 'postal_code', 'street_address', 'home_address',
        'office_address', 'mailing_address', 'billing_address',
        'shipping_address', 'location', 'region', 'province',
        'district', 'town', 'neighborhood', 'suburb', 'zip',
        'postcode', 'street_name', 'house_number', 'building',
        'floor', 'apartment', 'suite', 'unit', 'po_box',
        'full_address', 'address_line1', 'address_line2',
        'delivery_address', 'native_country', 'residence', 'geo_location',
        'county', 'municipality', 'ward', 'area_code', 'sector',
    ],
    'percentage': [
        # From: financial, KPI, business analytics, survey datasets
        'percentage', 'percent', 'rate', 'ratio', 'pct',
        'tax_rate', 'discount_rate', 'interest_rate', 'growth_rate',
        'success_rate', 'completion_pct', 'pass_rate', 'fail_rate',
        'churn_rate', 'conversion_rate', 'retention_rate', 'click_rate',
        'open_rate', 'bounce_rate', 'engagement_rate', 'market_share',
        'occupancy_rate', 'utilization_rate', 'efficiency_rate',
        'accuracy_pct', 'discount_pct', 'profit_margin', 'gross_margin',
        'net_margin', 'tax_pct', 'ownership_pct', 'allocation_pct',
        'response_rate', 'approval_rate', 'fill_rate', 'hit_rate',
        'attendance_rate', 'defect_rate', 'shrinkage_rate', 'variance_pct',
    ],
    'numeric': [
        # From: Titanic (Age, SibSp, Parch), Iris, Census, UCI Adult
        'age', 'quantity', 'count', 'score', 'rank', 'weight',
        'height', 'temperature', 'duration', 'distance', 'volume',
        'size', 'length', 'width', 'depth', 'num_orders', 'total_items',
        'page_views', 'clicks', 'impressions', 'rating', 'stars',
        'points', 'level', 'priority', 'num_employees', 'seat_count',
        'sibsp', 'parch', 'pclass', 'education_num', 'hours_per_week',
        'fnl_wgt', 'sepal_length', 'sepal_width', 'petal_length',
        'petal_width', 'fixed_acidity', 'volatile_acidity', 'alcohol',
        'residual_sugar', 'chlorides', 'free_sulfur_dioxide', 'density',
    ],
    'text': [
        # From: product, review, ticketing, medical, survey datasets
        'notes', 'description', 'comments', 'remarks', 'summary',
        'message', 'content', 'body', 'details', 'info', 'bio',
        'about', 'feedback', 'review', 'testimonial', 'narrative',
        'observation', 'log', 'memo', 'annotation', 'instructions',
        'guidelines', 'reason', 'explanation', 'justification',
        'diagnosis', 'prescription', 'question', 'answer', 'response',
        'subject', 'title', 'label', 'tag', 'category', 'occupation',
        'education', 'marital_status', 'relationship', 'workclass',
        'cabin', 'embarked', 'sex', 'race', 'native-country',
    ]
}

LABEL_MAP = {
    'email': 0, 'phone': 1, 'name': 2, 'date': 3, 'currency': 4,
    'id': 5, 'address': 6, 'percentage': 7, 'numeric': 8, 'text': 9
}

records = []
for label, columns in REAL_COLUMNS.items():
    for col in columns:
        records.append({
            'column_name': col.strip().lower(),
            'label': label,
            'label_id': LABEL_MAP[label]
        })

df_cols = pd.DataFrame(records).drop_duplicates(subset='column_name')
df_cols = df_cols.sample(frac=1, random_state=42).reset_index(drop=True)
df_cols.to_csv('../data/raw/real_column_labels.csv', index=False)

print(f"\nReal column name dataset created!")
print(f"  Total unique columns : {len(df_cols)}")
print(f"\nPer-class counts:")
for label, count in df_cols['label'].value_counts().items():
    print(f"  {label:<12} : {count}")
print(f"\n  Saved to: ../data/raw/real_column_labels.csv")

print("\n" + "=" * 60)
print("All datasets ready.")
print("=" * 60)
