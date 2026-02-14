"""
Budgeting data in Firestore (Firebase). Primary data store for budgeting app.
Read/write via these models; no dependency on Django ORM for budgeting data.
"""
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from firebase_client import get_firestore_client


def _as_decimal(value):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0.00")


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _as_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        s = str(value)
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s[:10])
    except Exception:
        return None


class BudgetingFirestoreModel:
    collection_name: str = ""

    def __init__(self, pk: Optional[str] = None):
        self.pk = pk

    def _collection(self):
        return get_firestore_client().collection(self.collection_name)

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        raise NotImplementedError

    def save(self):
        col = self._collection()
        data = self.to_dict()
        if not self.pk:
            doc_ref = col.document()
            self.pk = doc_ref.id
            doc_ref.set(data)
        else:
            col.document(self.pk).set(data)
        return self

    def delete(self):
        if not self.pk:
            return
        self._collection().document(self.pk).delete()

    @classmethod
    def get(cls, pk: str):
        db = get_firestore_client()
        doc = db.collection(cls.collection_name).document(pk).get()
        if not doc.exists:
            return None
        return cls.from_dict(doc.id, doc.to_dict())

    @classmethod
    def list_all(cls, limit: int = 500) -> List:
        db = get_firestore_client()
        docs = db.collection(cls.collection_name).limit(limit).stream()
        return [cls.from_dict(d.id, d.to_dict()) for d in docs]

    @classmethod
    def query_by_field(cls, field_name: str, op: str, value, limit: int = 500) -> List:
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where(field_name, op, value).limit(limit)
        return [cls.from_dict(d.id, d.to_dict()) for d in q.stream()]


# --- Group (no user_id; global reference) ---
@dataclass
class GroupFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_groups")
    pk: Optional[str] = None
    name: str = ""
    order: int = 0

    def to_dict(self):
        return {"name": self.name, "order": self.order}

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.name = data.get("name", "") or ""
        o.order = int(data.get("order", 0) or 0)
        return o


