"""
Olist E-Commerce Customer Analytics
Analyzes customer behavior, revenue patterns, and retention metrics
from Brazilian e-commerce marketplace data
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Set visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 100

# All generated charts are written here
VIZ_DIR = Path('visualizations')
VIZ_DIR.mkdir(exist_ok=True)


def load_data():
    """Load all required datasets and perform initial validation"""
    data_files = {
        'orders': 'olist_orders_dataset.csv',
        'payments': 'olist_order_payments_dataset.csv',
        'customers': 'olist_customers_dataset.csv',
        'reviews': 'olist_order_reviews_dataset.csv'
    }
    
    datasets = {}
    for key, filename in data_files.items():
        datasets[key] = pd.read_csv(filename)
        print(f"Loaded {filename}: {datasets[key].shape[0]:,} rows")
    
    return datasets


def build_analytical_dataset(datasets):
    """
    Merge all datasets into single analytical table.
    Left join on reviews since not all orders have reviews.
    """
    df = (datasets['orders']
          .merge(datasets['payments'], on='order_id', how='inner')
          .merge(datasets['customers'], on='customer_id', how='inner')
          .merge(datasets['reviews'][['order_id', 'review_score']], 
                 on='order_id', how='left'))
    
    # Convert timestamps
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    df['order_month'] = df['order_purchase_timestamp'].dt.to_period('M')
    
    print(f"\nMerged dataset: {df.shape[0]:,} records, {df.shape[1]} columns")
    return df


def analyze_revenue_trends(df):
    """Monthly revenue aggregation and visualization"""
    revenue_by_month = (df.groupby('order_month')['payment_value']
                        .sum()
                        .sort_index())
    
    fig, ax = plt.subplots(figsize=(12, 6))
    revenue_by_month.plot(ax=ax, marker='o', linewidth=2, markersize=6)
    ax.set_title('Monthly Revenue Trend', fontsize=14, fontweight='bold')
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Revenue (BRL)', fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(VIZ_DIR / 'monthly_revenue.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return revenue_by_month


def segment_customers_by_value(df):
    """
    Calculate customer lifetime value and identify segments.
    Using total spend as proxy for CLV.
    """
    clv = (df.groupby('customer_unique_id')
           .agg({
               'payment_value': 'sum',
               'order_id': 'count'
           })
           .rename(columns={'payment_value': 'total_spent', 
                           'order_id': 'order_count'}))
    
    # Define value segments using quartiles
    clv['value_segment'] = pd.qcut(clv['total_spent'], 
                                     q=4, 
                                     labels=['Low', 'Medium', 'High', 'VIP'])
    
    print("\nCustomer Value Segments:")
    print(clv.groupby('value_segment')['total_spent'].describe())
    
    # Visualize distribution
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    axes[0].hist(clv['total_spent'], bins=50, edgecolor='black', alpha=0.7)
    axes[0].set_xlabel('Total Spend (BRL)')
    axes[0].set_ylabel('Number of Customers')
    axes[0].set_title('Customer Lifetime Value Distribution')
    axes[0].axvline(clv['total_spent'].median(), color='red', 
                    linestyle='--', label=f'Median: {clv["total_spent"].median():.2f}')
    axes[0].legend()
    
    segment_counts = clv['value_segment'].value_counts().sort_index()
    axes[1].bar(segment_counts.index, segment_counts.values, 
                color=['#d3d3d3', '#90ee90', '#ffd700', '#ff6347'])
    axes[1].set_xlabel('Customer Segment')
    axes[1].set_ylabel('Count')
    axes[1].set_title('Customer Segmentation')
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / 'customer_segments.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return clv


def analyze_payment_methods(df):
    """Payment type distribution analysis"""
    payment_dist = df['payment_type'].value_counts()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = sns.color_palette('Set2', len(payment_dist))
    payment_dist.plot(kind='bar', ax=ax, color=colors, edgecolor='black')
    ax.set_title('Payment Method Distribution', fontsize=14, fontweight='bold')
    ax.set_xlabel('Payment Type')
    ax.set_ylabel('Transaction Count')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    
    # Add percentage labels
    total = payment_dist.sum()
    for i, v in enumerate(payment_dist):
        ax.text(i, v + total*0.01, f'{v/total*100:.1f}%', 
                ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / 'payment_methods.png', dpi=300, bbox_inches='tight')
    plt.show()


def geographic_analysis(df):
    """Revenue breakdown by state"""
    state_metrics = (df.groupby('customer_state')
                     .agg({
                         'payment_value': 'sum',
                         'customer_unique_id': 'nunique'
                     })
                     .rename(columns={'payment_value': 'total_revenue',
                                     'customer_unique_id': 'unique_customers'})
                     .sort_values('total_revenue', ascending=False))
    
    top_states = state_metrics.head(10)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(top_states))
    width = 0.35
    
    ax.bar(x - width/2, top_states['total_revenue']/1000, width, 
           label='Revenue (K BRL)', color='steelblue')
    ax2 = ax.twinx()
    ax2.bar(x + width/2, top_states['unique_customers'], width, 
            label='Customers', color='coral', alpha=0.7)
    
    ax.set_xlabel('State')
    ax.set_ylabel('Revenue (Thousands BRL)', color='steelblue')
    ax2.set_ylabel('Number of Customers', color='coral')
    ax.set_title('Top 10 States: Revenue & Customer Base')
    ax.set_xticks(x)
    ax.set_xticklabels(top_states.index, rotation=45, ha='right')
    
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / 'geographic_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return state_metrics


def satisfaction_vs_repeat_purchase(df):
    """
    Examine relationship between customer satisfaction (review scores)
    and repeat purchase behavior
    """
    customer_metrics = (df.groupby('customer_unique_id')
                        .agg({
                            'review_score': 'mean',
                            'order_id': 'nunique'
                        })
                        .rename(columns={'order_id': 'num_orders'})
                        .dropna())
    
    # Only customers with 2+ orders for meaningful analysis
    repeat_customers = customer_metrics[customer_metrics['num_orders'] > 1]
    
    correlation = repeat_customers['review_score'].corr(repeat_customers['num_orders'])
    print(f"\nCorrelation (satisfaction vs repeat purchase): {correlation:.3f}")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(repeat_customers['review_score'], 
                        repeat_customers['num_orders'],
                        alpha=0.5, s=30, c=repeat_customers['num_orders'],
                        cmap='viridis')
    ax.set_xlabel('Average Review Score')
    ax.set_ylabel('Number of Orders')
    ax.set_title(f'Customer Satisfaction vs Repeat Purchases (r={correlation:.3f})')
    plt.colorbar(scatter, ax=ax, label='Order Count')
    plt.tight_layout()
    plt.savefig(VIZ_DIR / 'satisfaction_correlation.png', dpi=300, bbox_inches='tight')
    plt.show()


def cohort_retention_analysis(df):
    """
    Build cohort analysis based on first purchase month.
    Track how many customers from each cohort return in subsequent months.
    """
    # Get each customer's first purchase month
    customer_cohorts = (df.groupby('customer_unique_id')['order_month']
                        .min()
                        .reset_index()
                        .rename(columns={'order_month': 'cohort'}))
    
    # Merge back to main dataframe
    df_cohort = df.merge(customer_cohorts, on='customer_unique_id')
    
    # Calculate period number (months since first purchase)
    df_cohort['period'] = (df_cohort['order_month'].astype(int) - 
                           df_cohort['cohort'].astype(int))
    
    # Build cohort matrix
    cohort_data = (df_cohort.groupby(['cohort', 'period'])
                   ['customer_unique_id']
                   .nunique()
                   .reset_index())
    
    cohort_pivot = cohort_data.pivot(index='cohort', 
                                     columns='period', 
                                     values='customer_unique_id')
    
    # Calculate retention rates
    cohort_sizes = cohort_pivot.iloc[:, 0]
    retention_rates = cohort_pivot.div(cohort_sizes, axis=0) * 100
    
    # Visualization
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(retention_rates, 
                annot=True, 
                fmt='.0f',
                cmap='RdYlGn',
                vmin=0,
                vmax=100,
                cbar_kws={'label': 'Retention Rate (%)'},
                linewidths=0.5,
                ax=ax)
    
    ax.set_title('Cohort Retention Analysis', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Months Since First Purchase', fontsize=12)
    ax.set_ylabel('Cohort (First Purchase Month)', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / 'cohort_retention.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("\nRetention Matrix (first 6 cohorts, first 6 months):")
    print(retention_rates.iloc[:6, :6])
    
    return retention_rates


def rfm_analysis(df):
    """
    RFM (Recency, Frequency, Monetary) segmentation.
    Scores each customer 1-5 on each dimension.
    - Recency: how recently did they buy? (lower days = better = higher score)
    - Frequency: how many orders did they make? (higher = better)
    - Monetary: how much did they spend in total? (higher = better)
    """
    # Set snapshot date as one day after last order
    # (so recency is meaningful relative to the dataset, not today's date)
    snapshot_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

    # Calculate R, F, M for each customer
    rfm = df.groupby('customer_unique_id').agg({
        'order_purchase_timestamp': 'max',
        'order_id': 'count',
        'payment_value': 'sum'
    }).rename(columns={
        'order_purchase_timestamp': 'last_purchase',
        'order_id': 'frequency',
        'payment_value': 'monetary'
    })

    # Recency = days since last purchase
    rfm['recency'] = (snapshot_date - rfm['last_purchase']).dt.days
    rfm.drop(columns=['last_purchase'], inplace=True)

    # Score each metric 1-5
    # Recency is reversed: fewer days = score 5 (better)
    # Frequency and Monetary: higher = score 5 (better)
    rfm['r_score'] = pd.qcut(rfm['recency'], q=5, labels=[5, 4, 3, 2, 1])
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5])
    rfm['m_score'] = pd.qcut(rfm['monetary'], q=5, labels=[1, 2, 3, 4, 5])

    # Combined RFM score (max 15)
    rfm['rfm_score'] = (rfm['r_score'].astype(int) +
                        rfm['f_score'].astype(int) +
                        rfm['m_score'].astype(int))

    # Segment labels based on combined score
    def label_segment(score):
        if score >= 13:
            return 'Champion'
        elif score >= 10:
            return 'Loyal'
        elif score >= 7:
            return 'At Risk'
        else:
            return 'Lost'

    rfm['segment'] = rfm['rfm_score'].apply(label_segment)

    print("\nRFM Segments:")
    print(rfm['segment'].value_counts())
    print(f"\nAverage RFM metrics by segment:")
    print(rfm.groupby('segment')[['recency', 'frequency', 'monetary']].mean().round(2))

    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Segment distribution
    segment_counts = rfm['segment'].value_counts()
    colors = ['#4169e1', '#90ee90', '#ffd700', '#ff6347']
    axes[0].bar(segment_counts.index, segment_counts.values,
                color=colors, edgecolor='black')
    axes[0].set_title('RFM Customer Segments', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Segment')
    axes[0].set_ylabel('Number of Customers')
    for i, v in enumerate(segment_counts.values):
        axes[0].text(i, v + 50, str(v), ha='center', fontweight='bold')

    # Average monetary value by segment
    avg_monetary = rfm.groupby('segment')['monetary'].mean().sort_values(ascending=False)
    axes[1].bar(avg_monetary.index, avg_monetary.values,
                color=colors, edgecolor='black')
    axes[1].set_title('Average Spend by Segment', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Segment')
    axes[1].set_ylabel('Average Spend (BRL)')
    for i, v in enumerate(avg_monetary.values):
        axes[1].text(i, v + 10, f'{v:.0f}', ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(VIZ_DIR / 'rfm_segments.png', dpi=300, bbox_inches='tight')
    plt.show()

    return rfm


def main():
    """Execute full analysis pipeline"""
    print("="*60)
    print("OLIST E-COMMERCE ANALYTICS PIPELINE")
    print("="*60)
    
    # Load data
    datasets = load_data()
    
    # Build analytical dataset
    df = build_analytical_dataset(datasets)
    
    # Run analyses
    print("\n[1/7] Revenue trend analysis...")
    revenue_trends = analyze_revenue_trends(df)
    
    print("\n[2/7] Customer segmentation...")
    customer_segments = segment_customers_by_value(df)
    
    print("\n[3/7] Payment method analysis...")
    analyze_payment_methods(df)
    
    print("\n[4/7] Geographic revenue distribution...")
    geo_metrics = geographic_analysis(df)
    
    print("\n[5/7] Satisfaction correlation...")
    satisfaction_vs_repeat_purchase(df)
    
    print("\n[6/7] Cohort retention analysis...")
    retention = cohort_retention_analysis(df)

    print("\n[7/7] RFM segmentation...")
    rfm = rfm_analysis(df)
    
    print("\n[8/8] Analysis complete!")
    print(f"\nGenerated visualizations (in {VIZ_DIR}/):")
    print("  - monthly_revenue.png")
    print("  - customer_segments.png")
    print("  - payment_methods.png")
    print("  - geographic_analysis.png")
    print("  - satisfaction_correlation.png")
    print("  - cohort_retention.png")
    print("  - rfm_segments.png")
    
    print("\n" + "="*60)
    print("Pipeline finished successfully")
    print("="*60)

    total_revenue = df['payment_value'].sum()
    total_orders = df['order_id'].nunique()
    repeat_rate = (df.groupby('customer_unique_id')['order_id']
               .nunique()
               .gt(1)
               .mean() * 100)

    print("\nEXECUTIVE SUMMARY")
    print("-"*40)
    print(f"Total Revenue: BRL {total_revenue:,.2f}")
    print(f"Total Orders: {total_orders:,}")
    print(f"Repeat Customer Rate: {repeat_rate:.2f}%")


if __name__ == "__main__":
    main()
