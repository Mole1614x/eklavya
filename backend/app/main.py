import logging
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DatabaseSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .catalog import list_problems
from .config import settings
from .auth_routes import router as auth_router
from .main_dependencies import get_db
from .models import Problem
from .schemas import Catalog, Category, Difficulty, ProblemDetail
from .submission_routes import router as submission_router
from .gamification_routes import router as gamification_router
from .learning_routes import router as learning_router
from .contest_routes import router as contest_router
from .operations import RateLimitMiddleware, RequestMiddleware, configure_logging, metrics

configuration = settings()
configure_logging(configuration.log_level)
logger = logging.getLogger(__name__)
app = FastAPI(
    title="EKLAVYA", version="1.0.0",
    docs_url=None if configuration.environment == "production" else "/docs",
    redoc_url=None if configuration.environment == "production" else "/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configuration.origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=configuration.host_list)
app.add_middleware(RateLimitMiddleware, configuration=configuration)
app.add_middleware(RequestMiddleware, configuration=configuration)
router = APIRouter(prefix="/api/v1")


DB = Annotated[DatabaseSession, Depends(get_db)]


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    logger.error(
        "database_operation_failed",
        extra={"request_id": request.state.request_id, "path": request.url.path},
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "The service is temporarily unavailable", "request_id": request.state.request_id},
    )


@router.get("/health")
@router.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "eklavya-api"}


@router.get("/health/ready")
def readiness(db: DB) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        if configuration.readiness_check_redis:
            client = Redis.from_url(configuration.redis_url, socket_connect_timeout=1, socket_timeout=1)
            try:
                client.ping()
            finally:
                client.close()
    except Exception as error:
        raise HTTPException(status_code=503, detail="A required dependency is unavailable") from error
    return {"status": "ready", "service": "eklavya-api"}


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> PlainTextResponse:
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


@router.get("/problems", response_model=Catalog)
def problems(
    db: DB, q: Annotated[str, Query(max_length=100)] = "", category: Category | None = None,
    difficulty: Difficulty | None = None, topic: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0,
) -> Catalog:
    return list_problems(db, q, category, difficulty, topic, limit, offset)


@router.get("/problems/{slug}", response_model=ProblemDetail)
def problem(slug: str, db: DB) -> Problem:
    item = db.get(Problem, slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return item


router.include_router(auth_router)
router.include_router(submission_router)
router.include_router(gamification_router)
router.include_router(learning_router)
router.include_router(contest_router)
app.include_router(router)
