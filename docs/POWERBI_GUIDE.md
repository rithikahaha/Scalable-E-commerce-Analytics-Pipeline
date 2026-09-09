# Power BI Dashboard Guide

This repo can't ship a working `.pbix` file directly (Power BI Desktop isn't something the pipeline can run headlessly), but [`power_bi_exports.py`](../power_bi_exports.py) produces clean, pre-aggregated CSVs in [`power_bi/exports/`](../power_bi/exports/) that are ready to drop straight into Power BI Desktop. This guide walks through building the dashboard from them.

## 1. Generate the exports

```bash
python power_bi_exports.py
```

This writes 8 CSVs to `power_bi/exports/`:

| File | Grain | Use for |
|---|---|---|
| `kpi_summary.csv` | 1 row | Executive KPI cards |
| `monthly_revenue.csv` | 1 row / month | Revenue trend line chart |
| `revenue_by_state.csv` | 1 row / state | Geographic bar chart / map |
| `payment_methods.csv` | 1 row / payment type | Payment mix pie/bar chart |
| `order_status.csv` | 1 row / status | Order fulfillment funnel |
| `top_categories.csv` | 1 row / category (top 20) | Product category ranking |
| `delivery_performance.csv` | 1 row | Delivery KPI cards |
| `rfm_segments.csv` | 1 row / segment | Customer segmentation chart |

Each is a flat, already-aggregated table — no relationships need to be modeled between them in Power BI; treat each as an independent visual's data source.

## 2. Import into Power BI Desktop

1. Open Power BI Desktop → **Get Data** → **Text/CSV**.
2. Import all 8 files from `power_bi/exports/`.
3. Power BI will auto-detect types; double-check `total_revenue`, `revenue`, `avg_order_value` etc. are typed as **Decimal Number**, not text.
4. Skip "Manage Relationships" — these tables are independent aggregates, not a star schema, so no relationships are needed.

## 3. Suggested report pages

**Page 1 — Executive Overview**
- KPI cards from `kpi_summary.csv`: Total Revenue, Total Orders, Total Customers, Avg Order Value
- KPI cards from `delivery_performance.csv`: Avg Delivery Days, On-Time Rate
- Line chart: `monthly_revenue.csv` (`order_month` on X, `revenue` on Y)

**Page 2 — Geography**
- Bar chart or filled map: `revenue_by_state.csv` (`customer_state`, `revenue`)
- Secondary bar: `customers` by state

**Page 3 — Payments & Orders**
- Donut chart: `payment_methods.csv` (`payment_type`, `orders`)
- Bar chart: `order_status.csv` (`order_status`, `order_count`)

**Page 4 — Products**
- Horizontal bar: `top_categories.csv` (`category`, `revenue`), sorted descending
- Scatter: `avg_price` vs `orders` per category

**Page 5 — Customer Segments**
- Bar or treemap: `rfm_segments.csv` (`segment`, `customers`)
- Table: segment averages (`avg_recency`, `avg_frequency`, `avg_monetary`)

## 4. Save

Save the finished dashboard as `power_bi/olist_dashboard.pbix` — that path is already referenced from the README once you've built it, so the repo structure matches without further edits.

## 5. If the underlying data changes

Re-run `python power_bi_exports.py`, then in Power BI: **Home → Refresh**. Since the exports are always written to the same 8 filenames, existing visuals will pick up the new data without needing to be rebuilt.
