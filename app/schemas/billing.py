import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


# --- Fee Types ---


class FeeTypeCreate(BaseModel):
    name: str
    description: str | None = None
    category: str = "custom"
    default_amount: Decimal | None = None
    currency: str = "NGN"
    is_recurring: bool = False

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Fee type name cannot be empty")
        return v

    @field_validator("category")
    @classmethod
    def valid_category(cls, v: str) -> str:
        allowed = {"tuition", "material", "service", "contribution", "custom"}
        if v not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(sorted(allowed))}")
        return v

    def generate_slug(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", self.name.lower()).strip("_")
        return slug[:50]


class FeeTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    default_amount: Decimal | None = None
    is_recurring: bool | None = None
    is_active: bool | None = None


class FeeTypeOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    category: str
    default_amount: Decimal | None = None
    currency: str = "NGN"
    is_recurring: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Invoice Items ---


class InvoiceItemCreate(BaseModel):
    fee_type_id: uuid.UUID
    description: str
    quantity: int = 1
    unit_amount: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v

    @field_validator("unit_amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Unit amount must be greater than 0")
        return v

    @property
    def total_amount(self) -> Decimal:
        return self.quantity * self.unit_amount


class InvoiceItemOut(BaseModel):
    id: uuid.UUID
    fee_type_id: uuid.UUID
    description: str
    quantity: int
    unit_amount: Decimal
    total_amount: Decimal
    fee_type: FeeTypeOut | None = None

    class Config:
        from_attributes = True


# --- Invoices ---


class InvoiceCreate(BaseModel):
    parent_id: uuid.UUID
    student_id: uuid.UUID | None = None
    title: str
    academic_term: str | None = None
    items: list[InvoiceItemCreate]
    due_date: date | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Invoice title cannot be empty")
        return v

    @field_validator("items")
    @classmethod
    def at_least_one_item(cls, v: list) -> list:
        if not v:
            raise ValueError("Invoice must have at least one item")
        return v


class InvoiceBulkCreate(BaseModel):
    student_ids: list[uuid.UUID]
    title: str
    academic_term: str | None = None
    items: list[InvoiceItemCreate]
    due_date: date | None = None
    notes: str | None = None

    @field_validator("student_ids")
    @classmethod
    def at_least_one_student(cls, v: list) -> list:
        if not v:
            raise ValueError("Must specify at least one student")
        return v

    @field_validator("items")
    @classmethod
    def at_least_one_item(cls, v: list) -> list:
        if not v:
            raise ValueError("Invoice must have at least one item")
        return v


class InvoiceOut(BaseModel):
    id: uuid.UUID
    invoice_number: str
    parent_id: uuid.UUID
    student_id: uuid.UUID | None = None
    academic_term: str | None = None
    title: str
    total_amount: Decimal
    amount_paid: Decimal
    amount_remaining: Decimal
    currency: str = "NGN"
    status: str
    due_date: date | None = None
    notes: str | None = None
    issued_at: datetime
    paid_at: datetime | None = None
    created_at: datetime
    items: list[InvoiceItemOut] = []

    class Config:
        from_attributes = True


class InvoiceListOut(BaseModel):
    id: uuid.UUID
    invoice_number: str
    parent_id: uuid.UUID
    student_id: uuid.UUID | None = None
    title: str
    total_amount: Decimal
    amount_paid: Decimal
    status: str
    due_date: date | None = None
    academic_term: str | None = None
    issued_at: datetime

    class Config:
        from_attributes = True


class InvoiceSendRequest(BaseModel):
    custom_message: str | None = None


# --- Balance & Stats ---


class ParentBalanceOut(BaseModel):
    total_invoiced: Decimal
    total_paid: Decimal
    outstanding: Decimal
    invoice_count: int
    overdue_count: int


class BillingStatsOut(BaseModel):
    total_invoiced: Decimal
    total_collected: Decimal
    outstanding: Decimal
    overdue: Decimal
    invoice_count: int
    paid_count: int
    overdue_count: int
