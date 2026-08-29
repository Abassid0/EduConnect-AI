import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: uuid.UUID
    reference: str
    student_id: uuid.UUID
    enrollment_id: uuid.UUID | None = None
    programme_id: uuid.UUID | None = None
    invoice_id: uuid.UUID | None = None
    fee_type_id: uuid.UUID | None = None
    payment_type: str = "enrollment"
    description: str | None = None
    amount: Decimal
    currency: str = "NGN"
    status: str = "pending"
    whatsapp_number: str
    paystack_reference: str | None = None
    paystack_authorization_url: str | None = None
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentListOut(BaseModel):
    id: uuid.UUID
    reference: str
    amount: Decimal
    currency: str = "NGN"
    status: str
    paid_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentVerifyOut(BaseModel):
    reference: str
    status: str
    amount: Decimal
    paystack_status: str
    verified: bool
