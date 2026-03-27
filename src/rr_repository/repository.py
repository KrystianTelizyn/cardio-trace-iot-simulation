"""Repository for heart rate records and their RR intervals."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from .db import get_engine, get_session_factory, init_db
from .models import Record, pack_rr_intervals, unpack_rr_intervals
from .exceptions import (
    RecordNotFoundError,
    RecordDuplicateError,
    InitializationError,
    RecordValidationError,
)


class RecordRepository:
    """Provides access to heart rate records and their RR intervals."""

    def __init__(self, db_path: str | Path | None = None):
        try:
            self._db_path = db_path or Path("data/rr_records.db")
            self._engine = get_engine(self._db_path)
            init_db(self._engine)
            self._session_factory = get_session_factory(self._engine)
        except SQLAlchemyError as e:
            raise InitializationError(self._db_path) from e

    def list_records(self, tag_part: str | None = None) -> list[dict]:
        """List records as dicts {tag, description, size}, optionally filtered by tag."""
        with self._session_factory() as session:
            stmt = select(Record)
            if tag_part is not None:
                # Filter records by tag containing the tag_part
                stmt = stmt.filter(Record.tag.like(f"%{tag_part}%"))
            records = session.execute(stmt).scalars().all()
            return [
                {"tag": r.tag, "description": r.description, "size": r.size}
                for r in records
            ]

    def add_record(
        self,
        tag: str,
        description: str,
        rr_intervals: list[float],
    ) -> Record:
        """Create a new record with RR intervals. Commits on success."""
        if self.record_exists(tag):
            raise RecordDuplicateError(tag)
        if len(rr_intervals) == 0:
            raise RecordValidationError("RR intervals cannot be empty")
        if len(rr_intervals) > 65535:
            raise RecordValidationError("RR intervals cannot be more than 65535")
        with self._session_factory() as session:
            blob = pack_rr_intervals(rr_intervals)
            record = Record(
                tag=tag,
                description=description,
                size=len(rr_intervals),
                rr_intervals_blob=blob,
            )
            session.add(record)
            session.commit()
            return {"tag": tag, "description": description, "size": len(rr_intervals)}

    def get_record_data(self, tag: str) -> list[int]:
        """Get RR intervals for a record by tag, ordered by sample index."""
        if not self.record_exists(tag):
            raise RecordNotFoundError(tag)
        with self._session_factory() as session:
            stmt = select(Record).where(Record.tag == tag)
            record = session.scalars(stmt).first()
            return unpack_rr_intervals(record.rr_intervals_blob)

    def record_exists(self, tag: str) -> bool:
        """Check if a record exists by tag."""
        with self._session_factory() as session:
            stmt = select(Record).where(Record.tag == tag)
            return session.scalars(stmt).first() is not None
