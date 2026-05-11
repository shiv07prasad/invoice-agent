from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from agents import add_event, run_invoice_pipeline
from database import SessionLocal
from init_db import init_db
from models import Approval, Invoice, InvoiceLineItem, ProcessingEvent, Vendor
from schemas import (
    ApprovalCreate,
    EventOut,
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceLineItemOut,
    InvoiceOut,
    VendorCreate,
    VendorOut,
    VendorUpdate,
)


app = FastAPI(title="Invoice Agent API", version="0.1.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    invoice = Invoice(
        id=str(uuid4()),
        invoice_number=payload.invoice_number,
        vendor_name=payload.vendor_name,
        vendor_tax_id=payload.vendor_tax_id,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        currency=payload.currency,
        subtotal=payload.subtotal,
        tax_amount=payload.tax_amount,
        total_amount=payload.total_amount,
        po_number=payload.po_number,
        status="received",
        confidence_score=payload.confidence_score,
        file_path=payload.file_path,
        raw_text=payload.raw_text,
    )
    db.add(invoice)
    db.flush()
    add_event(
        db,
        invoice.id,
        "ingested",
        "DocumentIntakeAgent",
        "Invoice received by API.",
        None,
        invoice.status,
    )
    db.commit()
    db.refresh(invoice)
    return invoice


@app.post("/invoices/{invoice_id}/process")
def process_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    result = run_invoice_pipeline(db, invoice)
    db.commit()
    db.refresh(invoice)
    return {
        "invoice_id": invoice.id,
        "status": invoice.status,
        "message": result.message,
    }


@app.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.created_at.desc()).all()


@app.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@app.get("/invoices/{invoice_id}/events", response_model=list[EventOut])
def get_invoice_events(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return (
        db.query(ProcessingEvent)
        .filter(ProcessingEvent.invoice_id == invoice_id)
        .order_by(ProcessingEvent.created_at.asc())
        .all()
    )


@app.post("/invoices/{invoice_id}/approval")
def approve_invoice(invoice_id: str, payload: ApprovalCreate, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    approval = Approval(
        invoice_id=invoice_id,
        approver_email=payload.approver_email,
        decision=payload.decision,
        comment=payload.comment,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(approval)

    old_status = invoice.status
    if payload.decision == "approved":
        invoice.status = "approved"
    else:
        invoice.status = "needs_review"

    add_event(
        db,
        invoice.id,
        "approved",
        "ApprovalExceptionAgent",
        f"Decision recorded: {payload.decision}",
        old_status,
        invoice.status,
    )
    db.commit()
    db.refresh(invoice)

    return {"invoice_id": invoice.id, "status": invoice.status, "decision": payload.decision}


@app.post("/invoices/{invoice_id}/line-items", response_model=InvoiceLineItemOut, status_code=status.HTTP_201_CREATED)
def add_line_item(invoice_id: str, payload: InvoiceLineItemCreate, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    line_item = InvoiceLineItem(
        invoice_id=invoice_id,
        line_no=payload.line_no,
        description=payload.description,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        tax_rate=payload.tax_rate,
        line_total=payload.line_total,
    )
    db.add(line_item)
    db.commit()
    db.refresh(line_item)
    return line_item


@app.get("/invoices/{invoice_id}/line-items", response_model=list[InvoiceLineItemOut])
def list_line_items(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == invoice_id).order_by(InvoiceLineItem.line_no.asc()).all()


@app.post("/vendors", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    existing = db.query(Vendor).filter(Vendor.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Vendor with this name already exists")

    vendor = Vendor(
        name=payload.name,
        tax_id=payload.tax_id,
        payment_terms=payload.payment_terms,
        default_currency=payload.default_currency,
        is_active=payload.is_active,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@app.get("/vendors", response_model=list[VendorOut])
def list_vendors(db: Session = Depends(get_db)):
    return db.query(Vendor).order_by(Vendor.name.asc()).all()


@app.get("/vendors/{vendor_id}", response_model=VendorOut)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@app.patch("/vendors/{vendor_id}", response_model=VendorOut)
def update_vendor(vendor_id: int, payload: VendorUpdate, db: Session = Depends(get_db)):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(vendor, key, value)

    db.commit()
    db.refresh(vendor)
    return vendor
