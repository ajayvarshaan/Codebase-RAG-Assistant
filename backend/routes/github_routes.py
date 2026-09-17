import io
import traceback
import zipfile
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.database import get_db

from models.project import Project
from models.code_file import CodeFile
from models.code_chunk import CodeChunk
from models.code_relationship import CodeRelationship
from models.user import User

from routes.code_file_routes import (
    process_zip_data,
    is_safe_zip_path,
    create_relationships,
    MAX_ZIP_SIZE,
    MAX_UNCOMPRESSED_SIZE,
    MAX_FILES,
    MAX_FILE_SIZE
)

from services.auth_dependency import get_current_user

from services.github_service import (
    download_github_repository
)

from services.github_diff_service import (
    detect_changed_files
)

from services.chunking import (
    split_code_into_chunks
)

from services.embedding_service import (
    EMBEDDING_MODEL,
    create_embeddings
)


router = APIRouter(
    prefix="/github",
    tags=["GitHub"]
)


# =========================================================
# FILES TO SKIP
# =========================================================

SKIP_FOLDERS = [
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

SKIP_FILES = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml"
]


# =========================================================
# NORMALIZE GITHUB PATH
# =========================================================

def normalize_github_path(
    path: str
) -> str | None:

    normalized = (
        path
        .replace("\\", "/")
        .lstrip("/")
    )

    if not normalized:
        return None

    if ".." in normalized.split("/"):
        return None

    # GitHub ZIP normally contains:
    #
    # repository-commit/
    #     src/
    #     package.json
    #
    # The first directory is removed later.
    return normalized


# =========================================================
# CHECK WHETHER FILE SHOULD BE INDEXED
# =========================================================

def should_index_file(
    file_path: str
) -> bool:

    normalized = (
        file_path
        .replace("\\", "/")
        .lstrip("/")
    )

    for folder in SKIP_FOLDERS:

        if folder in normalized:
            return False

    file_name = (
        normalized
        .split("/")[-1]
    )

    if file_name in SKIP_FILES:
        return False

    return True


# =========================================================
# EXTRACT GITHUB FILES
# =========================================================

def extract_github_files(
    zip_data: bytes
):
    """
    Extract indexable text files from a GitHub ZIP.

    Returns:

        [
            {
                "path": "src/main.py",
                "content": "..."
            }
        ]
    """

    files = []

    if len(zip_data) > MAX_ZIP_SIZE:

        raise ValueError(
            "ZIP file is too large. "
            "Maximum size is 25 MB."
        )

    try:

        archive = zipfile.ZipFile(
            io.BytesIO(zip_data)
        )

    except zipfile.BadZipFile:

        raise ValueError(
            "Invalid or corrupted GitHub ZIP."
        )

    try:

        members = [
            member
            for member in archive.infolist()
            if not member.is_dir()
        ]

        if len(members) > MAX_FILES:

            raise ValueError(
                "ZIP contains too many files. "
                f"Maximum is {MAX_FILES}."
            )

        total_uncompressed_size = 0

        for member in members:

            raw_path = (
                member.filename
                .replace("\\", "/")
            )

            if not is_safe_zip_path(
                raw_path
            ):

                raise ValueError(
                    "Unsafe file path in GitHub ZIP: "
                    f"{member.filename}"
                )

            # Reject symbolic links.
            unix_mode = (
                member.external_attr
                >> 16
            ) & 0o170000

            if unix_mode == 0o120000:

                raise ValueError(
                    "Symbolic links are not allowed: "
                    f"{raw_path}"
                )

            if member.file_size > MAX_FILE_SIZE:

                raise ValueError(
                    f"File '{raw_path}' is too large. "
                    "Maximum size is 2 MB."
                )

            total_uncompressed_size += (
                member.file_size
            )

            if (
                total_uncompressed_size
                > MAX_UNCOMPRESSED_SIZE
            ):

                raise ValueError(
                    "ZIP expands to too much data. "
                    "Maximum uncompressed size "
                    "is 50 MB."
                )

        if not members:
            return files

        # -----------------------------------------------------
        # GitHub ZIP normally has one root directory.
        # -----------------------------------------------------

        first_parts = [
            member.filename
            .replace("\\", "/")
            .split("/")[0]
            for member in members
        ]

        common_root = (
            first_parts[0]
            if all(
                part == first_parts[0]
                for part in first_parts
            )
            else ""
        )

        processed_paths = set()

        for member in members:

            path = (
                member.filename
                .replace("\\", "/")
                .lstrip("/")
            )

            if (
                common_root
                and path.startswith(
                    common_root + "/"
                )
            ):

                path = path[
                    len(common_root) + 1:
                ]

            if not path:
                continue

            if not is_safe_zip_path(
                path
            ):
                continue

            if not should_index_file(
                path
            ):
                continue

            if path in processed_paths:
                continue

            processed_paths.add(path)

            try:

                content = archive.read(
                    member
                ).decode("utf-8")

            except (
                UnicodeDecodeError,
                RuntimeError,
                OSError,
                KeyError
            ):

                # Ignore binary files and files
                # that cannot be decoded as UTF-8.
                continue

            if not content.strip():
                continue

            files.append(
                {
                    "path": path,
                    "content": content
                }
            )

    finally:

        archive.close()

    return files


