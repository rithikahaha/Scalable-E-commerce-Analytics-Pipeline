# Project Summary

Detailed methodology and findings behind the [Scalable E-Commerce Analytics Pipeline](../README.md). See the root README for the high-level pitch, tech stack, and visuals — this doc goes one level deeper into how each analysis was built and what it found.

---

## Dataset

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — ~100k orders placed between 2016 and 2018 across multiple Brazilian marketplaces. The pipeline joins four of the eight relational tables:

| Dataset | Role in the pipeline |
|---|---|
| `olist_orders_dataset.csv` | Order-level grain; source of purchase timestamps |
| `olist_order_payments_dataset.csv` | Payment type and value per order |
| `olist_customers_dataset.csv` | Customer identity and geography (state) |
| `olist_order_reviews_dataset.csv` | Review scores, left-joined since not every order has one |

## Methodology

1. **Load** — read the four CSVs, log row counts for a quick sanity check.
2. **Integrate** — inner-join orders → payments → customers on their keys, then left-join review scores. Inner joins are used for tables required to compute revenue; a left join is used for reviews because their absence shouldn't drop an otherwise valid order.
3. **Derive** — cast `order_purchase_timestamp` to a proper datetime and roll it up to `order_month` for time-series and cohort work.
4. **Analyze** — seven independent analyses run over the merged dataset (see below), each producing one chart in [`visualizations/`](../visualizations/).

## Analyses

| # | Analysis | Technique | Output |
|---|---|---|---|
| 1 | Revenue trend | Monthly `groupby().sum()` on `payment_value` | `monthly_revenue.png` |
| 2 | Customer value segmentation | Quartile binning (`pd.qcut`) of total spend per customer into Low/Medium/High/VIP | `customer_segments.png` |
| 3 | Payment method mix | Value counts on `payment_type` | `payment_methods.png` |
| 4 | Geographic distribution | Revenue and customer count grouped by `customer_state`, top 10 states | `geographic_analysis.png` |
| 5 | Satisfaction vs. loyalty | Pearson correlation between average review score and order count, for customers with 2+ orders | `satisfaction_correlation.png` |
| 6 | Cohort retention | Customers grouped by first-purchase month, tracked across subsequent months as a retention-rate matrix | `cohort_retention.png` |
| 7 | RFM segmentation | Recency/Frequency/Monetary scored 1–5 via quintile binning, summed into Champion/Loyal/At Risk/Lost segments | `rfm_segments.png` |

## Key Findings

- **Payment mix:** ~73.9% of transactions use credit card, making gateway reliability for that method the single highest-leverage payment infrastructure investment.
- **Revenue concentration:** revenue is geographically concentrated in a small number of states (São Paulo and Rio de Janeiro lead), consistent with population and marketplace density.
- **Satisfaction ≠ loyalty:** the correlation between review score and repeat-purchase count is weak (r≈0.038), meaning a satisfied customer is not reliably a repeat one — price and delivery experience likely matter more than star ratings for retention.
- **Cohort drop-off:** the longitudinal cohort matrix shows most customer attrition happens in the first 1–2 months after acquisition, which is the highest-leverage window for re-engagement campaigns.
- **RFM Pareto effect:** the "Champion" segment (highest combined RFM score) spends roughly 4x the average customer, confirming a small cohort drives a disproportionate share of revenue.
- **Recency over total spend:** ordering customers by recency score alone surfaces high-value-but-inactive spenders that a total-spend ranking would overrate — recency is the more actionable signal for outreach timing.

## Limitations

- Segmentation thresholds (quartiles for CLV, quintiles for RFM) are statistical bins recomputed on each run, not fixed business rules — they will shift if the underlying data changes.
- The satisfaction/loyalty correlation is only computed for customers with 2+ orders, so it says nothing about what drives a customer's *first* repeat purchase.
- No product-level or seller-level dimensions are joined in, so findings are limited to customer, payment, and geography.
