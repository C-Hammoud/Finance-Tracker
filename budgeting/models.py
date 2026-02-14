"""
Budgeting Application — Data model per BRD.
Entities: Transaction, Category, Group, Budget, Savings, Commitment, FinancialStanding, reference LOVs.
"""
from django.db import models
from django.conf import settings
from decimal import Decimal


class Group(models.Model):
    """Category group (e.g. Home, Food, Transportation)."""
    name = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    """Category belonging to a Group; include_in_reports controls reporting."""
    name = models.CharField(max_length=80)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="categories")
    include_in_reports = models.BooleanField(
        default=True,
        help_text="Include in expense totals and budget reports",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["group", "order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.group.name} — {self.name}"


class Classification(models.TextChoices):
    FIXED = "fixed", "Fixed"
    VARIABLE = "variable", "Variable"


class AccountType(models.TextChoices):
    BANK = "bank", "Bank"
    CREDIT_CARD = "credit_card", "Credit Card"
    WALLET = "wallet", "Wallet"
    OTHER = "other", "Other"


class Direction(models.TextChoices):
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"
    TRANSFER = "transfer", "Transfer"


class Frequency(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    YEARLY = "yearly", "Yearly"


class Transaction(models.Model):
    """
    Bank/credit transaction: date, description, category, amount, direction.
    Transfers are excluded from expense totals.
    """
    date = models.DateField()
    month = models.CharField(max_length=7, db_index=True)  # YYYY-MM
    description = models.CharField(max_length=500)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    classification = models.CharField(
        max_length=20,
        choices=Classification.choices,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    direction = models.CharField(max_length=20, choices=Direction.choices)
    source_account = models.CharField(max_length=100, blank=True)
    external_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Bank transaction id for deduplication",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgeting_transactions",
    )

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["user", "month"]),
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"{self.date} {self.description[:40]} {self.amount} {self.direction}"


class MerchantCategoryLink(models.Model):
    """Keyword → Category mapping for automatic transaction classification."""
    keyword = models.CharField(max_length=120, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="merchant_links")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgeting_merchant_links",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["keyword"]
        unique_together = [["keyword", "category"]]

    def __str__(self):
        return f"{self.keyword} → {self.category.name}"


class Budget(models.Model):
    """Forecast amount per category per month/year."""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()  # 1–12
    forecast = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgeting_budgets",
    )

    class Meta:
        ordering = ["year", "month", "category"]
        unique_together = [["user", "category", "year", "month"]]

    def __str__(self):
        return f"{self.category.name} {self.year}-{self.month:02d} = {self.forecast}"


class GoalStatus(models.TextChoices):
    MET = "met", "Met"
    MISSED = "missed", "Missed"
    PENDING = "pending", "Pending"


class Savings(models.Model):
    """Monthly saving: actual (derived or manual), target, goal status."""
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    actual = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual savings (income - expenses - commitments)",
    )
    target = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    goal_status = models.CharField(
        max_length=20,
        choices=GoalStatus.choices,
        default=GoalStatus.PENDING,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgeting_savings",
    )

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = [["user", "year", "month"]]

    def __str__(self):
        return f"{self.year}-{self.month:02d} target={self.target} actual={self.actual} ({self.goal_status})"


class Commitment(models.Model):
    """Loan/commitment: amount, start, term, frequency, payment, balloon."""
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    start_date = models.DateField()
    term_months = models.PositiveIntegerField(help_text="Term in months")
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.MONTHLY)
    payment_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    balloon = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Balloon payment at end if any",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgeting_commitments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.name} — {self.amount}"


class CommitmentScheduleLine(models.Model):
    """Single line in a loan schedule: due date, amount, status."""
    class ScheduleStatus(models.TextChoices):
        PAID = "paid", "Paid"
        OUTSTANDING = "outstanding", "Outstanding"

    commitment = models.ForeignKey(
        Commitment,
        on_delete=models.CASCADE,
        related_name="schedule_lines",
    )
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=ScheduleStatus.choices,
        default=ScheduleStatus.OUTSTANDING,
    )
    sequence = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["commitment", "due_date"]

    def __str__(self):
        return f"{self.commitment.name} {self.due_date} {self.amount} ({self.status})"


class FinancialStanding(models.Model):
    """Snapshot of assets and liabilities."""
    snapshot_date = models.DateField()
    total_assets = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    current_assets = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    fixed_assets = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_liabilities = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    short_term_liabilities = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    long_term_liabilities = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    notes = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgeting_financial_standings",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-snapshot_date"]

    def __str__(self):
        return f"Standing {self.snapshot_date} A={self.total_assets} L={self.total_liabilities}"


class UploadTemplate(models.Model):
    """Saved column mapping for CSV/XLS bank statement import."""
    name = models.CharField(max_length=100)
    column_mapping = models.JSONField(
        default=dict,
        help_text="e.g. {\"date\": \"A\", \"description\": \"B\", \"amount\": \"C\"}",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgeting_upload_templates",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
