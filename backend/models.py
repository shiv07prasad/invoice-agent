from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True)
    invoice_number = Column(String(100), index=True, nullable=False)
    vendor_name = Column(String(255), index=True, nullable=False)
    vendor_tax_id = Column(String(100), nullable=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    po_number = Column(String(100), index=True, nullable=True)
    status = Column(String(30), nullable=False, default="received")
    confidence_score = Column(Float, nullable=True)
    file_path = Column(String(500), nullable=False)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    events = relationship("ProcessingEvent", back_populates="invoice", cascade="all, delete-orphan")
    exceptions = relationship("ExceptionRecord", back_populates="invoice", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), index=True, nullable=False)
    line_no = Column(Integer, nullable=False)
    description = Column(String(1000), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=True)
    tax_rate = Column(Numeric(5, 2), nullable=True)
    line_total = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")


class ProcessingEvent(Base):
    __tablename__ = "processing_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), index=True, nullable=False)
    event_type = Column(String(50), nullable=False)
    agent_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=True)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    invoice = relationship("Invoice", back_populates="events")


class ExceptionRecord(Base):
    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), index=True, nullable=False)
    reason_code = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="medium")
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    invoice = relationship("Invoice", back_populates="exceptions")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), index=True, nullable=False)
    approver_email = Column(String(255), nullable=False)
    decision = Column(String(20), nullable=False, default="pending")
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    invoice = relationship("Invoice", back_populates="approvals")


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    tax_id = Column(String(100), nullable=True)
    payment_terms = Column(String(100), nullable=True)
    default_currency = Column(String(10), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

