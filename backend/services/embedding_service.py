from sentence_transformers import SentenceTransformer


# =========================================================
# Local Embedding Model
# =========================================================

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# all-MiniLM-L6-v2 produces 384-dimensional embeddings.
EMBEDDING_DIMENSION = 384

model = SentenceTransformer(EMBEDDING_MODEL)


# =========================================================
# Create one embedding
# =========================================================

def create_embedding(text: str) -> list[float]:
    """
    Create a local embedding for a single text.
    Used for individual search queries.
    """

    if not text or not text.strip():
        raise ValueError("Cannot create embedding for empty text.")

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()


# =========================================================
# Create multiple embeddings
# =========================================================

def create_embeddings(
    texts: list[str]
) -> list[list[float]]:
    """
    Create local embeddings for multiple texts.

    No external API is used.
    """

    if not texts:
        return []

    cleaned_texts = []

    for text in texts:

        if not text or not text.strip():
            raise ValueError(
                "Cannot create embedding for empty text."
            )

        cleaned_texts.append(text)

    embeddings = model.encode(
        cleaned_texts,
        normalize_embeddings=True
    )

    return [
        embedding.tolist()
        for embedding in embeddings
    ]