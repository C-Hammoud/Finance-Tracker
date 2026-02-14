"""
Business logic for budgeting: actuals from transactions (Firestore), variance, auto-categorization.
All data is read from Firestore; no Django ORM.
"""
from decimal import Decimal
from datetime import date

from .firestore_models import (
    GroupFS,
    CategoryFS,
    TransactionFS,
    MerchantCategoryLinkFS,
    CommitmentScheduleLineFS,
    CommitmentFS,
)


def get_month_str(d):
    """Return YYYY-MM for a date."""
    return d.strftime("%Y-%m")


def _user_id(user):
    return str(user.pk) if hasattr(user, "pk") else str(user)


def actual_expense_by_category(user, year, month):
    """
    Sum of transaction amounts (expense direction) per category for a month.
    Returns dict category_id -> total amount. Uses Firestore data.
    """
    month_str = f"{year}-{month:02d}"
    txns = TransactionFS.list_by_user(_user_id(user), month=month_str)
    result = {}
    for t in txns:
        if t.direction != "expense":
            continue
        cid = t.category_id or "_none_"
        result[cid] = result.get(cid, Decimal("0")) + t.amount
    return result


def actual_income_total(user, year, month):
    """Total income for a month (exclude transfers). Firestore."""
    month_str = f"{year}-{month:02d}"
    txns = TransactionFS.list_by_user(_user_id(user), month=month_str)
    return sum((t.amount for t in txns if t.direction == "income"), Decimal("0"))


def actual_expense_total(user, year, month):
    """Total expenses for a month (exclude transfers). Firestore."""
    month_str = f"{year}-{month:02d}"
    txns = TransactionFS.list_by_user(_user_id(user), month=month_str)
    return sum((t.amount for t in txns if t.direction == "expense"), Decimal("0"))


def commitment_payments_total(user, year, month):
    """Total commitment payments due in a month. Firestore."""
    return CommitmentScheduleLineFS.sum_amount_due_in_month(_user_id(user), year, month)


def savings_actual(user, year, month):
    """Actual savings = income - expenses - commitment payments (for the month)."""
    inc = actual_income_total(user, year, month)
    exp = actual_expense_total(user, year, month)
    comm = commitment_payments_total(user, year, month)
    return inc - exp - comm


def budget_variance(actual, forecast):
    """Variance = actual - forecast (positive = overspend)."""
    a = actual or Decimal("0")
    f = forecast or Decimal("0")
    return a - f


def utilization_pct(actual, forecast):
    """Utilization % = (actual / forecast) * 100 if forecast else None."""
    a = actual or Decimal("0")
    f = forecast or Decimal("0")
    if f and f != 0:
        return (a / f * 100).quantize(Decimal("0.1"))
    return None


def suggest_category_for_description(description, user=None):
    """
    Suggest category from MerchantCategoryLink (Firestore) by keyword match (case-insensitive).
    Returns CategoryFS or None. user optional: if set, prefer user-specific links.
    """
    if not description:
        return None
    desc_lower = description.lower()
    uid = _user_id(user) if user else None
    # User-specific first
    if uid:
        links = MerchantCategoryLinkFS.list_by_user(uid)
        for link in links:
            if link.keyword.lower() in desc_lower:
                return CategoryFS.get(link.category_id)
    # Global (user_id null) - list all and filter
    all_links = MerchantCategoryLinkFS.list_all(limit=1000)
    for link in all_links:
        if link.user_id:
            continue
        if link.keyword.lower() in desc_lower:
            return CategoryFS.get(link.category_id)
    return None


def remaining_principal(commitment_fs):
    """Sum of outstanding schedule line amounts for a CommitmentFS."""
    return CommitmentScheduleLineFS.sum_outstanding_by_commitment(commitment_fs.pk)


def categories_and_groups_for_user():
    """
    Load all GroupFS and CategoryFS from Firestore; return (groups_list, categories_by_id).
    categories_by_id[category_id] = CategoryFS (with group_id); resolve group name from groups.
    """
    groups = {g.pk: g for g in GroupFS.list_all()}
    categories = CategoryFS.list_all()
    by_id = {c.pk: c for c in categories}
    # Attach group name to each category for templates
    for c in by_id.values():
        c.group_name = groups.get(c.group_id).name if c.group_id and c.group_id in groups else ""
    return list(groups.values()), by_id
