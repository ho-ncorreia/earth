import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ArchitectureDecision, ArchitectureRisk, ArchitectureStudy, User

STOP_WORDS = {"a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "in", "is", "it", "of", "on", "or", "the", "to", "what", "when", "where", "which", "who", "why", "with", "about", "does", "can", "this", "that", "dans", "les", "des", "une", "est", "pour", "avec", "quel", "quelle", "comment", "quoi", "sur", "que"}


def terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-zA-Z0-9À-ÿ_-]{3,}", text.lower()) if word not in STOP_WORDS}


def ranked_sources(db: Session, user: User, question: str, limit: int = 5) -> list[dict]:
    query_terms = terms(question)
    if not query_terms:
        return []
    candidates: list[dict] = []
    if "studies.read" in {item.code for item in user.role.permissions}:
        for study in db.scalars(select(ArchitectureStudy).order_by(ArchitectureStudy.updated_at.desc()).limit(200)).all():
            if study.confidentiality == "Restricted" and user.role.name != "Administrator" and study.lead_architect_id != user.id:
                continue
            excerpt = "\n".join((study.title, study.description, study.business_context, study.business_objectives, study.scope))
            candidates.append({"type": "study", "id": study.id, "title": f"{study.identifier} · {study.title}", "excerpt": excerpt[:1000]})
    if "decisions.read" in {item.code for item in user.role.permissions}:
        for decision in db.scalars(select(ArchitectureDecision).order_by(ArchitectureDecision.updated_at.desc()).limit(200)).all():
            if any(study.confidentiality == "Restricted" and study.lead_architect_id != user.id for study in decision.related_studies) and user.role.name != "Administrator":
                continue
            excerpt = "\n".join((decision.title, decision.context, decision.problem_statement, decision.decision_rationale, decision.selected_option, decision.positive_consequences, decision.negative_consequences))
            candidates.append({"type": "decision", "id": decision.id, "title": f"{decision.number} · {decision.title}", "excerpt": excerpt[:1000]})
    if "risks.read" in {item.code for item in user.role.permissions}:
        for risk in db.scalars(select(ArchitectureRisk).order_by(ArchitectureRisk.updated_at.desc()).limit(200)).all():
            study = db.get(ArchitectureStudy, risk.study_id) if risk.study_id else None
            if study and study.confidentiality == "Restricted" and study.lead_architect_id != user.id and user.role.name != "Administrator":
                continue
            excerpt = "\n".join((risk.title, risk.description, risk.cause, risk.risk_event, risk.consequences, risk.existing_controls))
            candidates.append({"type": "risk", "id": risk.id, "title": f"{risk.identifier} · {risk.title}", "excerpt": excerpt[:1000]})
    for source in candidates:
        source_terms = terms(source["title"] + " " + source["excerpt"])
        source["score"] = len(query_terms & source_terms)
    return sorted((source for source in candidates if source["score"] > 0), key=lambda source: source["score"], reverse=True)[:limit]