# =========================================================
# REQUEST MODEL
# =========================================================

class GitHubImportRequest(
    BaseModel
):

    project_id: int = Field(
        gt=0,
        description=(
            "Project ID to import "
            "the repository into"
        )
    )

    github_url: str = Field(
        min_length=1,
        max_length=500,
        description=(
            "Public GitHub repository URL"
        )
    )


# =========================================================
# IMPORT GITHUB REPOSITORY
# =========================================================

@router.post("/import")
async def import_github_repository(
    request: GitHubImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    # -----------------------------------------------------
    # Check project ownership
    # -----------------------------------------------------

    project = (
        db.query(Project)
        .filter(
            Project.id
            == request.project_id,

            Project.user_id
            == current_user.id
        )
        .first()
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail=(
                "Project not found or "
                "you do not have access to it."
            )
        )

    try:

        # -------------------------------------------------
        # Download repository.
        # -------------------------------------------------

        github_result = (
            await download_github_repository(
                request.github_url
            )
        )

        # -------------------------------------------------
        # Initial import uses existing full ZIP
        # processing.
        # -------------------------------------------------

        result = process_zip_data(
            project_id=project.id,
            zip_data=github_result[
                "zip_data"
            ],
            db=db
        )

        # -------------------------------------------------
        # Save GitHub URL.
        # -------------------------------------------------

        project.github_url = (
            f"https://github.com/"
            f"{github_result['owner']}/"
            f"{github_result['repo']}"
        )

        # -------------------------------------------------
        # Save commit SHA.
        # -------------------------------------------------

        project.github_commit_sha = (
            github_result[
                "commit_sha"
            ]
        )

        project.github_previous_commit_sha = None

        db.commit()

        db.refresh(project)

        return {
            "message": (
                "GitHub repository "
                "imported successfully"
            ),
            "project_id": project.id,
            "repository": (
                github_result["repo"]
            ),
            "owner": (
                github_result["owner"]
            ),
            "default_branch": (
                github_result[
                    "default_branch"
                ]
            ),
            "github_url": (
                project.github_url
            ),
            "commit_sha": (
                project.github_commit_sha
            ),
            "files_processed": (
                result[
                    "files_processed"
                ]
            ),
            "chunks_created": (
                result[
                    "chunks_created"
                ]
            ),
            "embedding_model": (
                result[
                    "embedding_model"
                ]
            ),
            "reindexed": True
        }

    except HTTPException:
        raise

    except ValueError as error:

        db.rollback()

        error_message = str(error)

        print(
            "========== GITHUB IMPORT "
            "VALUE ERROR =========="
        )

        print(error_message)

        print(
            "================================"
        )

        if (
            "too many files"
            in error_message.lower()
        ):

            raise HTTPException(
                status_code=413,
                detail=error_message
            )

        if (
            "too large"
            in error_message.lower()
        ):

            raise HTTPException(
                status_code=413,
                detail=error_message
            )

        raise HTTPException(
            status_code=400,
            detail=error_message
        )

    except Exception as error:

        db.rollback()

        print(
            "\n========== GITHUB IMPORT "
            "ERROR =========="
        )

        print(
            f"Error: {str(error)}"
        )

        traceback.print_exc()

        print(
            "================================"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "GitHub import failed: "
                f"{str(error)}"
            )
        )


# =========================================================
# CREATE CHUNKS + EMBEDDINGS FOR ONE FILE
# =========================================================

