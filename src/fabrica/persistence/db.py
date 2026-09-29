"""Issues e histórico de status em SQLAlchemy."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Integer, String, Text, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from fabrica.records import IssueView


class Base(DeclarativeBase):
    pass


class IssueRow(Base):
    """Uma linha por pedido."""

    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request: Mapped[str] = mapped_column(Text)
    phase: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(40), default="")
    markdown: Mapped[str] = mapped_column(Text, default="")
    document_json: Mapped[str] = mapped_column(Text, default="{}")


class StatusRow(Base):
    """Uma transição do canal de status."""

    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_id: Mapped[str] = mapped_column(String(64), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    agent: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(Text)


class SqlIssueStore:
    """Persiste a projeção da issue. O checkpoint do grafo fica em outro lugar."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._session = sessionmaker(bind=engine, expire_on_commit=False)
        Base.metadata.create_all(engine)

    def save(self, view: IssueView) -> None:
        with self._session() as session:
            row = session.get(IssueRow, view.id)
            if row is None:
                row = IssueRow(id=view.id, request=view.pedido, phase=view.fase)
                session.add(row)
            row.request = view.pedido
            row.phase = view.fase
            row.outcome = view.resultado
            row.markdown = view.markdown
            row.document_json = json.dumps(view.documento, ensure_ascii=False)
            session.execute(delete(StatusRow).where(StatusRow.issue_id == view.id))
            for seq, event in enumerate(view.registro_de_status):
                session.add(
                    StatusRow(
                        issue_id=view.id,
                        seq=seq,
                        agent=event.get("agent", ""),
                        status=event.get("status", ""),
                        detail=event.get("detail", ""),
                    )
                )
            session.commit()

    def get(self, issue_id: str) -> IssueView | None:
        with self._session() as session:
            row = session.get(IssueRow, issue_id)
            if row is None:
                return None
            events = session.scalars(
                select(StatusRow).where(StatusRow.issue_id == issue_id).order_by(StatusRow.seq)
            ).all()
            return _view(row, events)


def make_engine(url: str) -> Any:
    """Engine compartilhada. SQLite em memória usa um pool estático."""
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


def _view(row: IssueRow, events: list[StatusRow]) -> IssueView:
    try:
        document = json.loads(row.document_json or "{}")
    except json.JSONDecodeError:
        document = {}
    if not isinstance(document, dict):
        document = {}
    return IssueView(
        id=row.id,
        pedido=row.request,
        fase=row.phase,
        resultado=row.outcome or "",
        registro_de_status=[
            {"agent": event.agent, "status": event.status, "detail": event.detail} for event in events
        ],
        markdown=row.markdown or "",
        documento=document,
    )

