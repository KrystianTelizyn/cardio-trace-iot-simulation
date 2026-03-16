"""SQLAlchemy model for heart rate records with RR intervals stored as blob."""

import array

from sqlalchemy import Column, LargeBinary, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase

BLOB_TYPE = "H"  # unsigned short, 2 bytes per value (RR in ms fits 0-65535)


def pack_rr_intervals(rr_intervals: list[int | float]) -> bytes:
    """Serialize RR intervals to compact binary blob as integers (ms)."""
    return array.array(BLOB_TYPE, [int(round(x)) for x in rr_intervals]).tobytes()


def unpack_rr_intervals(blob: bytes | None) -> list[int]:
    """Deserialize RR intervals from blob to list of integers (ms)."""
    if not blob:
        return []
    arr = array.array(BLOB_TYPE)
    arr.frombytes(blob)
    return list(arr)


class Base(DeclarativeBase):
    pass


class Record(Base):
    """Single table: one row per record, RR intervals stored as blob."""

    __tablename__ = "records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String, unique=True)
    description = Column(Text)
    size = Column(Integer)
    rr_intervals_blob = Column(LargeBinary)
