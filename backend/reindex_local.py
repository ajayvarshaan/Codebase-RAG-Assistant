from database.database import SessionLocal

# Import all related models so SQLAlchemy
# can correctly configure relationships.
from models.project import Project
from models.user import User
from models.code_file import CodeFile
from models.code_chunk import CodeChunk
from models.code_relationship import CodeRelationship

from services.chunking import split_code_into_chunks

from services.embedding_service import (
    EMBEDDING_MODEL,
    create_embeddings
)


def reindex_all_projects():

    db = SessionLocal()

    try:
        print("=" * 60)
        print("LOCAL EMBEDDING RE-INDEXING")
        print("=" * 60)

        # -----------------------------------------------------
        # Delete existing chunks
        # -----------------------------------------------------

        deleted = db.query(CodeChunk).delete(
            synchronize_session=False
        )

        db.commit()

        print(f"Old chunks deleted: {deleted}")

        # -----------------------------------------------------
        # Get all existing code files
        # -----------------------------------------------------

        code_files = (
            db.query(CodeFile)
            .order_by(
                CodeFile.project_id,
                CodeFile.file_path
            )
            .all()
        )

        print(
            f"Code files found: {len(code_files)}"
        )

        print(
            f"Embedding model: {EMBEDDING_MODEL}"
        )

        print()

        total_chunks = 0

        # -----------------------------------------------------
        # Process every code file
        # -----------------------------------------------------

        for file_number, code_file in enumerate(
            code_files,
            start=1
        ):

            print(
                f"[{file_number}/{len(code_files)}] "
                f"{code_file.file_path}"
            )

            chunks = split_code_into_chunks(
                code_file.content
            )

            if not chunks:

                print("  No chunks found")

                continue

            # -------------------------------------------------
            # Create LOCAL embeddings
            # -------------------------------------------------

            embeddings = create_embeddings(
                [
                    chunk["content"]
                    for chunk in chunks
                ]
            )

            # -------------------------------------------------
            # Save chunks
            # -------------------------------------------------

            for chunk, embedding in zip(
                chunks,
                embeddings
            ):

                code_chunk = CodeChunk(
                    project_id=code_file.project_id,
                    file_id=code_file.id,
                    content=chunk["content"],
                    chunk_index=chunk["chunk_index"],
                    start_line=chunk["start_line"],
                    end_line=chunk["end_line"],
                    embedding=embedding,
                    embedding_model=EMBEDDING_MODEL
                )

                db.add(code_chunk)

                total_chunks += 1

            print(
                f"  Chunks created: {len(chunks)}"
            )

        # -----------------------------------------------------
        # Commit everything
        # -----------------------------------------------------

        db.commit()

        print()
        print("=" * 60)
        print("RE-INDEXING COMPLETED")
        print("=" * 60)

        print(
            f"Files processed: {len(code_files)}"
        )

        print(
            f"Total chunks created: {total_chunks}"
        )

        print(
            f"Embedding model: {EMBEDDING_MODEL}"
        )

        print(
            "Embedding source: LOCAL"
        )

        print("=" * 60)

    except Exception as error:

        db.rollback()

        print()
        print("ERROR:")
        print(error)

        raise

    finally:

        db.close()


if __name__ == "__main__":
    reindex_all_projects()