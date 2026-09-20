from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class AIResult(Base):
    __tablename__ = "ai_results"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_id = Column(
        Integer,
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    tool_name = Column(
        String(100),
        nullable=False,
        index=True,
    )

    result_json = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
