"""
Olist E-Commerce Machine Learning Models
Three models built on top of the analytical dataset:
  1. Delivery delay classification (Random Forest)
  2. Review score regression (Random Forest)
  3. Customer segmentation (K-Means on RFM)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import (
    accuracy_score, roc_auc_score, roc_curve, confusion_matrix,
    precision_score, recall_score,
    r2_score, mean_squared_error, mean_absolute_error, silhouette_score,
)

sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 100

DATA_DIR = Path('data/raw')
OUT_DIR = Path('ml_models')
OUT_DIR.mkdir(exist_ok=True)

RANDOM_STATE = 42


def load_raw():
    """Load the raw CSVs needed for feature engineering."""
    files = {
        'orders': 'olist_orders_dataset.csv',
        'items': 'olist_order_items_dataset.csv',
        'products': 'olist_products_dataset.csv',
        'payments': 'olist_order_payments_dataset.csv',
        'reviews': 'olist_order_reviews_dataset.csv',
        'customers': 'olist_customers_dataset.csv',
    }
    data = {key: pd.read_csv(DATA_DIR / name) for key, name in files.items()}
    for key, df in data.items():
        print(f"Loaded {files[key]}: {df.shape[0]:,} rows")
    return data


def build_feature_table(data):
    """
    Join orders -> items -> products -> payments -> reviews -> customers
    into one order-item-level table with delivery and review features.
    """
    orders = data['orders'].copy()
    for col in ['order_purchase_timestamp', 'order_delivered_customer_date',
                'order_estimated_delivery_date']:
        orders[col] = pd.to_datetime(orders[col])

    # Only delivered orders have an actual delivery date to compare against
    orders = orders[orders['order_status'] == 'delivered'].dropna(
        subset=['order_delivered_customer_date'])

    orders['actual_delivery_days'] = (
        orders['order_delivered_customer_date'] - orders['order_purchase_timestamp']
    ).dt.days
    orders['estimated_delivery_days'] = (
        orders['order_estimated_delivery_date'] - orders['order_purchase_timestamp']
    ).dt.days
    orders['is_late'] = (
        orders['order_delivered_customer_date'] > orders['order_estimated_delivery_date']
    ).astype(int)
    orders['purchase_month'] = orders['order_purchase_timestamp'].dt.month
    orders['purchase_dayofweek'] = orders['order_purchase_timestamp'].dt.dayofweek

    items = (data['items']
             .groupby('order_id')
             .agg(price=('price', 'sum'),
                  freight_value=('freight_value', 'sum'),
                  n_items=('order_item_id', 'count'),
                  product_id=('product_id', 'first'))
             .reset_index())

    products = data['products'][['product_id', 'product_weight_g',
                                  'product_length_cm', 'product_height_cm',
                                  'product_width_cm', 'product_category_name']]

    payments = (data['payments']
                .groupby('order_id')
                .agg(payment_value=('payment_value', 'sum'),
                     payment_installments=('payment_installments', 'max'))
                .reset_index())

    reviews = data['reviews'][['order_id', 'review_score']].drop_duplicates('order_id')

    df = (orders
          .merge(items, on='order_id', how='inner')
          .merge(products, on='product_id', how='left')
          .merge(payments, on='order_id', how='inner')
          .merge(reviews, on='order_id', how='left')
          .merge(data['customers'][['customer_id', 'customer_unique_id', 'customer_state']],
                 on='customer_id', how='left'))

    print(f"\nFeature table: {df.shape[0]:,} rows, {df.shape[1]} columns")
    return df


def delivery_delay_model(df):
    """Model 1: predict whether an order will arrive late."""
    print("\n" + "=" * 60)
    print("MODEL 1: DELIVERY DELAY PREDICTION")
    print("=" * 60)

    features = ['price', 'freight_value', 'n_items', 'product_weight_g',
                'product_length_cm', 'product_height_cm', 'product_width_cm',
                'payment_installments', 'estimated_delivery_days',
                'purchase_month', 'purchase_dayofweek']
    model_df = df.dropna(subset=features + ['is_late'])

    X = model_df[features]
    y = model_df['is_late']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y)

    clf = RandomForestClassifier(n_estimators=200, max_depth=10,
                                  random_state=RANDOM_STATE, n_jobs=-1,
                                  class_weight='balanced')
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)

    print(f"Accuracy:  {accuracy:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")

    importances = pd.Series(clf.feature_importances_, index=features).sort_values(ascending=False)
    print("\nTop features:")
    print(importances.head(5))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['On Time', 'Late'], yticklabels=['On Time', 'Late'], ax=ax)
    ax.set_xlabel('Predicted')
    ax.set_ylabel('Actual')
    ax.set_title(f'Delivery Delay: Confusion Matrix (Accuracy={accuracy:.1%})')
    plt.tight_layout()
    plt.savefig(OUT_DIR / '01_delivery_confusion_matrix.png', dpi=300, bbox_inches='tight')
    plt.show()

    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, linewidth=2, label=f'ROC-AUC = {roc_auc:.3f}')
    ax.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Random')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('Delivery Delay: ROC Curve')
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / '02_delivery_roc_curve.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Feature importance
    fig, ax = plt.subplots(figsize=(8, 6))
    importances.sort_values().plot(kind='barh', ax=ax, color='steelblue')
    ax.set_xlabel('Importance')
    ax.set_title('Delivery Delay: Feature Importance')
    plt.tight_layout()
    plt.savefig(OUT_DIR / '03_delivery_feature_importance.png', dpi=300, bbox_inches='tight')
    plt.show()

    return {
        'accuracy': accuracy, 'roc_auc': roc_auc,
        'precision': precision, 'recall': recall,
        'top_features': importances.head(3).to_dict(),
    }


def review_score_model(df):
    """Model 2: predict the review score an order will receive."""
    print("\n" + "=" * 60)
    print("MODEL 2: REVIEW SCORE PREDICTION")
    print("=" * 60)

    features = ['price', 'freight_value', 'n_items', 'payment_installments',
                'payment_value', 'actual_delivery_days', 'estimated_delivery_days',
                'is_late']
    model_df = df.dropna(subset=features + ['review_score'])

    X = model_df[features]
    y = model_df['review_score']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    reg = RandomForestRegressor(n_estimators=200, max_depth=10,
                                 random_state=RANDOM_STATE, n_jobs=-1)
    reg.fit(X_train_scaled, y_train)

    y_pred = reg.predict(X_test_scaled)

    r2 = r2_score(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred) ** 0.5
    mae = mean_absolute_error(y_test, y_pred)

    print(f"R^2 Score: {r2:.4f}")
    print(f"RMSE:      {rmse:.4f} stars")
    print(f"MAE:       {mae:.4f} stars")

    importances = pd.Series(reg.feature_importances_, index=features).sort_values(ascending=False)
    print("\nTop features:")
    print(importances.head(5))

    # Actual vs predicted
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(y_test, y_pred, alpha=0.15, s=15, color='teal')
    ax.plot([1, 5], [1, 5], linestyle='--', color='red', label='Perfect prediction')
    ax.set_xlabel('Actual Review Score')
    ax.set_ylabel('Predicted Review Score')
    ax.set_title(f'Review Score: Actual vs Predicted (R²={r2:.3f})')
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / '04_review_actual_vs_predicted.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Feature importance
    fig, ax = plt.subplots(figsize=(8, 6))
    importances.sort_values().plot(kind='barh', ax=ax, color='darkorange')
    ax.set_xlabel('Importance')
    ax.set_title('Review Score: Feature Importance')
    plt.tight_layout()
    plt.savefig(OUT_DIR / '05_review_feature_importance.png', dpi=300, bbox_inches='tight')
    plt.show()

    return {
        'r2': r2, 'rmse': rmse, 'mae': mae,
        'top_features': importances.head(3).to_dict(),
    }


def customer_segmentation_model(df):
    """Model 3: K-Means clustering on RFM features."""
    print("\n" + "=" * 60)
    print("MODEL 3: CUSTOMER SEGMENTATION (K-MEANS)")
    print("=" * 60)

    snapshot_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

    rfm = df.groupby('customer_unique_id').agg(
        last_purchase=('order_purchase_timestamp', 'max'),
        frequency=('order_id', 'nunique'),
        monetary=('payment_value', 'sum'),
    )
    rfm['recency'] = (snapshot_date - rfm['last_purchase']).dt.days
    rfm = rfm.drop(columns=['last_purchase'])

    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm[['recency', 'frequency', 'monetary']])

    k = 4
    kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
    rfm['cluster'] = kmeans.fit_predict(rfm_scaled)

    sil_score = silhouette_score(rfm_scaled, rfm['cluster'], sample_size=10000, random_state=RANDOM_STATE)
    print(f"Customers analyzed: {len(rfm):,}")
    print(f"Silhouette Score: {sil_score:.4f}")

    cluster_profile = rfm.groupby('cluster')[['recency', 'frequency', 'monetary']].mean().round(2)
    cluster_profile['count'] = rfm.groupby('cluster').size()
    print("\nCluster profiles:")
    print(cluster_profile)

    # Name clusters by monetary rank so labels are meaningful
    rank = cluster_profile['monetary'].sort_values(ascending=False).index.tolist()
    labels_by_rank = ['Champions', 'Loyal', 'At Risk', 'Lost']
    label_map = {cluster_id: labels_by_rank[i] for i, cluster_id in enumerate(rank)}
    rfm['segment'] = rfm['cluster'].map(label_map)

    fig, ax = plt.subplots(figsize=(8, 6))
    palette = sns.color_palette('Set2', k)
    for i, cluster_id in enumerate(rank):
        subset = rfm[rfm['cluster'] == cluster_id]
        ax.scatter(subset['frequency'], subset['monetary'], s=15, alpha=0.4,
                   color=palette[i], label=label_map[cluster_id])
    ax.set_xlabel('Frequency (# orders)')
    ax.set_ylabel('Monetary (total spend, BRL)')
    ax.set_yscale('log')
    ax.set_title(f'Customer Segments — K-Means (k={k}, silhouette={sil_score:.3f})')
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / '06_customer_segmentation.png', dpi=300, bbox_inches='tight')
    plt.show()

    return {
        'k': k, 'silhouette': sil_score,
        'segment_counts': rfm['segment'].value_counts().to_dict(),
        'cluster_profile': cluster_profile,
    }, rfm


def write_summary_report(delivery_metrics, review_metrics, segmentation_metrics):
    lines = []
    lines.append("OLIST E-COMMERCE ML MODELS — SUMMARY REPORT")
    lines.append("=" * 60)

    lines.append("\nModel 1: Delivery Delay Prediction (Random Forest Classifier)")
    lines.append(f"  Accuracy:  {delivery_metrics['accuracy']:.4f}")
    lines.append(f"  ROC-AUC:   {delivery_metrics['roc_auc']:.4f}")
    lines.append(f"  Precision: {delivery_metrics['precision']:.4f}")
    lines.append(f"  Recall:    {delivery_metrics['recall']:.4f}")
    lines.append(f"  Top features: {list(delivery_metrics['top_features'].keys())}")

    lines.append("\nModel 2: Review Score Prediction (Random Forest Regressor)")
    lines.append(f"  R^2 Score: {review_metrics['r2']:.4f}")
    lines.append(f"  RMSE:      {review_metrics['rmse']:.4f} stars")
    lines.append(f"  MAE:       {review_metrics['mae']:.4f} stars")
    lines.append(f"  Top features: {list(review_metrics['top_features'].keys())}")

    lines.append("\nModel 3: Customer Segmentation (K-Means, RFM)")
    lines.append(f"  k: {segmentation_metrics['k']}")
    lines.append(f"  Silhouette Score: {segmentation_metrics['silhouette']:.4f}")
    lines.append(f"  Segment sizes: {segmentation_metrics['segment_counts']}")

    report = "\n".join(lines)
    (OUT_DIR / 'MODEL_SUMMARY_REPORT.txt').write_text(report, encoding='utf-8')
    print("\n" + report)


def main():
    print("=" * 60)
    print("OLIST E-COMMERCE ML MODELS")
    print("=" * 60)

    data = load_raw()
    df = build_feature_table(data)

    delivery_metrics = delivery_delay_model(df)
    review_metrics = review_score_model(df)
    segmentation_metrics, rfm = customer_segmentation_model(df)

    write_summary_report(delivery_metrics, review_metrics, segmentation_metrics)

    print(f"\nAll outputs written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
