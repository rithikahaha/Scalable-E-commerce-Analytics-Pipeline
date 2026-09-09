# Project Summary

Detailed methodology and findings behind the [Scalable E-Commerce Analytics Pipeline](../README.md). See the root README for the high-level pitch, tech stack, and visuals — this doc goes one level deeper into how each analysis was built and what it found.

---

## Dataset

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 99,441 orders placed between September 2016 and October 2018 across multiple Brazilian marketplaces. Downloaded via the Kaggle API into `data/raw/`. Different parts of the pipeline join different subsets of the 8 relational tables:

| Dataset | Used by |
|---|---|
| `olist_orders_dataset.csv` | All scripts — order-level grain, timestamps, delivery dates |
| `olist_order_payments_dataset.csv` | All scripts — payment type and value per order |
| `olist_customers_dataset.csv` | All scripts — customer identity and geography (state) |
| `olist_order_reviews_dataset.csv` | All scripts — review scores |
| `olist_order_items_dataset.csv` | `ml_models.py`, `power_bi_exports.py` — price, freight, item count |
| `olist_products_dataset.csv` | `ml_models.py`, `power_bi_exports.py` — weight/dimensions, category |
| `product_category_name_translation.csv` | `power_bi_exports.py` — English category names |

## Verified Metrics (from a real run against the full dataset)

| Metric | Value |
|---|---|
| Total Revenue | R$16,081,420.74 |
| Total Orders | 99,440 |
| Total Customers (unique) | 96,095 |
| Avg Order Value | R$161.72 |
| Repeat Customer Rate | **3.12%** |
| Avg Delivery Time | 12.09 days |
| On-Time Delivery Rate | 91.89% |
| Top State by Revenue | São Paulo (R$6.03M, 37.5% of total) |
| Top Category by Revenue | Health & Beauty (R$1.26M) |
| Credit Card Share of Transactions | 73.9% |

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

## Machine Learning Models

`ml_models.py` builds an order-item-level feature table (orders + items + products + payments + reviews) and trains three models. Outputs land in [`ml_models/`](../ml_models/); full metrics in [`ml_models/MODEL_SUMMARY_REPORT.txt`](../ml_models/MODEL_SUMMARY_REPORT.txt).

| Model | Technique | Result |
|---|---|---|
| Delivery delay prediction | Random Forest Classifier (balanced class weights) | Accuracy 78.2%, ROC-AUC 0.737, Recall 53.7% |
| Review score prediction | Random Forest Regressor | R²=0.216, RMSE=1.14 stars |
| Customer segmentation | K-Means (k=4) on scaled RFM | Silhouette score 0.497 |

The delivery model is deliberately trained with `class_weight='balanced'` rather than tuned for raw accuracy, because only ~8% of orders arrive late — an unweighted model can hit ~92% accuracy just by always predicting "on time," which looks impressive but is useless for actually flagging at-risk orders. The balanced version trades some precision for meaningfully better recall on the minority (late) class, which is the class that actually matters operationally.

## Interactive Dashboard & Power BI

- `dashboard.py` builds a self-contained interactive HTML dashboard at [`dashboard/index.html`](../dashboard/index.html) (Plotly — hoverable KPIs, revenue trend, state breakdown, payment mix). Open it directly in a browser, no server required.
- `power_bi_exports.py` writes 8 pre-aggregated CSVs to [`power_bi/exports/`](../power_bi/exports/) for building an actual Power BI dashboard. See [`POWERBI_GUIDE.md`](POWERBI_GUIDE.md) for the walkthrough.

## Key Findings

- **Payment mix:** 73.9% of transactions use credit card, making gateway reliability for that method the single highest-leverage payment infrastructure investment.
- **Revenue concentration:** São Paulo alone accounts for 37.5% of total revenue (R$6.03M) — geographic concentration consistent with population and marketplace density.
- **Satisfaction ≠ loyalty:** the correlation between review score and repeat-purchase count is weak (r≈0.038 in the full-dataset run), meaning a satisfied customer is not reliably a repeat one.
- **Repeat purchases are rare, not just declining.** This is the most important — and least expected — finding in the dataset: only **3.12%** of customers place more than one order. The cohort retention matrix isn't showing a gradual month-over-month drop-off so much as a near-vertical cliff — almost every cohort's retention reads 0% by month 1. That reframes what "retention strategy" even means here: this isn't a subscription-style funnel where you're fighting gradual churn, it's a marketplace of largely one-time buyers, likely because Olist aggregates many independent sellers rather than being a single brand people return to. A retention strategy for this business would need to focus on *converting first-time buyers into second-time buyers at all*, not on slowing decay across months.
- **RFM "Champion" premium is real, but more modest than a marketing headline would suggest.** The quintile-RFM Champion segment (8,215 customers) averages R$344.76 in lifetime spend vs. an overall customer average of R$167.35 — about **2.1x**, not the "4x" figure that circulated in earlier drafts of this project's narrative. The K-Means-clustered "Champions" (a smaller, stricter cluster of 2,416 genuinely high-value customers) average R$1,161 — nearly **7x** the overall average. Which multiple is "correct" depends entirely on how tightly you define the segment; both are reported here rather than picking whichever sounds better.
- **Recency over total spend:** ordering customers by recency score alone surfaces high-value-but-inactive spenders that a total-spend ranking would overrate — recency is the more actionable signal for outreach timing.
- **Delivery lateness is the single strongest predictor of review score** (`is_late` is the top feature in the review model by a wide margin), stronger than price or freight cost — operationally, fixing delivery reliability likely does more for satisfaction than anything else in this dataset.

## Limitations

- Segmentation thresholds (quartiles for CLV, quintiles for RFM) are statistical bins recomputed on each run, not fixed business rules — they will shift if the underlying data changes.
- The satisfaction/loyalty correlation is only computed for customers with 2+ orders (a small minority, per the finding above), so it says relatively little about the broader customer base.
- The delivery delay model's precision (~19%) is low — it over-flags orders as "late" in exchange for catching more of the true late deliveries (recall 53.7%). Whether that trade-off is worth it depends on the cost of a false alarm vs. a missed late delivery in a real operational setting.
- ML models are trained on delivered orders only (order status filtering drops undelivered/canceled orders), so they say nothing about predicting non-delivery outcomes.
