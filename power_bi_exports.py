"""
Generates clean, pre-aggregated CSV exports for building a Power BI dashboard.
Each file is a flat, ready-to-import table -- no further transformation
should be needed inside Power BI beyond dropping them onto visuals.
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path('data/raw')
OUT_DIR = Path('power_bi/exports')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load():
    orders = pd.read_csv(DATA_DIR / 'olist_orders_dataset.csv')
    payments = pd.read_csv(DATA_DIR / 'olist_order_payments_dataset.csv')
    customers = pd.read_csv(DATA_DIR / 'olist_customers_dataset.csv')
    reviews = pd.read_csv(DATA_DIR / 'olist_order_reviews_dataset.csv')
    items = pd.read_csv(DATA_DIR / 'olist_order_items_dataset.csv')
    products = pd.read_csv(DATA_DIR / 'olist_products_dataset.csv')
    translation = pd.read_csv(DATA_DIR / 'product_category_name_translation.csv')

    orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'])
    orders['order_month'] = orders['order_purchase_timestamp'].dt.to_period('M').astype(str)

    df = (orders
          .merge(payments, on='order_id', how='inner')
          .merge(customers, on='customer_id', how='inner')
          .merge(reviews[['order_id', 'review_score']], on='order_id', how='left'))

    return df, orders, items, products, translation


def export_kpi_summary(df):
    total_revenue = df['payment_value'].sum()
    total_orders = df['order_id'].nunique()
    total_customers = df['customer_unique_id'].nunique()
    total_sellers = None  # not joined here; left as NA to keep this table order-level
    avg_order_value = total_revenue / total_orders

    kpi = pd.DataFrame([{
        'total_revenue': round(total_revenue, 2),
        'total_orders': total_orders,
        'total_customers': total_customers,
        'avg_order_value': round(avg_order_value, 2),
    }])
    kpi.to_csv(OUT_DIR / 'kpi_summary.csv', index=False)
    print(f"kpi_summary.csv: {kpi.shape}")


def export_monthly_revenue(df):
    monthly = (df.groupby('order_month')['payment_value']
               .sum().reset_index()
               .rename(columns={'payment_value': 'revenue'}))
    monthly.to_csv(OUT_DIR / 'monthly_revenue.csv', index=False)
    print(f"monthly_revenue.csv: {monthly.shape}")


def export_revenue_by_state(df):
    by_state = (df.groupby('customer_state')
                .agg(revenue=('payment_value', 'sum'),
                     customers=('customer_unique_id', 'nunique'),
                     orders=('order_id', 'nunique'))
                .reset_index()
                .sort_values('revenue', ascending=False))
    by_state.to_csv(OUT_DIR / 'revenue_by_state.csv', index=False)
    print(f"revenue_by_state.csv: {by_state.shape}")


def export_payment_methods(df):
    pm = (df.groupby('payment_type')
          .agg(orders=('order_id', 'nunique'),
               avg_order_value=('payment_value', 'mean'),
               total_revenue=('payment_value', 'sum'))
          .reset_index()
          .sort_values('orders', ascending=False))
    pm['avg_order_value'] = pm['avg_order_value'].round(2)
    pm.to_csv(OUT_DIR / 'payment_methods.csv', index=False)
    print(f"payment_methods.csv: {pm.shape}")


def export_order_status(orders):
    status = (orders['order_status'].value_counts()
              .rename_axis('order_status').reset_index(name='order_count'))
    status['pct_of_orders'] = (status['order_count'] / status['order_count'].sum() * 100).round(2)
    status.to_csv(OUT_DIR / 'order_status.csv', index=False)
    print(f"order_status.csv: {status.shape}")


def export_top_categories(items, products, translation):
    cat = (items
           .merge(products[['product_id', 'product_category_name']], on='product_id', how='left')
           .merge(translation, on='product_category_name', how='left'))
    cat['category'] = cat['product_category_name_english'].fillna(cat['product_category_name']).fillna('unknown')
    top = (cat.groupby('category')
           .agg(revenue=('price', 'sum'),
                orders=('order_id', 'nunique'),
                avg_price=('price', 'mean'))
           .reset_index()
           .sort_values('revenue', ascending=False)
           .head(20))
    top['avg_price'] = top['avg_price'].round(2)
    top.to_csv(OUT_DIR / 'top_categories.csv', index=False)
    print(f"top_categories.csv: {top.shape}")


def export_delivery_performance(orders):
    delivered = orders[orders['order_status'] == 'delivered'].dropna(
        subset=['order_delivered_customer_date'])
    for col in ['order_purchase_timestamp', 'order_delivered_customer_date',
                'order_estimated_delivery_date']:
        delivered[col] = pd.to_datetime(delivered[col])
    delivered = delivered.copy()
    delivered['delivery_days'] = (delivered['order_delivered_customer_date']
                                   - delivered['order_purchase_timestamp']).dt.days
    delivered['is_late'] = (delivered['order_delivered_customer_date']
                             > delivered['order_estimated_delivery_date'])

    summary = pd.DataFrame([{
        'avg_delivery_days': round(delivered['delivery_days'].mean(), 2),
        'median_delivery_days': delivered['delivery_days'].median(),
        'on_time_rate_pct': round((~delivered['is_late']).mean() * 100, 2),
        'late_rate_pct': round(delivered['is_late'].mean() * 100, 2),
        'orders_analyzed': len(delivered),
    }])
    summary.to_csv(OUT_DIR / 'delivery_performance.csv', index=False)
    print(f"delivery_performance.csv: {summary.shape}")


def export_rfm_segments(df):
    snapshot_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)
    rfm = df.groupby('customer_unique_id').agg(
        last_purchase=('order_purchase_timestamp', 'max'),
        frequency=('order_id', 'nunique'),
        monetary=('payment_value', 'sum'),
    )
    rfm['recency'] = (snapshot_date - rfm['last_purchase']).dt.days
    rfm = rfm.drop(columns=['last_purchase'])

    rfm['r_score'] = pd.qcut(rfm['recency'], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['m_score'] = pd.qcut(rfm['monetary'], q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['rfm_score'] = rfm['r_score'] + rfm['f_score'] + rfm['m_score']

    def label(score):
        if score >= 13:
            return 'Champion'
        elif score >= 10:
            return 'Loyal'
        elif score >= 7:
            return 'At Risk'
        return 'Lost'

    rfm['segment'] = rfm['rfm_score'].apply(label)

    segment_summary = (rfm.groupby('segment')
                       .agg(customers=('recency', 'count'),
                            avg_recency=('recency', 'mean'),
                            avg_frequency=('frequency', 'mean'),
                            avg_monetary=('monetary', 'mean'))
                       .reset_index())
    for c in ['avg_recency', 'avg_frequency', 'avg_monetary']:
        segment_summary[c] = segment_summary[c].round(2)
    segment_summary.to_csv(OUT_DIR / 'rfm_segments.csv', index=False)
    print(f"rfm_segments.csv: {segment_summary.shape}")


def main():
    df, orders, items, products, translation = load()
    export_kpi_summary(df)
    export_monthly_revenue(df)
    export_revenue_by_state(df)
    export_payment_methods(df)
    export_order_status(orders)
    export_top_categories(items, products, translation)
    export_delivery_performance(orders)
    export_rfm_segments(df)
    print(f"\nAll exports written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
