import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth_routes import router as auth_router


# =========================================================
# Routes
# =========================================================

from routes.search_routes import router as search_router

from routes.chat_routes import router as chat_router

from routes.relationship_routes import (
    router as relationship_router
)

from routes.impact_routes import (
    router as impact_router
)

from routes.impact_explanation_routes import (
    router as impact_explanation_router
)

from routes.architecture_routes import (
    router as architecture_router
)

from routes.file_explanation_routes import (
    router as file_explanation_router
)

from routes.code_review_routes import (
    router as code_review_router
)

from routes.test_generation_routes import (
    router as test_generation_router
)

from routes.code_fix_routes import (
    router as code_fix_router
)

from routes.code_search_routes import (
    router as code_search_router
)

from routes.code_diff_routes import (
    router as code_diff_router
)

from routes.documentation_routes import (
    router as documentation_router
)


from routes.readme_routes import (
    router as readme_router
)


from routes.test_runner_routes import (
    router as test_runner_router
)

from routes.github_routes import router as github_router
from routes.ai_result_routes import router as ai_result_router
# =========================================================
# Database
# =========================================================

from database.database import Base, engine


# =========================================================
# Models
# =========================================================

from models.project import Project
from models.code_file import CodeFile
from models.code_chunk import CodeChunk
from models.code_relationship import CodeRelationship
from models.user import User
from models.ai_result import AIResult

Base.metadata.create_all(bind=engine)


# =========================================================
# Basic Routes
# =========================================================

from routes.project_routes import (
    router as project_router
)

from routes.code_file_routes import (
    router as code_file_router
)

from routes.chunk_routes import (
    router as chunk_router
)
from routes.auth_routes import router as auth_router

from routes.auth_routes import router as auth_router
# =========================================================
# Create FastAPI Application
# =========================================================

async def secure_exception_handler(request, exc):
    """
    Return a safe error message without exposing internal
    stack traces, database details, file paths, or secrets.
    """
    logging.exception(
        "Unhandled backend error: %s %s",
        request.method,
        request.url.path
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected server error occurred. Please try again."
        }
    )


app = FastAPI()

# Keep detailed exception information in the backend logs,
# but return a safe message to API clients.
logger = logging.getLogger("uvicorn.error")


@app.exception_handler(Exception)
async def handle_unexpected_exception(request, exc):
    logger.exception(
        "Unhandled server error on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )



# =========================================================
# Register AI / Feature Routes
# =========================================================

app.include_router(search_router)

app.include_router(chat_router)

app.include_router(relationship_router)

app.include_router(impact_router)

app.include_router(
    impact_explanation_router
)
app.add_exception_handler(Exception, secure_exception_handler)


app.include_router(
    architecture_router
)

app.include_router(
    file_explanation_router
)

app.include_router(
    code_review_router
)

app.include_router(
    test_generation_router
)

app.include_router(
    code_fix_router
)

app.include_router(
    code_search_router
)

app.include_router(
    code_diff_router
)

app.include_router(
    documentation_router
)


app.include_router(
    readme_router
)


app.include_router(
    test_runner_router
)

app.include_router(auth_router)

app.include_router(auth_router)

app.include_router(github_router)
app.include_router(ai_result_router)

# =========================================================
# Create Database Tables
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# Register Basic Routes
# =========================================================

app.include_router(
    project_router
)

app.include_router(
    code_file_router
)

app.include_router(
    chunk_router
)

app.include_router(auth_router)
# =========================================================
# Security Middleware
# =========================================================

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


MAX_REQUEST_SIZE = 25 * 1024 * 1024  # 25 MB



# =========================================================
# Simple in-memory rate limiting
# =========================================================

AI_RATE_LIMIT = 30          # requests
AI_RATE_WINDOW = 60         # seconds

AI_ENDPOINTS = (
    "/chat/",
    "/search/",
    "/architecture/",
    "/impact/",
    "/impact-explanation/",
    "/file-explanation/",
    "/code-review/",
    "/test-generation/",
    "/code-fix/",
    "/code-search/",
    "/documentation/",
    "/readme/",
    "/code-diff/",
)

request_history = defaultdict(deque)


def is_ai_endpoint(path: str) -> bool:
    return any(path.startswith(endpoint) for endpoint in AI_ENDPOINTS)


def is_rate_limited(client_ip: str, path: str) -> bool:
    key = f"{client_ip}:{path.split('/')[1]}"
    now = time.monotonic()
    requests = request_history[key]

    while requests and now - requests[0] > AI_RATE_WINDOW:
        requests.popleft()

    if len(requests) >= AI_RATE_LIMIT:
        return True

    requests.append(now)
    return False


class SecurityMiddleware:
    """Add basic API security protections."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Basic URL/input validation.
        raw_path = scope.get("path", "")
        raw_query = scope.get("query_string", b"")

        if "\\x00" in raw_path:
            response = JSONResponse(
                status_code=400,
                content={"detail": "Invalid request path"}
            )
            await response(scope, receive, send)
            return

        if len(raw_path) > 2048:
            response = JSONResponse(
                status_code=414,
                content={"detail": "Request URL is too long"}
            )
            await response(scope, receive, send)
            return

        if len(raw_query) > 4096:
            response = JSONResponse(
                status_code=414,
                content={"detail": "Query string is too long"}
            )
            await response(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        if is_ai_endpoint(raw_path) and is_rate_limited(client_ip, raw_path):
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "Too many AI requests. "
                        "Please wait a minute and try again."
                    )
                },
                headers={"Retry-After": str(AI_RATE_WINDOW)}
            )
            await response(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        content_length = headers.get("content-length")

        if content_length:
            try:
                request_size = int(content_length)
            except ValueError:
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"}
                )
                await response(scope, receive, send)
                return

            if request_size > MAX_REQUEST_SIZE:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Request is too large. Maximum size is 25 MB."
                    }
                )
                await response(scope, receive, send)
                return

        async def secure_send(message):
            if message["type"] == "http.response.start":
                existing_headers = list(message.get("headers", []))
                existing_names = {
                    key.lower()
                    for key, _ in existing_headers
                }

                security_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (
                        b"permissions-policy",
                        b"camera=(), microphone=(), geolocation=()"
                    ),
                ]

                for key, value in security_headers:
                    if key not in existing_names:
                        existing_headers.append((key, value))

                message["headers"] = existing_headers

            await send(message)

        await self.app(scope, receive, secure_send)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    SecurityMiddleware
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)


# =========================================================
# Root Endpoint
# =========================================================

@app.get("/")
def root():

    return {
        "message":
        "Codebase RAG Assistant API is running"
    }


# =========================================================
# Database Test
# =========================================================

@app.get("/db-test")
def database_test():

    try:

        with engine.connect():

            return {
                "message":
                "Database connection successful"
            }

    except Exception as e:

        return {
            "message":
            "Database connection failed",
            "error":
            str(e)
        }