# --- Category (group_id = Group doc id) ---
@dataclass
class CategoryFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_categories")
    pk: Optional[str] = None
    name: str = ""
    group_id: str = ""
    include_in_reports: bool = True
    order: int = 0

    def to_dict(self):
        return {
            "name": self.name,
            "group_id": self.group_id,
            "include_in_reports": self.include_in_reports,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.name = data.get("name", "") or ""
        o.group_id = data.get("group_id", "") or ""
        o.include_in_reports = bool(data.get("include_in_reports", True))
        o.order = int(data.get("order", 0) or 0)
        return o


# --- Transaction ---
@dataclass
class TransactionFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_transactions")
    pk: Optional[str] = None
    user_id: str = ""
    date: Optional[date] = None
    month: str = ""
    description: str = ""
    category_id: Optional[str] = None
    classification: Optional[str] = None
    amount: Decimal = Decimal("0")
    direction: str = "expense"
    source_account: str = ""
    external_id: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "month": self.month,
            "description": (self.description or "")[:500],
            "category_id": self.category_id,
            "classification": self.classification,
            "amount": str(self.amount),
            "direction": self.direction,
            "source_account": self.source_account or "",
            "external_id": self.external_id or "",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.user_id = data.get("user_id", "") or ""
        o.date = _as_date(data.get("date"))
        o.month = data.get("month", "") or ""
        o.description = data.get("description", "") or ""
        o.category_id = data.get("category_id")
        o.classification = data.get("classification")
        o.amount = _as_decimal(data.get("amount", "0"))
        o.direction = data.get("direction", "expense")
        o.source_account = data.get("source_account", "") or ""
        o.external_id = data.get("external_id", "") or ""
        o.created_at = _as_datetime(data.get("created_at"))
        o.updated_at = _as_datetime(data.get("updated_at"))
        return o

    def save(self):
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        return super().save()

    @classmethod
    def list_by_user(cls, user_id: str, month: Optional[str] = None, limit: int = 500) -> List:
        # Query by user_id only to avoid requiring a composite index (user_id + month + order_by date)
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("user_id", "==", str(user_id)).limit(1000)
        out = [cls.from_dict(d.id, d.to_dict()) for d in q.stream()]
        if month:
            out = [t for t in out if t.month == month]
        out.sort(key=lambda t: (t.date or date(1970, 1, 1)), reverse=True)
        return out[:limit]

    @classmethod
    def exists_by_external_id(cls, user_id: str, external_id: str) -> bool:
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("user_id", "==", str(user_id)).where("external_id", "==", external_id).limit(1)
        return len(list(q.stream())) > 0

    @classmethod
    def get_by_external_id(cls, user_id: str, external_id: str):
        """Return the first transaction with this user_id and external_id, or None."""
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("user_id", "==", str(user_id)).where("external_id", "==", external_id).limit(1)
        for doc in q.stream():
            return cls.from_dict(doc.id, doc.to_dict())
        return None


# --- MerchantCategoryLink ---
@dataclass
class MerchantCategoryLinkFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_merchant_links")
    pk: Optional[str] = None
    keyword: str = ""
    category_id: str = ""
    user_id: Optional[str] = None

    def to_dict(self):
        return {"keyword": self.keyword, "category_id": self.category_id, "user_id": self.user_id}

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.keyword = data.get("keyword", "") or ""
        o.category_id = data.get("category_id", "") or ""
        o.user_id = data.get("user_id")
        return o

    @classmethod
    def list_by_user(cls, user_id: str, limit: int = 500) -> List:
        return cls.query_by_field("user_id", "==", str(user_id), limit=limit)


# --- Budget ---
@dataclass
class BudgetFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_budgets")
    pk: Optional[str] = None
    user_id: str = ""
    category_id: str = ""
    year: int = 0
    month: int = 0
    forecast: Decimal = Decimal("0")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "category_id": self.category_id,
            "year": self.year,
            "month": self.month,
            "forecast": str(self.forecast),
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.user_id = data.get("user_id", "") or ""
        o.category_id = data.get("category_id", "") or ""
        o.year = int(data.get("year", 0) or 0)
        o.month = int(data.get("month", 0) or 0)
        o.forecast = _as_decimal(data.get("forecast", "0"))
        return o

    @classmethod
    def list_by_user(cls, user_id: str, year: Optional[int] = None, month: Optional[int] = None, limit: int = 1000) -> List:
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("user_id", "==", str(user_id))
        if year is not None:
            q = q.where("year", "==", year)
        if month is not None:
            q = q.where("month", "==", month)
        q = q.limit(limit)
        out = [cls.from_dict(d.id, d.to_dict()) for d in q.stream()]
        out.sort(key=lambda x: (x.year, x.month, x.category_id))
        return out

    @classmethod
    def get_by_user_category_month(cls, user_id: str, category_id: str, year: int, month: int):
        db = get_firestore_client()
        q = (
            db.collection(cls.collection_name)
            .where("user_id", "==", str(user_id))
            .where("category_id", "==", str(category_id))
            .where("year", "==", year)
            .where("month", "==", month)
            .limit(1)
        )
        for d in q.stream():
            return cls.from_dict(d.id, d.to_dict())
        return None


# --- Savings ---
@dataclass
class SavingsFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_savings")
    pk: Optional[str] = None
    user_id: str = ""
    year: int = 0
    month: int = 0
    actual: Optional[Decimal] = None
    target: Decimal = Decimal("0")
    goal_status: str = "pending"

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "year": self.year,
            "month": self.month,
            "actual": str(self.actual) if self.actual is not None else None,
            "target": str(self.target),
            "goal_status": self.goal_status,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.user_id = data.get("user_id", "") or ""
        o.year = int(data.get("year", 0) or 0)
        o.month = int(data.get("month", 0) or 0)
        a = data.get("actual")
        o.actual = _as_decimal(a) if a is not None else None
        o.target = _as_decimal(data.get("target", "0"))
        o.goal_status = data.get("goal_status", "pending") or "pending"
        return o

    @classmethod
    def list_by_user(cls, user_id: str, limit: int = 100) -> List:
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("user_id", "==", str(user_id)).limit(limit)
        out = [cls.from_dict(d.id, d.to_dict()) for d in q.stream()]
        out.sort(key=lambda x: (x.year, x.month), reverse=True)
        return out[:limit]

    @classmethod
    def get_by_user_month(cls, user_id: str, year: int, month: int):
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("user_id", "==", str(user_id)).where("year", "==", year).where("month", "==", month).limit(1)
        for d in q.stream():
            return cls.from_dict(d.id, d.to_dict())
        return None


# --- Commitment ---
@dataclass
class CommitmentFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_commitments")
    pk: Optional[str] = None
    user_id: str = ""
    name: str = ""
    amount: Decimal = Decimal("0")
    start_date: Optional[date] = None
    term_months: int = 0
    frequency: str = "monthly"
    payment_amount: Decimal = Decimal("0")
    balloon: Decimal = Decimal("0")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "amount": str(self.amount),
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "term_months": self.term_months,
            "frequency": self.frequency,
            "payment_amount": str(self.payment_amount),
            "balloon": str(self.balloon),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.user_id = data.get("user_id", "") or ""
        o.name = data.get("name", "") or ""
        o.amount = _as_decimal(data.get("amount", "0"))
        o.start_date = _as_date(data.get("start_date"))
        o.term_months = int(data.get("term_months", 0) or 0)
        o.frequency = data.get("frequency", "monthly") or "monthly"
        o.payment_amount = _as_decimal(data.get("payment_amount", "0"))
        o.balloon = _as_decimal(data.get("balloon", "0"))
        o.created_at = _as_datetime(data.get("created_at"))
        o.updated_at = _as_datetime(data.get("updated_at"))
        return o

    def save(self):
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        return super().save()

    @classmethod
    def list_by_user(cls, user_id: str, limit: int = 100) -> List:
        return cls.query_by_field("user_id", "==", str(user_id), limit=limit)


# --- CommitmentScheduleLine ---
@dataclass
class CommitmentScheduleLineFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_commitment_schedule_lines")
    pk: Optional[str] = None
    commitment_id: str = ""
    due_date: Optional[date] = None
    amount: Decimal = Decimal("0")
    status: str = "outstanding"
    sequence: int = 0

    def to_dict(self):
        return {
            "commitment_id": self.commitment_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "amount": str(self.amount),
            "status": self.status,
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.commitment_id = data.get("commitment_id", "") or ""
        o.due_date = _as_date(data.get("due_date"))
        o.amount = _as_decimal(data.get("amount", "0"))
        o.status = data.get("status", "outstanding") or "outstanding"
        o.sequence = int(data.get("sequence", 0) or 0)
        return o

    @classmethod
    def list_by_commitment(cls, commitment_id: str, limit: int = 500) -> List:
        # Query by commitment_id only to avoid composite index (commitment_id + order_by due_date)
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("commitment_id", "==", str(commitment_id)).limit(limit)
        out = [cls.from_dict(d.id, d.to_dict()) for d in q.stream()]
        out.sort(key=lambda x: (x.due_date or date(1970, 1, 1), x.sequence))
        return out[:limit]

    @classmethod
    def sum_outstanding_by_commitment(cls, commitment_id: str) -> Decimal:
        lines = cls.list_by_commitment(commitment_id)
        return sum((l.amount for l in lines if l.status == "outstanding"), Decimal("0"))

    @classmethod
    def sum_amount_due_in_month(cls, user_id: str, year: int, month: int) -> Decimal:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        commitments = CommitmentFS.list_by_user(user_id)
        c_ids = [c.pk for c in commitments]
        total = Decimal("0")
        for cid in c_ids:
            for line in cls.list_by_commitment(cid):
                if line.due_date and start <= line.due_date < end:
                    total += line.amount
        return total


# --- FinancialStanding ---
@dataclass
class FinancialStandingFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_financial_standings")
    pk: Optional[str] = None
    user_id: str = ""
    snapshot_date: Optional[date] = None
    total_assets: Decimal = Decimal("0")
    current_assets: Decimal = Decimal("0")
    fixed_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    short_term_liabilities: Decimal = Decimal("0")
    long_term_liabilities: Decimal = Decimal("0")
    notes: str = ""
    created_at: Optional[datetime] = None

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "total_assets": str(self.total_assets),
            "current_assets": str(self.current_assets),
            "fixed_assets": str(self.fixed_assets),
            "total_liabilities": str(self.total_liabilities),
            "short_term_liabilities": str(self.short_term_liabilities),
            "long_term_liabilities": str(self.long_term_liabilities),
            "notes": self.notes or "",
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.user_id = data.get("user_id", "") or ""
        o.snapshot_date = _as_date(data.get("snapshot_date"))
        o.total_assets = _as_decimal(data.get("total_assets", "0"))
        o.current_assets = _as_decimal(data.get("current_assets", "0"))
        o.fixed_assets = _as_decimal(data.get("fixed_assets", "0"))
        o.total_liabilities = _as_decimal(data.get("total_liabilities", "0"))
        o.short_term_liabilities = _as_decimal(data.get("short_term_liabilities", "0"))
        o.long_term_liabilities = _as_decimal(data.get("long_term_liabilities", "0"))
        o.notes = data.get("notes", "") or ""
        o.created_at = _as_datetime(data.get("created_at"))
        return o

    def save(self):
        if not self.created_at:
            self.created_at = datetime.utcnow()
        return super().save()

    @classmethod
    def list_by_user(cls, user_id: str, limit: int = 100) -> List:
        db = get_firestore_client()
        q = db.collection(cls.collection_name).where("user_id", "==", str(user_id)).limit(limit)
        out = [cls.from_dict(d.id, d.to_dict()) for d in q.stream()]
        out.sort(key=lambda x: x.snapshot_date or date(1970, 1, 1), reverse=True)
        return out[:limit]


# --- UploadTemplate (optional) ---
@dataclass
class UploadTemplateFS(BudgetingFirestoreModel):
    collection_name: str = field(init=False, default="budgeting_upload_templates")
    pk: Optional[str] = None
    user_id: Optional[str] = None
    name: str = ""
    column_mapping: Dict = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "column_mapping": self.column_mapping or {},
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: Dict[str, Any]):
        o = cls(pk=doc_id)
        o.user_id = data.get("user_id")
        o.name = data.get("name", "") or ""
        o.column_mapping = data.get("column_mapping") or {}
        o.created_at = _as_datetime(data.get("created_at"))
        return o

    def save(self):
        if not self.created_at:
            self.created_at = datetime.utcnow()
        return super().save()
