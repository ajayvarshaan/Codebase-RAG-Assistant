import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "gemini-embedding-2"


if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from the .env file")


client = genai.Client(api_key=GEMINI_API_KEY)


def create_embedding(text: str) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=1536
        )
    )

    return response.embeddings[0].values