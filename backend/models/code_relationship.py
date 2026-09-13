from sqlalchemy import Column, Integer, String, ForeignKey

from database.database import Base


class CodeRelationship(Base):
    __tablename__ = "code_relationships"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False
    )

    source_file_id = Column(
        Integer,
        ForeignKey("code_files.id"),
        nullable=False
    )

    target_file_id = Column(
        Integer,
        ForeignKey("code_files.id"),
        nullable=False
    )

    relationship_type = Column(
        String,
        nullable=False
    )