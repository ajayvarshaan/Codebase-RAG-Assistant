from sqlalchemy.orm import Session

from models.code_chunk import CodeChunk
from services.embedding_service import create_embedding


def search_similar_chunks(
    db: Session,
    query: str,
    project_id: int,
    top_k: int = 3
):
    # Create embedding for the user's question
    query_embedding = create_embedding(query)

    # Calculate cosine distance
    distance = CodeChunk.embedding.cosine_distance(
        query_embedding
    )

    # Search only inside the selected project
    results = (
        db.query(CodeChunk, distance.label("distance"))
        .filter(
            CodeChunk.project_id == project_id,
            CodeChunk.embedding.isnot(None)
        )
        .order_by(distance)
        .limit(top_k)
        .all()
    )

    # Keep only reasonably relevant chunks
    relevant_chunks = []

    for chunk, chunk_distance in results:

        # Cosine distance:
        # 0 = very similar
        # 1 = not very similar
        # We allow distances up to 0.5
        if chunk_distance <= 0.5:
            relevant_chunks.append(chunk)

    return relevant_chunks