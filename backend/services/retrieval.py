import re

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models.code_chunk import CodeChunk
from models.code_file import CodeFile
from services.embedding_service import create_embedding


# ============================================================
# SEARCH SETTINGS
# ============================================================

CANDIDATE_COUNT = 15

# Reciprocal Rank Fusion constant.
RRF_K = 60


# ============================================================
# CODE-AWARE HELPERS
# ============================================================

SOURCE_EXTENSIONS = (
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".dart",
)


def extract_code_terms(query: str) -> list[str]:
    """
    Extract useful code-related terms from the user's question.

    Examples:

        "Where is hello.py used?"
        -> ["hello.py"]

        "Where is generate_answer() used?"
        -> ["generate_answer"]

        "Explain UserService class"
        -> ["UserService"]

        "What does `loginUser` do?"
        -> ["loginUser"]
    """

    terms = set()

    # --------------------------------------------------------
    # 1. Backtick terms
    # --------------------------------------------------------

    backtick_terms = re.findall(
        r"`([^`]+)`",
        query
    )

    for term in backtick_terms:
        term = term.strip()

        if term:
            terms.add(term)


    # --------------------------------------------------------
    # 2. Function / method names
    #
    # Example:
    # generate_answer()
    # loginUser()
    # authenticate_user()
    # --------------------------------------------------------

    function_terms = re.findall(
        r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(",
        query
    )

    for term in function_terms:
        term = term.rstrip("(").strip()

        if len(term) >= 2:
            terms.add(term)


    # --------------------------------------------------------
    # 3. File names
    #
    # Example:
    # hello.py
    # auth_service.py
    # App.tsx
    # User.java
    # --------------------------------------------------------

    file_terms = re.findall(
        r"\b[A-Za-z0-9_.-]+\.(?:py|js|jsx|ts|tsx|java|c|cpp|cs|go|rs|php|rb|swift|kt|dart|json|yaml|yml|md|sql)\b",
        query,
        re.IGNORECASE
    )

    for term in file_terms:
        terms.add(term)


    # --------------------------------------------------------
    # 4. Identifier-style words
    #
    # Detect:
    # snake_case
    # camelCase
    # PascalCase
    # CONSTANT_NAME
    # --------------------------------------------------------

    identifier_terms = re.findall(
        r"\b[A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]+\b",
        query
    )

    for term in identifier_terms:
        if len(term) >= 3:
            terms.add(term)


    # CamelCase / PascalCase
    camel_case_terms = re.findall(
        r"\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b",
        query
    )

    for term in camel_case_terms:
        terms.add(term)


    return list(terms)


def is_source_file(file_path: str) -> bool:
    """
    Check whether a file is an actual source-code file.
    """

    return file_path.lower().endswith(
        SOURCE_EXTENSIONS
    )


def is_code_question(query: str) -> bool:
    """
    Detect whether the user is asking about code structure.
    """

    query_lower = query.lower()

    code_words = [
        "code",
        "python",
        "javascript",
        "typescript",
        "java",
        "function",
        "method",
        "class",
        "variable",
        "import",
        "route",
        "component",
        "implementation",
        "defined",
        "definition",
        "used",
        "usage",
        "called",
        "calls",
        "calling",
        "main",
        "source",
        "file",
        "dependency",
        "dependencies",
    ]

    return any(
        word in query_lower
        for word in code_words
    )


def is_structure_question(query: str) -> bool:
    """
    Detect questions about code structure/usages.
    """

    query_lower = query.lower()

    structure_words = [
        "where is",
        "where are",
        "where does",
        "where do",
        "used",
        "usage",
        "called",
        "calls",
        "calling",
        "defined",
        "definition",
        "implementation",
        "import",
        "dependency",
        "dependencies",
    ]

    return any(
        phrase in query_lower
        for phrase in structure_words
    )


# ============================================================
# MAIN RETRIEVAL FUNCTION
# ============================================================

def search_similar_chunks(
    db: Session,
    query: str,
    project_id: int,
    top_k: int = 3
):
    """
    Hybrid + code-aware retrieval.

    Search methods:

    1. Semantic vector search
    2. PostgreSQL keyword search
    3. Exact code-symbol search
    4. Code/file ranking
    5. Reciprocal Rank Fusion

    Returns the best CodeChunk objects.
    """

    query = query.strip()

    if not query:
        return []


    # ========================================================
    # 1. SEMANTIC SEARCH
    # ========================================================

    query_embedding = create_embedding(query)

    distance = CodeChunk.embedding.cosine_distance(
        query_embedding
    )

    semantic_results = (
        db.query(
            CodeChunk,
            CodeFile.file_path,
            distance.label("distance")
        )
        .join(
            CodeFile,
            CodeChunk.file_id == CodeFile.id
        )
        .filter(
            CodeChunk.project_id == project_id,
            CodeChunk.embedding.isnot(None)
        )
        .order_by(distance)
        .limit(CANDIDATE_COUNT)
        .all()
    )


    # ========================================================
    # 2. POSTGRESQL KEYWORD SEARCH
    # ========================================================

    search_vector = func.to_tsvector(
        "simple",
        CodeChunk.content
    )

    search_query = func.plainto_tsquery(
        "simple",
        query
    )

    keyword_rank = func.ts_rank_cd(
        search_vector,
        search_query
    )

    keyword_results = (
        db.query(
            CodeChunk,
            CodeFile.file_path,
            keyword_rank.label("rank")
        )
        .join(
            CodeFile,
            CodeChunk.file_id == CodeFile.id
        )
        .filter(
            CodeChunk.project_id == project_id,
            search_vector.op("@@")(search_query)
        )
        .order_by(
            keyword_rank.desc()
        )
        .limit(CANDIDATE_COUNT)
        .all()
    )


    # ========================================================
    # 3. EXACT CODE / FILE SEARCH
    # ========================================================

    code_terms = extract_code_terms(query)

    exact_results = []

    if code_terms:

        exact_conditions = []

        for term in code_terms:

            exact_conditions.append(
                CodeChunk.content.ilike(
                    f"%{term}%"
                )
            )

            exact_conditions.append(
                CodeFile.file_path.ilike(
                    f"%{term}%"
                )
            )

        exact_results = (
            db.query(
                CodeChunk,
                CodeFile.file_path
            )
            .join(
                CodeFile,
                CodeChunk.file_id == CodeFile.id
            )
            .filter(
                CodeChunk.project_id == project_id,
                or_(*exact_conditions)
            )
            .limit(CANDIDATE_COUNT)
            .all()
        )


    # ========================================================
    # 4. RRF SCORE STORAGE
    # ========================================================

    scores = {}

    chunks = {}

    file_paths = {}


    # ========================================================
    # 5. ADD SEMANTIC RANKING
    # ========================================================

    for rank, (
        chunk,
        file_path,
        chunk_distance
    ) in enumerate(
        semantic_results,
        start=1
    ):

        chunk_id = chunk.id

        chunks[chunk_id] = chunk

        file_paths[chunk_id] = file_path

        scores.setdefault(
            chunk_id,
            0.0
        )

        scores[chunk_id] += (
            1.0 / (RRF_K + rank)
        )


    # ========================================================
    # 6. ADD KEYWORD RANKING
    # ========================================================

    for rank, (
        chunk,
        file_path,
        text_rank
    ) in enumerate(
        keyword_results,
        start=1
    ):

        chunk_id = chunk.id

        chunks[chunk_id] = chunk

        file_paths[chunk_id] = file_path

        scores.setdefault(
            chunk_id,
            0.0
        )

        scores[chunk_id] += (
            1.0 / (RRF_K + rank)
        )


    # ========================================================
    # 7. ADD EXACT CODE RANKING
    # ========================================================

    for rank, (
        chunk,
        file_path
    ) in enumerate(
        exact_results,
        start=1
    ):

        chunk_id = chunk.id

        chunks[chunk_id] = chunk

        file_paths[chunk_id] = file_path

        scores.setdefault(
            chunk_id,
            0.0
        )

        # Exact symbol/file matches receive
        # a stronger contribution.
        scores[chunk_id] += (
            2.0 / (RRF_K + rank)
        )


    # ========================================================
    # 8. FILE TYPE + CODE STRUCTURE BOOSTS
    # ========================================================

    query_lower = query.lower()

    code_question = is_code_question(query)

    structure_question = is_structure_question(query)


    for chunk_id in list(scores.keys()):

        file_path = file_paths[chunk_id]

        path_lower = file_path.lower()

        content = chunks[chunk_id].content

        content_lower = content.lower()


        # ----------------------------------------------------
        # README boost
        # ----------------------------------------------------

        if "readme" in path_lower:
            scores[chunk_id] += 0.003


        # ----------------------------------------------------
        # Source-code boost
        # ----------------------------------------------------

        if is_source_file(file_path):

            scores[chunk_id] += 0.002


        # ----------------------------------------------------
        # Reduce IDE configuration files
        # ----------------------------------------------------

        if (
            ".idea/" in path_lower
            or ".vscode/" in path_lower
        ):
            scores[chunk_id] -= 0.003


        # ----------------------------------------------------
        # Code question → source files
        # ----------------------------------------------------

        if code_question:

            if is_source_file(file_path):
                scores[chunk_id] += 0.003


        # ----------------------------------------------------
        # Structure question
        # ----------------------------------------------------

        if structure_question:

            # Function definitions
            if re.search(
                r"\b(def|function)\s+[A-Za-z_][A-Za-z0-9_]*",
                content
            ):
                scores[chunk_id] += 0.004


            # Python classes
            if re.search(
                r"\bclass\s+[A-Za-z_][A-Za-z0-9_]*",
                content
            ):
                scores[chunk_id] += 0.004


            # JavaScript / TypeScript functions
            if re.search(
                r"\b(?:const|let|var)\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:async\s*)?\(",
                content
            ):
                scores[chunk_id] += 0.003


            # Imports
            if (
                "import " in content_lower
                or "from " in content_lower
                or "require(" in content_lower
            ):
                scores[chunk_id] += 0.002


            # Function calls
            if re.search(
                r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(",
                content
            ):
                scores[chunk_id] += 0.002


    # ========================================================
    # 9. EXACT SYMBOL BOOST
    # ========================================================

    for term in code_terms:

        term_lower = term.lower()

        for chunk_id in list(scores.keys()):

            content_lower = (
                chunks[chunk_id]
                .content
                .lower()
            )

            path_lower = (
                file_paths[chunk_id]
                .lower()
            )

            # Exact term in source code
            if term_lower in content_lower:

                scores[chunk_id] += 0.006


            # Exact term in file path
            if term_lower in path_lower:

                scores[chunk_id] += 0.004


    # ========================================================
    # 10. TOKEN MATCH BOOST
    # ========================================================

    query_words = [
        word.strip(
            ".,!?()[]{}\"'"
        ).lower()
        for word in query.split()
    ]

    query_words = [
        word
        for word in query_words
        if len(word) >= 3
    ]


    for chunk_id in list(scores.keys()):

        content_lower = (
            chunks[chunk_id]
            .content
            .lower()
        )

        matching_words = 0

        for word in query_words:

            if word in content_lower:
                matching_words += 1


        if matching_words:

            scores[chunk_id] += (
                0.001 * matching_words
            )


    # ========================================================
    # 11. FINAL RANKING
    # ========================================================

    ranked_chunks = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )


    # ========================================================
    # 12. RETURN TOP RESULTS
    # ========================================================

    return [
        chunks[chunk_id]
        for chunk_id, _ in ranked_chunks[:top_k]
    ]