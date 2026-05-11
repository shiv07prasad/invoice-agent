from dataclasses import dataclass
from typing import Optional

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from models import ExceptionRecord, Invoice, ProcessingEvent


def add_event(
    db: Session,
    invoice_id: str,
    event_type: str,
    agent_name: str,
    message: Optional[str],
    old_status: Optional[str],
    new_status: Optional[str],
) -> None:
    db.add(
        ProcessingEvent(
            invoice_id=invoice_id,
            event_type=event_type,
            agent_name=agent_name,
            message=message,
            old_status=old_status,
            new_status=new_status,
        )
    )


@dataclass
class AgentResult:
    final_status: str
    message: str


class ExtractionAgent:
    name = "ExtractionAgent"

    def run(self, db: Session, invoice: Invoice) -> AgentResult:
        old_status = invoice.status
        invoice.status = "extracted"
        add_event(
            db,
            invoice.id,
            "extracted",
            self.name,
            "Invoice data extracted (prototype pipeline).",
            old_status,
            invoice.status,
        )
        return AgentResult(final_status=invoice.status, message="Extraction completed")


class ValidationMatchingAgent:
    name = "ValidationMatchingAgent"

    def run(self, db: Session, invoice: Invoice) -> AgentResult:
        old_status = invoice.status
        if invoice.total_amount < 0:
            invoice.status = "failed"
            add_event(
                db,
                invoice.id,
                "error",
                self.name,
                "Total amount cannot be negative.",
                old_status,
                invoice.status,
            )
            return AgentResult(final_status=invoice.status, message="Validation failed")

        if invoice.confidence_score is not None and invoice.confidence_score < 0.75:
            invoice.status = "needs_review"
            db.add(
                ExceptionRecord(
                    invoice_id=invoice.id,
                    reason_code="low_confidence",
                    details=f"Confidence score {invoice.confidence_score} is below threshold 0.75.",
                    severity="medium",
                    resolved=False,
                )
            )
            add_event(
                db,
                invoice.id,
                "validated",
                self.name,
                "Validation completed with review required.",
                old_status,
                invoice.status,
            )
            return AgentResult(final_status=invoice.status, message="Needs human review")

        invoice.status = "validated"
        add_event(
            db,
            invoice.id,
            "validated",
            self.name,
            "Validation and matching checks passed.",
            old_status,
            invoice.status,
        )
        return AgentResult(final_status=invoice.status, message="Validation completed")


class PostingAuditAgent:
    name = "PostingAuditAgent"

    def run(self, db: Session, invoice: Invoice) -> AgentResult:
        old_status = invoice.status
        invoice.status = "posted"
        add_event(
            db,
            invoice.id,
            "posted",
            self.name,
            "Invoice posted to accounting system (prototype stub).",
            old_status,
            invoice.status,
        )
        return AgentResult(final_status=invoice.status, message="Posting completed")


@dataclass
class PipelineState:
    db: Session
    invoice: Invoice
    result: Optional[AgentResult] = None


def _extract_node(state: PipelineState) -> PipelineState:
    state.result = ExtractionAgent().run(state.db, state.invoice)
    return state


def _validate_node(state: PipelineState) -> PipelineState:
    state.result = ValidationMatchingAgent().run(state.db, state.invoice)
    return state


def _post_node(state: PipelineState) -> PipelineState:
    state.result = PostingAuditAgent().run(state.db, state.invoice)
    return state


def _route_after_validate(state: PipelineState) -> str:
    if state.invoice.status == "validated":
        return "post"
    return "end"


def _build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("extract", _extract_node)
    graph.add_node("validate", _validate_node)
    graph.add_node("post", _post_node)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "validate")
    graph.add_conditional_edges("validate", _route_after_validate, {"post": "post", "end": END})
    graph.add_edge("post", END)
    return graph.compile()


PIPELINE_GRAPH = _build_graph()


def run_invoice_pipeline(db: Session, invoice: Invoice) -> AgentResult:
    final_state = PIPELINE_GRAPH.invoke(PipelineState(db=db, invoice=invoice))
    if final_state.result is None:
        return AgentResult(final_status=invoice.status, message="Pipeline finished")
    return final_state.result
