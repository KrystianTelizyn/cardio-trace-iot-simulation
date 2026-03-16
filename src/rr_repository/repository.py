"""Repository for heart rate records and their RR intervals."""

from pathlib import Path

from sqlalchemy import select

from .db import get_engine, get_session_factory, init_db
from .models import Record, pack_rr_intervals, unpack_rr_intervals


class RecordRepository:
    """Provides access to heart rate records and their RR intervals."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = db_path or Path("data/rr_records.db")
        self._engine = get_engine(self._db_path)
        init_db(self._engine)
        self._session_factory = get_session_factory(self._engine)

    def list_records(self, tag: str | None = None) -> list[dict]:
        """List records as dicts {tag, description, size}, optionally filtered by tag."""
        with self._session_factory() as session:
            stmt = select(Record)
            if tag is not None:
                stmt = stmt.where(Record.tag == tag)
            records = list(session.scalars(stmt).all())
            return [
                {"tag": r.tag, "description": r.description, "size": r.size}
                for r in records
            ]

    def add_record(
        self,
        tag: str | None = None,
        description: str | None = None,
        rr_intervals: list[float] | None = None,
    ) -> Record:
        """Create a new record with optional RR intervals. Commits on success."""
        with self._session_factory() as session:
            blob = pack_rr_intervals(rr_intervals) if rr_intervals else None
            record = Record(
                tag=tag,
                description=description,
                size=len(rr_intervals) if rr_intervals else 0,
                rr_intervals_blob=blob,
            )
            session.add(record)
            session.commit()
            return record

    def get_record_data(self, tag: str) -> list[int]:
        """Get RR intervals for a record by tag, ordered by sample index."""
        with self._session_factory() as session:
            stmt = select(Record).where(Record.tag == tag)
            record = session.scalars(stmt).first()
            if record is None:
                return []
            return unpack_rr_intervals(record.rr_intervals_blob)
