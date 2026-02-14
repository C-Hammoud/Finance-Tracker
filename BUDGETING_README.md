# Budgeting Application (BRD v1.0)

This module implements the **Budgeting Application** from the Business Requirements Document (Chadi M. Hammoud, Feb 10, 2026). It is a separate Django app (`budgeting`) that does **not** change any expense-tracking logic or data in the existing `expenses` app.

## Data store: Firebase (Firestore)

**All budgeting data is stored in Firestore**, not in local SQL. The app reads and writes exclusively to Firebase collections:

- `budgeting_groups` — Category groups (e.g. Home, Food)
- `budgeting_categories` — Categories with `group_id`, `include_in_reports`
- `budgeting_transactions` — Transactions (user_id, date, category_id, amount, direction, …)
- `budgeting_merchant_links` — Keyword → category_id for auto-classification
- `budgeting_budgets` — Forecast per user/category/year/month
- `budgeting_savings` — Monthly target/actual/goal_status per user
- `budgeting_commitments` — Loans; `budgeting_commitment_schedule_lines` — schedule lines
- `budgeting_financial_standings` — Assets/liabilities snapshots
- `budgeting_upload_templates` — (optional) column mappings

Django models in `budgeting.models` remain for reference and optional Admin use; **views and services use `budgeting.firestore_models` only**.

## What Was Added

### New app: `budgeting`
- **Firestore models** (`budgeting/firestore_models.py`): GroupFS, CategoryFS, TransactionFS, MerchantCategoryLinkFS, BudgetFS, SavingsFS, CommitmentFS, CommitmentScheduleLineFS, FinancialStandingFS, UploadTemplateFS — same entities as BRD §8.1, stored in Firestore.
- **Django models** (`budgeting/models.py`) kept for compatibility; not used for primary read/write.

### Features
- **Dashboard** (`/budgeting/`) — Monthly budget vs actual by category, total forecast/actual, variance, utilization %, highest expense category, top overspends; income/expense totals
- **Transactions** — List, add, edit; **CSV upload** with date/description/amount (column 0/1/2), deduplication by date+amount+description, auto-categorization from merchant links
- **Budgets** — List and edit forecast per category/month
- **Savings** — List and edit target/actual/goal status per month; actual = income − expenses − commitment payments (due in month)
- **Commitments** — List, add, edit loans; remaining principal from outstanding schedule lines
- **Financial standing** — List and add assets/liabilities snapshots
- **Config** — Categories & groups (read-only; edit in Django Admin); **Merchant links** for auto-classification

### Navigation
- **Budgeting** link added to the main navbar (in `expenses/base.html`) so users can open `/budgeting/`. No other changes were made to expense views, models, or URLs.

### URLs (all under `/budgeting/`)
| Path | Purpose |
|------|--------|
| `/budgeting/` | Dashboard |
| `/budgeting/transactions/` | Transaction list |
| `/budgeting/transactions/add/` | Add transaction |
| `/budgeting/transactions/upload/` | Upload CSV |
| `/budgeting/transactions/<id>/edit/` | Edit transaction |
| `/budgeting/budgets/` | Budget list |
| `/budgeting/budgets/<y>/<m>/<cat_id>/` | Edit budget |
| `/budgeting/savings/` | Savings list |
| `/budgeting/savings/<y>/<m>/` | Edit savings |
| `/budgeting/commitments/` | Commitments list |
| `/budgeting/commitments/add/` | Add commitment |
| `/budgeting/commitments/<id>/edit/` | Edit commitment |
| `/budgeting/financial-standing/` | Financial standing list |
| `/budgeting/financial-standing/add/` | Add snapshot |
| `/budgeting/config/categories/` | Categories & groups |
| `/budgeting/config/merchant-links/` | Merchant → category links |

## Setup

1. **Firebase**: Ensure `firebase_client.py` and your service account key (e.g. `resources/finance-tracker-firebase_key.json` or `FIREBASE_KEY_PATH`) are configured so `get_firestore_client()` works (same as the expenses app).
2. **Seed groups and categories** in Firestore (required before using budgets/transactions):
   ```bash
   python manage.py seed_firestore_budgeting
   ```
   This creates default groups (Home, Food, Transportation, etc.) and categories in Firestore.
3. **Optional:** Add **Merchant → Category** links in the app (Budgeting → Merchant links) so CSV imports auto-classify by description keyword.

## CSV import format

- **Column 0:** Date (`YYYY-MM-DD` or `DD/MM/YYYY`)
- **Column 1:** Description
- **Column 2:** Amount (negative = expense, positive = income)

Duplicates are skipped (same date + amount + description). Column mapping templates (UploadTemplate) are for future extension; current code uses fixed column positions.

## Out of scope (per BRD)

- Investment analytics, multi-currency, tax, Open Banking (Phase 2)
- No changes were made to the **expenses** app logic or data; only the shared navbar was extended with one “Budgeting” link.
