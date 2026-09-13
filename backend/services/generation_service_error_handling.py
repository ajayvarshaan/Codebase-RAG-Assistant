import os

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GENERATION_MODEL = "gemini-3.6-flash"


if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in the .env file")


client = genai.Client(api_key=GEMINI_API_KEY)


def generate_answer(
    question: str,
    context: str,
    conversation_history: str = ""
):
    prompt = f"""
You are an AI assistant that helps developers understand and work with codebases.

Use only the provided code context when answering.
Do not invent files, functions, dependencies, or behavior that are not supported
by the provided context.

Conversation history:
{conversation_history}

Code context:
{context}

User question:
{question}

Give a clear, practical answer. Use Markdown when useful.
"""

    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt
        )

        return response.text or "The AI returned an empty response."

    except Exception as e:
        error_text = str(e)
        status_code = getattr(e, "status_code", None)

        # Gemini quota / rate-limit error
        if (
            status_code == 429
            or "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "generate_content_free_tier_requests" in error_text
            or "quota exceeded" in error_text.lower()
        ):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API quota has been exceeded. "
                    "Please wait for the quota to reset or check your "
                    "Gemini API project billing and usage limits."
                )
            )

        # Gemini authentication / API key error
        if (
            status_code in (401, 403)
            or "API key" in error_text
            or "UNAUTHENTICATED" in error_text
            or "PERMISSION_DENIED" in error_text
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "Gemini API authentication failed. "
                    "Please check the GEMINI_API_KEY in the backend .env file."
                )
            )

        # Other Gemini/API errors
        raise HTTPException(
            status_code=502,
            detail=(
                "The Gemini AI service could not complete the request. "
                "Please try again later."
            )
        )