def index_single_file(
    db: Session,
    project_id: int,
    code_file: CodeFile
) -> int:
    """
    Create chunks and local embeddings
    for one CodeFile.

    Returns:
        number of chunks created
    """

    chunks = split_code_into_chunks(
        code_file.content or ""
    )

    if not chunks:
        return 0

    BATCH_SIZE = 10

    chunks_created = 0

    for batch_start in range(
        0,
        len(chunks),
        BATCH_SIZE
    ):

        batch = chunks[
            batch_start:
            batch_start + BATCH_SIZE
        ]

        print(
            f"Embedding {code_file.file_path}: "
            f"chunks "
            f"{batch_start + 1}-"
            f"{batch_start + len(batch)}"
        )

        embeddings = create_embeddings(
            [
                chunk["content"]
                for chunk in batch
            ]
        )

        for (
            chunk,
            embedding
        ) in zip(
            batch,
            embeddings
        ):

            code_chunk = CodeChunk(
                project_id=project_id,
                file_id=code_file.id,
                content=chunk["content"],
                chunk_index=(
                    chunk["chunk_index"]
                ),
                start_line=(
                    chunk["start_line"]
                ),
                end_line=(
                    chunk["end_line"]
                ),
                embedding=embedding,
                embedding_model=(
                    EMBEDDING_MODEL
                )
            )

            db.add(code_chunk)

            chunks_created += 1

    return chunks_created


# =========================================================
# INCREMENTAL GITHUB UPDATE
# =========================================================

def apply_incremental_update(
    db: Session,
    project_id: int,
    old_code_files: list[CodeFile],
    new_files: list[dict],
    changed_files: dict
):
    """
    Update only added, modified and deleted files.

    Existing unchanged files are preserved.
    """

    added_paths = set(
        changed_files.get(
            "added",
            []
        )
    )

    modified_paths = set(
        changed_files.get(
            "modified",
            []
        )
    )

    deleted_paths = set(
        changed_files.get(
            "deleted",
            []
        )
    )

    changed_paths = (
        added_paths
        | modified_paths
    )

    # -----------------------------------------------------
    # Build maps.
    # -----------------------------------------------------

    old_file_map = {
        file.file_path: file
        for file in old_code_files
    }

    new_file_map = {
        file["path"]: file
        for file in new_files
    }

    # -----------------------------------------------------
    # 1. Delete relationships first.
    #
    # Relationships reference CodeFile IDs.
    # We rebuild them after the update.
    # -----------------------------------------------------

    db.query(
        CodeRelationship
    ).filter(
        CodeRelationship.project_id
        == project_id
    ).delete(
        synchronize_session=False
    )

    # -----------------------------------------------------
    # 2. Delete chunks for modified/deleted files.
    #
    # Modified files need fresh chunks.
    # Deleted files no longer need chunks.
    # -----------------------------------------------------

    files_requiring_chunk_delete = []

    for path in (
        modified_paths
        | deleted_paths
    ):

        old_file = old_file_map.get(
            path
        )

        if old_file:

            files_requiring_chunk_delete.append(
                old_file.id
            )

    if files_requiring_chunk_delete:

        db.query(
            CodeChunk
        ).filter(
            CodeChunk.file_id.in_(
                files_requiring_chunk_delete
            )
        ).delete(
            synchronize_session=False
        )

    # -----------------------------------------------------
    # 3. Delete removed CodeFile rows.
    # -----------------------------------------------------

    for path in deleted_paths:

        old_file = old_file_map.get(
            path
        )

        if not old_file:
            continue

        print(
            f"Deleting file: {path}"
        )

        db.delete(old_file)

    db.flush()

    # -----------------------------------------------------
    # 4. Update modified files.
    # -----------------------------------------------------

    chunks_created = 0

    modified_count = 0
    added_count = 0
    deleted_count = 0

    for path in modified_paths:

        new_file_data = (
            new_file_map.get(path)
        )

        old_file = (
            old_file_map.get(path)
        )

        if (
            not new_file_data
            or not old_file
        ):
            continue

        print(
            f"Updating file: {path}"
        )

        old_file.content = (
            new_file_data["content"]
        )

        chunks_created += (
            index_single_file(
                db=db,
                project_id=project_id,
                code_file=old_file
            )
        )

        modified_count += 1

    # -----------------------------------------------------
    # 5. Add new files.
    # -----------------------------------------------------

    for path in added_paths:

        new_file_data = (
            new_file_map.get(path)
        )

        if not new_file_data:
            continue

        print(
            f"Adding file: {path}"
        )

        code_file = CodeFile(
            project_id=project_id,
            file_path=path,
            content=new_file_data[
                "content"
            ]
        )

        db.add(code_file)

        db.flush()

        chunks_created += (
            index_single_file(
                db=db,
                project_id=project_id,
                code_file=code_file
            )
        )

        added_count += 1

    # -----------------------------------------------------
    # Count deleted files.
    # -----------------------------------------------------

    deleted_count = len(
        deleted_paths
    )

    db.flush()

    # -----------------------------------------------------
    # 6. Rebuild relationships.
    #
    # We preserve all unchanged files and use the
    # updated complete file list.
    # -----------------------------------------------------

    current_files = (
        db.query(CodeFile)
        .filter(
            CodeFile.project_id
            == project_id
        )
        .order_by(
            CodeFile.file_path
        )
        .all()
    )

    create_relationships(
        db=db,
        project_id=project_id,
        code_files=current_files
    )

    db.flush()

    return {
        "added_count": added_count,
        "modified_count": modified_count,
        "deleted_count": deleted_count,
        "chunks_created": chunks_created,
        "files_processed": (
            added_count
            + modified_count
        )
    }


