from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class InvoiceCreate(BaseModel):
    invoice_number: str
    vendor_name: str
    vendor_tax_id: Optional[str] = None
    invoice_date: date
    due_date: Optional[date] = None
    currency: str = "USD"
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    po_number: Optional[str] = None
    file_path: str
    raw_text: Optional[str] = None
    confidence_score: Optional[float] = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_number: str
    vendor_name: str
    status: str
    total_amount: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime


class ApprovalCreate(BaseModel):
    approver_email: str
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: Optional[str] = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    agent_name: str
    message: Optional[str]
    old_status: Optional[str]
    new_status: Optional[str]
    created_at: datetime


class InvoiceLineItemCreate(BaseModel):
    line_no: int
    description: str
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    line_total: Decimal


class InvoiceLineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: str
    line_no: int
    description: str
    quantity: Optional[Decimal]
    unit_price: Optional[Decimal]
    tax_rate: Optional[Decimal]
    line_total: Decimal


class VendorCreate(BaseModel):
    name: str
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    default_currency: Optional[str] = None
    is_active: bool = True


class VendorUpdate(BaseModel):
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    default_currency: Optional[str] = None
    is_active: Optional[bool] = None


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tax_id: Optional[str]
    payment_terms: Optional[str]
    default_currency: Optional[str]
    is_active: bool
    created_at: datetime
