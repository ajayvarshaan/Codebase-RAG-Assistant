import os

from google import genai
from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=GEMINI_API_KEY
)

GENERATION_MODEL = "gemini-3.6-flash"


def generate_answer(
    question: str,
    context: str,
    conversation_history: str = ""
):

    prompt = f"""
You are an AI assistant that answers questions about a software codebase.

Use ONLY the provided code context and conversation history.

Do not invent code, files, functions, or behavior that is not supported
by the provided context.

If the answer cannot be determined from the provided context,
clearly say that the information is not available.

CONVERSATION HISTORY:
{conversation_history}

CURRENT QUESTION:
{question}

CODE CONTEXT:
{context}

Answer the current question clearly and directly.

If the user asks a follow-up question such as:
- "What does it do?"
- "How does it work?"
- "Where is it used?"
- "Explain that"

use the conversation history to understand what they are referring to.
"""

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    return response.text