# =========================================================
# RE-IMPORT / REFRESH GITHUB REPOSITORY
# =========================================================

@router.post(
    "/reimport/{project_id}"
)
async def reimport_github_repository(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    # -----------------------------------------------------
    # Check project ownership.
    # -----------------------------------------------------

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id
            == current_user.id
        )
        .first()
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail=(
                "Project not found or "
                "you do not have access to it."
            )
        )

    # -----------------------------------------------------
    # Check saved GitHub URL.
    # -----------------------------------------------------

    if not project.github_url:

        raise HTTPException(
            status_code=400,
            detail=(
                "This project does not have "
                "a saved GitHub repository."
            )
        )

    try:

        # -------------------------------------------------
        # Get latest GitHub repository.
        # -------------------------------------------------

        github_result = (
            await download_github_repository(
                project.github_url
            )
        )

        latest_commit_sha = (
            github_result[
                "commit_sha"
            ]
        )

        saved_commit_sha = (
            project.github_commit_sha
        )

        print(
            "\n========== GITHUB "
            "INCREMENTAL REFRESH =========="
        )

        print(
            f"Saved commit SHA:  "
            f"{saved_commit_sha}"
        )

        print(
            f"Latest commit SHA: "
            f"{latest_commit_sha}"
        )

        # -------------------------------------------------
        # Repository unchanged.
        # -------------------------------------------------

        if (
            saved_commit_sha
            and saved_commit_sha
            == latest_commit_sha
        ):

            print(
                "Repository is already "
                "up to date."
            )

            print(
                "================================"
            )

            return {
                "message": (
                    "GitHub repository is "
                    "already up to date"
                ),
                "project_id": project.id,
                "previous_commit_sha": (
                    saved_commit_sha
                ),
                "repository": (
                    github_result["repo"]
                ),
                "owner": (
                    github_result["owner"]
                ),
                "default_branch": (
                    github_result[
                        "default_branch"
                    ]
                ),
                "github_url": (
                    project.github_url
                ),
                "commit_sha": (
                    latest_commit_sha
                ),
                "changed_files": {
                    "added": [],
                    "modified": [],
                    "deleted": []
                },
                "files_processed": 0,
                "chunks_created": 0,
                "embedding_model": (
                    EMBEDDING_MODEL
                ),
                "reindexed": False
            }

        # -------------------------------------------------
        # Load current indexed files BEFORE modifying DB.
        # -------------------------------------------------

        old_code_files = (
            db.query(CodeFile)
            .filter(
                CodeFile.project_id
                == project.id
            )
            .all()
        )

        # -------------------------------------------------
        # Extract latest GitHub files.
        # -------------------------------------------------

        new_files = extract_github_files(
            github_result["zip_data"]
        )

        # -------------------------------------------------
        # Build old file representation.
        # -------------------------------------------------

        old_files = [
            {
                "path": code_file.file_path,
                "content": code_file.content
            }
            for code_file in old_code_files
        ]

        # -------------------------------------------------
        # Detect changes.
        # -------------------------------------------------

        changed_files = (
            detect_changed_files(
                old_files,
                new_files
            )
        )

        added_count = len(
            changed_files["added"]
        )

        modified_count = len(
            changed_files["modified"]
        )

        deleted_count = len(
            changed_files["deleted"]
        )

        print(
            "\nChanges detected:"
        )

        print(
            f"Added:    {added_count}"
        )

        print(
            f"Modified: {modified_count}"
        )

        print(
            f"Deleted:  {deleted_count}"
        )

        # -------------------------------------------------
        # Safety check.
        #
        # If the GitHub archive contains no files but the
        # project previously had files, don't accidentally
        # delete the entire index.
        # -------------------------------------------------

        if (
            not new_files
            and old_code_files
        ):

            raise ValueError(
                "GitHub returned no indexable files. "
                "The existing project index was "
                "not changed."
            )

        # -------------------------------------------------
        # No file content changes despite different commit.
        #
        # This can happen for commits affecting ignored files.
        # -------------------------------------------------

        if (
            not changed_files["added"]
            and not changed_files["modified"]
            and not changed_files["deleted"]
        ):

            project.github_previous_commit_sha = (
                saved_commit_sha
            )

            project.github_commit_sha = (
                latest_commit_sha
            )

            project.github_url = (
                f"https://github.com/"
                f"{github_result['owner']}/"
                f"{github_result['repo']}"
            )

            db.commit()

            db.refresh(project)

            print(
                "Commit changed, but no indexed "
                "files changed."
            )

            return {
                "message": (
                    "GitHub commit updated. "
                    "No indexed files changed."
                ),
                "project_id": project.id,
                "previous_commit_sha": (
                    saved_commit_sha
                ),
                "repository": (
                    github_result["repo"]
                ),
                "owner": (
                    github_result["owner"]
                ),
                "default_branch": (
                    github_result[
                        "default_branch"
                    ]
                ),
                "github_url": (
                    project.github_url
                ),
                "commit_sha": (
                    latest_commit_sha
                ),
                "changed_files": (
                    changed_files
                ),
                "files_processed": 0,
                "chunks_created": 0,
                "embedding_model": (
                    EMBEDDING_MODEL
                ),
                "reindexed": False
            }

        # -------------------------------------------------
        # Apply incremental update.
        # -------------------------------------------------

        result = apply_incremental_update(
            db=db,
            project_id=project.id,
            old_code_files=old_code_files,
            new_files=new_files,
            changed_files=changed_files
        )

        # -------------------------------------------------
        # Save previous commit SHA.
        # -------------------------------------------------

        project.github_previous_commit_sha = (
            saved_commit_sha
        )

        # -------------------------------------------------
        # Save new commit SHA.
        # -------------------------------------------------

        project.github_commit_sha = (
            latest_commit_sha
        )

        # -------------------------------------------------
        # Save normalized GitHub URL.
        # -------------------------------------------------

        project.github_url = (
            f"https://github.com/"
            f"{github_result['owner']}/"
            f"{github_result['repo']}"
        )

        # -------------------------------------------------
        # Commit entire incremental update.
        # -------------------------------------------------

        db.commit()

        db.refresh(project)

        print(
            "\nIncremental GitHub indexing "
            "completed successfully."
        )

        print(
            f"Files reprocessed: "
            f"{result['files_processed']}"
        )

        print(
            f"Chunks recreated: "
            f"{result['chunks_created']}"
        )

        print(
            "==========================================\n"
        )

        return {
            "message": (
                "New GitHub commit detected. "
                "Only changed files were "
                "incrementally re-indexed."
            ),
            "project_id": project.id,
            "previous_commit_sha": (
                saved_commit_sha
            ),
            "repository": (
                github_result["repo"]
            ),
            "owner": (
                github_result["owner"]
            ),
            "default_branch": (
                github_result[
                    "default_branch"
                ]
            ),
            "github_url": (
                project.github_url
            ),
            "commit_sha": (
                project.github_commit_sha
            ),
            "changed_files": (
                changed_files
            ),
            "files_processed": (
                result[
                    "files_processed"
                ]
            ),
            "chunks_created": (
                result[
                    "chunks_created"
                ]
            ),
            "embedding_model": (
                EMBEDDING_MODEL
            ),
            "reindexed": True
        }

    except HTTPException:

        db.rollback()

        raise

    except ValueError as error:

        db.rollback()

        error_message = str(error)

        print(
            "\n========== GITHUB REFRESH "
            "VALUE ERROR =========="
        )

        print(error_message)

        print(
            "================================"
        )

        if (
            "too many files"
            in error_message.lower()
        ):

            raise HTTPException(
                status_code=413,
                detail=error_message
            )

        if (
            "too large"
            in error_message.lower()
        ):

            raise HTTPException(
                status_code=413,
                detail=error_message
            )

        raise HTTPException(
            status_code=400,
            detail=error_message
        )

    except Exception as error:

        db.rollback()

        print(
            "\n========== GITHUB REFRESH "
            "ERROR =========="
        )

        print(
            f"Error: {str(error)}"
        )

        traceback.print_exc()

        print(
            "================================"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "GitHub refresh failed: "
                f"{str(error)}"
            )
        )