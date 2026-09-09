"""
Builds a single self-contained interactive HTML dashboard (Plotly) covering
executive KPIs, revenue, payments, geography, and RFM segments.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

DATA_DIR = Path('data/raw')
OUT_DIR = Path('dashboard')
OUT_DIR.mkdir(exist_ok=True)


def load_and_merge():
    orders = pd.read_csv(DATA_DIR / 'olist_orders_dataset.csv')
    payments = pd.read_csv(DATA_DIR / 'olist_order_payments_dataset.csv')
    customers = pd.read_csv(DATA_DIR / 'olist_customers_dataset.csv')
    reviews = pd.read_csv(DATA_DIR / 'olist_order_reviews_dataset.csv')

    orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'])
    orders['order_month'] = orders['order_purchase_timestamp'].dt.to_period('M').astype(str)

    df = (orders
          .merge(payments, on='order_id', how='inner')
          .merge(customers, on='customer_id', how='inner')
          .merge(reviews[['order_id', 'review_score']], on='order_id', how='left'))
    return df, orders


def build_dashboard(df, orders):
    total_revenue = df['payment_value'].sum()
    total_orders = df['order_id'].nunique()
    total_customers = df['customer_unique_id'].nunique()
    avg_order_value = total_revenue / total_orders
    on_time_rate = (orders['order_status'] == 'delivered').mean() * 100

    revenue_by_month = df.groupby('order_month')['payment_value'].sum().sort_index()

    revenue_by_state = (df.groupby('customer_state')['payment_value']
                         .sum().sort_values(ascending=False).head(10))

    payment_dist = df['payment_type'].value_counts()

    order_status = orders['order_status'].value_counts()

    review_dist = df['review_score'].dropna().value_counts().sort_index()

    fig = make_subplots(
        rows=3, cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "scatter", "colspan": 2}, None],
            [{"type": "bar"}, {"type": "pie"}],
        ],
        row_heights=[0.18, 0.4, 0.42],
        subplot_titles=("", "", "Monthly Revenue Trend",
                         "Top 10 States by Revenue", "Payment Method Distribution"),
        vertical_spacing=0.09,
    )

    fig.add_trace(go.Indicator(
        mode="number", value=total_revenue,
        number={'prefix': "R$", 'valueformat': ',.0f'},
        title={"text": "Total Revenue"},
    ), row=1, col=1)

    fig.add_trace(go.Indicator(
        mode="number", value=total_orders,
        number={'valueformat': ',.0f'},
        title={"text": "Total Orders"},
    ), row=1, col=2)

    fig.add_trace(go.Scatter(
        x=revenue_by_month.index, y=revenue_by_month.values,
        mode='lines+markers', line=dict(color='#4C78A8', width=3),
        name='Revenue',
    ), row=2, col=1)

    fig.add_trace(go.Bar(
        x=revenue_by_state.index, y=revenue_by_state.values,
        marker_color='#72B7B2', name='Revenue by State',
    ), row=3, col=1)

    fig.add_trace(go.Pie(
        labels=payment_dist.index, values=payment_dist.values,
        hole=0.45, marker=dict(colors=['#4C78A8', '#F58518', '#54A24B', '#E45756']),
    ), row=3, col=2)

    fig.update_layout(
        title=dict(text="Olist E-Commerce — Executive Dashboard", x=0.5, font=dict(size=22)),
        height=950, showlegend=False,
        template='plotly_white',
        margin=dict(t=90, b=40, l=40, r=40),
    )
    fig.update_yaxes(title_text="Revenue (BRL)", row=2, col=1)
    fig.update_yaxes(title_text="Revenue (BRL)", row=3, col=1)

    extra_stats = (
        f"Customers: {total_customers:,} &nbsp;|&nbsp; "
        f"Avg Order Value: R${avg_order_value:,.2f} &nbsp;|&nbsp; "
        f"Delivered Rate: {on_time_rate:.1f}%"
    )

    html_path = OUT_DIR / 'index.html'
    fig.write_html(html_path, include_plotlyjs='cdn', full_html=True)

    # Inject a small stats strip under the title
    html = html_path.read_text(encoding='utf-8')
    marker = '<body>'
    banner = (
        f'<body><div style="text-align:center;font-family:sans-serif;'
        f'padding:10px;color:#555;">{extra_stats}</div>'
    )
    html = html.replace(marker, banner, 1)
    html_path.write_text(html, encoding='utf-8')

    print(f"Dashboard written to {html_path}")
    print(f"Total Revenue: BRL {total_revenue:,.2f}")
    print(f"Total Orders: {total_orders:,}")
    print(f"Total Customers: {total_customers:,}")
    print(f"Avg Order Value: BRL {avg_order_value:,.2f}")


def main():
    df, orders = load_and_merge()
    build_dashboard(df, orders)


if __name__ == "__main__":
    main()
