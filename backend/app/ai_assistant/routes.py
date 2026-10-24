from fastapi import APIRouter, Depends, HTTPException, Request
from httpx import HTTPError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_assistant.provider import MistralProvider, MistralUnavailable, NO_SOURCE_ANSWER, PROMPT_VERSION
from app.ai_assistant.retrieval import ranked_sources
from app.audit.service import record_event
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_csrf
from app.models import AIConversation, AIMessage, SourceReference, User
from app.schemas import AIConversationDetailOut, AIConversationOut, ChatAsk, ChatResponse, Page

router = APIRouter(prefix="/ai", tags=["AI architecture assistant"])


def require_assistant(user: User) -> None:
    if "assistant.use" not in {permission.code for permission in user.role.permissions}:
        raise HTTPException(status_code=403, detail="Insufficient permission")


@router.get("/conversations", response_model=Page[AIConversationOut])
def list_conversations(limit: int = 25, offset: int = 0, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_assistant(user)
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    rows = db.scalars(select(AIConversation).where(AIConversation.owner_id == user.id).order_by(AIConversation.updated_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count(AIConversation.id)).where(AIConversation.owner_id == user.id)) or 0
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/conversations", response_model=AIConversationOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_conversation(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AIConversation:
    require_assistant(user)
    conversation = AIConversation(owner_id=user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetailOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AIConversation:
    require_assistant(user)
    conversation = db.scalar(select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.owner_id == user.id))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/ask", response_model=ChatResponse, dependencies=[Depends(require_csrf)])
async def ask(payload: ChatAsk, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_assistant(user)
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty")
    conversation = None
    if payload.conversation_id is not None:
        conversation = db.scalar(select(AIConversation).where(AIConversation.id == payload.conversation_id, AIConversation.owner_id == user.id))
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = AIConversation(owner_id=user.id, title=question[:120])
        db.add(conversation)
        db.flush()

    sources = ranked_sources(db, user, question)
    if not sources:
        answer = NO_SOURCE_ANSWER
        model_name = "authorised-search"
    else:
        provider = MistralProvider()
        try:
            answer = await provider.answer(question, sources)
        except MistralUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except HTTPError as exc:
            raise HTTPException(status_code=502, detail="Mistral is temporarily unavailable.") from exc
        model_name = settings.mistral_model
        answer = f"{answer}\n\nSources: " + "; ".join(f"[R{index}] {source['title']}" for index, source in enumerate(sources, start=1))

    user_message = AIMessage(conversation_id=conversation.id, role="user", content=question, model="", prompt_version=PROMPT_VERSION)
    assistant_message = AIMessage(conversation_id=conversation.id, role="assistant", content=answer, model=model_name, prompt_version=PROMPT_VERSION)
    db.add_all([user_message, assistant_message])
    db.flush()
    for index, source in enumerate(sources, start=1):
        db.add(SourceReference(message_id=assistant_message.id, source_type=source["type"], object_id=source["id"], title=f"[R{index}] {source['title']}", excerpt=source["excerpt"][:1000]))
    record_event(
        db,
        actor=user,
        action="ai.sources_retrieved" if sources else "ai.no_source",
        object_type="ai_conversation",
        object_id=str(conversation.id),
        new_value={"source_count": len(sources), "model": model_name, "prompt_version": PROMPT_VERSION},
        correlation_id=request.headers.get("x-correlation-id", ""),
        origin="ai-assistant",
    )
    db.commit()
    db.refresh(conversation)
    db.refresh(user_message)
    db.refresh(assistant_message)
    return {"conversation": conversation, "user_message": user_message, "assistant_message": assistant_message}