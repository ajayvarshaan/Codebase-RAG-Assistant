from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from database.database import Base


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False
    )

    file_id = Column(
        Integer,
        ForeignKey("code_files.id"),
        nullable=False
    )

    content = Column(Text, nullable=False)

    chunk_index = Column(Integer, nullable=False)

    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    embedding = Column(Vector(1536), nullable=True)

    embedding_model = Column(
        String(100),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )