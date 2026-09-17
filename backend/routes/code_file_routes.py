from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from zipfile import ZipFile, BadZipFile
from io import BytesIO
from pathlib import PurePosixPath

from database.database import SessionLocal
from models.code_file import CodeFile
from models.code_chunk import CodeChunk
from models.project import Project
from models.code_relationship import CodeRelationship

from services.chunking import split_code_into_chunks
from services.embedding_service import EMBEDDING_MODEL, create_embedding, create_embeddings
from services.import_analyzer import find_imports
from services.auth_dependency import get_current_user
from models.user import User


router = APIRouter(prefix="/files", tags=["Files"])


# =========================================================
# Security limits for uploaded projects
# =========================================================

MAX_ZIP_SIZE = 25 * 1024 * 1024       # 25 MB
MAX_UNCOMPRESSED_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_FILES = 200
MAX_FILE_SIZE = 2 * 1024 * 1024       # 2 MB per file


class CodeFileCreate(BaseModel):
    project_id: int = Field(gt=0)
    file_path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=2 * 1024 * 1024)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# Helpers
# =========================================================

def is_safe_zip_path(file_path: str):
    """
    Prevent ZIP path traversal such as:
    ../../secret.txt
    ..\\secret.txt
    /absolute/path.txt
    C:/absolute/path.txt
    """
    normalized = file_path.replace("\\", "/")

    if not normalized or normalized.startswith("/"):
        return False

    path = PurePosixPath(normalized)

    if any(part == ".." for part in path.parts):
        return False

    # Reject Windows drive-style paths such as C:/file.txt
    if len(normalized) >= 2 and normalized[1] == ":":
        return False

    return True


def resolve_import_path(source_path: str, import_path: str, file_map: dict):
    """
    Resolve a relative JS/TS import to an indexed file.
    """
    if not import_path.startswith("."):
        return None

    source_dir = PurePosixPath(source_path).parent
    target = PurePosixPath(
        str(source_dir / import_path)
    )

    normalized = str(target)

    extensions = ["", ".ts", ".tsx", ".js", ".jsx", ".py"]

    for extension in extensions:
        candidate = normalized + extension
        if candidate in file_map:
            return file_map[candidate]

    for extension in [".ts", ".tsx", ".js", ".jsx", ".py"]:
        candidate = normalized + "/index" + extension
        if candidate in file_map:
            return file_map[candidate]

    return None


def create_relationships(
    db: Session,
    project_id: int,
    code_files: list[CodeFile]
):
    """
    Build import relationships after all files are indexed.
    """
    file_map = {
        code_file.file_path: code_file
        for code_file in code_files
    }

    relationships = []

    for source_file in code_files:
        imports = find_imports(source_file.content)

        for import_path in imports:
            target_file = resolve_import_path(
                source_file.file_path,
                import_path,
                file_map
            )

            if not target_file:
                continue

            relationship_exists = (
                db.query(CodeRelationship)
                .filter(
                    CodeRelationship.project_id == project_id,
                    CodeRelationship.source_file_id == source_file.id,
                    CodeRelationship.target_file_id == target_file.id,
                    CodeRelationship.relationship_type == "imports"
                )
                .first()
            )

            if relationship_exists:
                continue

            relationships.append(
                CodeRelationship(
                    project_id=project_id,
                    source_file_id=source_file.id,
                    target_file_id=target_file.id,
                    relationship_type="imports"
                )
            )

    if relationships:
        db.add_all(relationships)


# =========================================================
# Add one code file
# =========================================================

@router.post("/")
def create_code_file(
    file_data: CodeFileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = (
        db.query(Project)
        .filter(
            Project.id == file_data.project_id,
            Project.user_id == current_user.id
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    normalized_file_path = file_data.file_path.strip().replace("\\", "/")

    if not normalized_file_path:
        raise HTTPException(
            status_code=400,
            detail="File path cannot be empty"
        )

    if not is_safe_zip_path(normalized_file_path):
        raise HTTPException(
            status_code=400,
            detail="Invalid file path"
        )

    if normalized_file_path.startswith("./"):
        normalized_file_path = normalized_file_path[2:]

    duplicate_file = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id == file_data.project_id,
            CodeFile.file_path == normalized_file_path
        )
        .first()
    )

    if duplicate_file:
        raise HTTPException(
            status_code=409,
            detail="A file with this path already exists in this project"
        )

    if len(file_data.content.encode("utf-8")) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 2 MB."
        )

    try:
        code_file = CodeFile(
            project_id=file_data.project_id,
            file_path=normalized_file_path,
            content=file_data.content
        )

        db.add(code_file)
        db.flush()

        chunks = split_code_into_chunks(
            file_data.content
        )

        # Create embeddings in small batches to reduce Gemini API requests.
        BATCH_SIZE = 10

        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[
                batch_start:batch_start + BATCH_SIZE
            ]

            embeddings = create_embeddings(
                [chunk["content"] for chunk in batch]
            )

            for chunk, embedding in zip(
                batch,
                embeddings
            ):
                code_chunk = CodeChunk(
                    project_id=file_data.project_id,
                    file_id=code_file.id,
                    content=chunk["content"],
                    chunk_index=chunk["chunk_index"],
                    start_line=chunk["start_line"],
                    end_line=chunk["end_line"],
                    embedding=embedding,
                    embedding_model=EMBEDDING_MODEL
                )

                db.add(code_chunk)

        db.commit()
        db.refresh(code_file)

        return {
            "id": code_file.id,
            "project_id": code_file.project_id,
            "file_path": code_file.file_path,
            "content": code_file.content,
            "chunks_created": len(chunks),
            "embedding_model": EMBEDDING_MODEL,
            "created_at": code_file.created_at
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not process code file: {str(error)}"
        )


# =========================================================
# Upload complete project ZIP
# =========================================================

def process_zip_data(
    project_id: int,
    zip_data: bytes,
    db: Session
):
    """
    Validate and index ZIP data into an existing project.

    This function is shared by normal ZIP uploads and GitHub imports.
    """

    if len(zip_data) > MAX_ZIP_SIZE:
        raise HTTPException(
            status_code=413,
            detail="ZIP file is too large. Maximum size is 25 MB."
        )

    try:
        # -----------------------------------------------------
        # Validate ZIP before changing the database
        # -----------------------------------------------------

        try:
            zip_file = ZipFile(BytesIO(zip_data))
        except BadZipFile:
            raise HTTPException(
                status_code=400,
                detail="Invalid or corrupted ZIP file."
            )

        members = zip_file.infolist()

        if len(members) > MAX_FILES:
            zip_file.close()
            raise HTTPException(
                status_code=413,
                detail=f"ZIP contains too many files. Maximum is {MAX_FILES}."
            )

        total_uncompressed_size = 0

        for zip_info in members:
            file_path = zip_info.filename.replace("\\", "/")

            # Skip directory entries.
            if zip_info.is_dir():
                continue

            # ZIP path traversal protection.
            if not is_safe_zip_path(file_path):
                zip_file.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsafe file path in ZIP: {zip_info.filename}"
                )

            # Reject symbolic links.
            unix_mode = (zip_info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                zip_file.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"Symbolic links are not allowed: {file_path}"
                )

            if zip_info.file_size > MAX_FILE_SIZE:
                zip_file.close()
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"File '{file_path}' is too large. "
                        "Maximum size is 2 MB."
                    )
                )

            total_uncompressed_size += zip_info.file_size

            if total_uncompressed_size > MAX_UNCOMPRESSED_SIZE:
                zip_file.close()
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "ZIP expands to too much data. "
                        "Maximum uncompressed size is 50 MB."
                    )
                )

        # -----------------------------------------------------
        # Delete old project data only AFTER validation
        # -----------------------------------------------------

        db.query(CodeRelationship).filter(
            CodeRelationship.project_id == project_id
        ).delete(
            synchronize_session=False
        )

        db.query(CodeChunk).filter(
            CodeChunk.project_id == project_id
        ).delete(
            synchronize_session=False
        )

        db.query(CodeFile).filter(
            CodeFile.project_id == project_id
        ).delete(
            synchronize_session=False
        )

        db.flush()

        files_processed = 0
        chunks_created = 0
        processed_paths = set()
        saved_files = []

        # -----------------------------------------------------
        # Folders/files to skip
        # -----------------------------------------------------

        skip_folders = [
            "node_modules/",
            ".git/",
            "__pycache__/",
            ".venv/",
            "venv/",
            "dist/",
            "build/",
            ".next/",
            ".vite/"
        ]

        skip_files = [
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml"
        ]

        # -----------------------------------------------------
        # Process ZIP
        # -----------------------------------------------------

        for zip_info in members:
            if zip_info.is_dir():
                continue

            file_path = zip_info.filename.replace("\\", "/")

            if any(
                folder in file_path
                for folder in skip_folders
            ):
                continue

            file_name = file_path.split("/")[-1]

            if file_name in skip_files:
                continue

            if file_path in processed_paths:
                continue

            processed_paths.add(file_path)

            try:
                content = zip_file.read(
                    zip_info
                ).decode("utf-8")
            except (
                UnicodeDecodeError,
                KeyError
            ):
                continue

            if not content.strip():
                continue

            code_file = CodeFile(
                project_id=project_id,
                file_path=file_path,
                content=content
            )

            db.add(code_file)
            db.flush()

            chunks = split_code_into_chunks(
                content
            )

            # Create embeddings in batches to reduce Gemini API requests.
            BATCH_SIZE = 10

            for batch_start in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[
                    batch_start:batch_start + BATCH_SIZE
                ]

                print(
                    f"Embedding {file_path}: "
                    f"chunks {batch_start + 1}-"
                    f"{batch_start + len(batch)}"
                )

                embeddings = create_embeddings(
                    [chunk["content"] for chunk in batch]
                )

                for chunk, embedding in zip(
                    batch,
                    embeddings
                ):
                    code_chunk = CodeChunk(
                        project_id=project_id,
                        file_id=code_file.id,
                        content=chunk["content"],
                        chunk_index=chunk["chunk_index"],
                        start_line=chunk["start_line"],
                        end_line=chunk["end_line"],
                        embedding=embedding,
                        embedding_model=EMBEDDING_MODEL
                    )

                    db.add(code_chunk)
                    chunks_created += 1

            saved_files.append(code_file)
            files_processed += 1

        zip_file.close()

        # -----------------------------------------------------
        # Rebuild code relationships
        # -----------------------------------------------------

        create_relationships(
            db=db,
            project_id=project_id,
            code_files=saved_files
        )

        # -----------------------------------------------------
        # Save everything
        # -----------------------------------------------------

        db.commit()

        return {
            "message": "Project uploaded and indexed successfully",
            "project_id": project_id,
            "files_processed": files_processed,
            "chunks_created": chunks_created,
            "embedding_model": EMBEDDING_MODEL
        }

    except HTTPException:
        db.rollback()
        raise

    except BadZipFile:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted ZIP file."
        )

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not process ZIP file: {str(error)}"
        )


@router.post("/upload-zip/{project_id}")
async def upload_project_zip(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a ZIP file"
        )

    try:
        zip_data = await file.read()

        return process_zip_data(
            project_id=project_id,
            zip_data=zip_data,
            db=db
        )

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not process ZIP file: {str(error)}"
        )


# =========================================================
# Get project file metadata
# =========================================================

@router.get("/project/{project_id}")
def get_project_files(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    files = (
        db.query(CodeFile)
        .filter(CodeFile.project_id == project_id)
        .order_by(CodeFile.file_path)
        .all()
    )

    # Do not send full source code when loading the project tree.
    return [
        {
            "id": code_file.id,
            "project_id": code_file.project_id,
            "file_path": code_file.file_path,
            "created_at": code_file.created_at
        }
        for code_file in files
    ]


# =========================================================
# Get one file's source code
# =========================================================

@router.get("/project/{project_id}/file/{file_id}")
def get_project_file(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    code_file = (
        db.query(CodeFile)
        .filter(
            CodeFile.id == file_id,
            CodeFile.project_id == project_id
        )
        .first()
    )

    if not code_file:
        raise HTTPException(
            status_code=404,
            detail="Code file not found"
        )

    return {
        "id": code_file.id,
        "project_id": code_file.project_id,
        "file_path": code_file.file_path,
        "content": code_file.content,
        "created_at": code_file.created_at
    }
