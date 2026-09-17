from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    description = Column(
        String,
        nullable=True
    )

    github_url = Column(
        String(500),
        nullable=True
    )

    github_commit_sha = Column(
        String(40),
        nullable=True
    )

    github_previous_commit_sha = Column(
        String(40),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationship with code files
    code_files = relationship(
        "CodeFile",
        back_populates="project",
        cascade="all, delete-orphan"
    )