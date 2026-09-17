import httpx

from fastapi import HTTPException


# =========================================================
# Ollama Configuration
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/generate"

GENERATION_MODEL = "qwen2.5-coder:7b-instruct"

# Local Ollama can take longer on larger codebases.
OLLAMA_TIMEOUT = 600.0


# =========================================================
# Generate Answer
# =========================================================

def generate_answer(
    question: str,
    context: str,
    conversation_history: str = ""
):

    prompt = f"""
You are an AI assistant that answers questions about a software codebase.

Use ONLY the provided code context and conversation history.

Do not invent code, files, functions, dependencies, APIs,
or behavior that is not supported by the provided context.

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

Use Markdown when useful.
"""

    payload = {
        "model": GENERATION_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 512
        }
    }

    try:

        response = httpx.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        answer = data.get("response", "")

        if not answer.strip():
            raise HTTPException(
                status_code=502,
                detail="Ollama returned an empty response."
            )

        return answer.strip()

    except httpx.ConnectError:

        raise HTTPException(
            status_code=503,
            detail=(
                "Could not connect to Ollama. "
                "Please make sure Ollama is running."
            )
        )

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail=(
                "Ollama took too long to generate a response. "
                "Please try again."
            )
        )

    except httpx.HTTPStatusError as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama returned an error: "
                f"{error.response.status_code}"
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Local AI generation failed: {str(error)}"
        )