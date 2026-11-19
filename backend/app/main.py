import logging
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DatabaseSession

from .catalog import list_problems
from .config import settings
from .auth_routes import router as auth_router
from .main_dependencies import get_db
from .models import Problem
from .schemas import Catalog, Category, Difficulty, ProblemDetail
from .submission_routes import router as submission_router
from .gamification_routes import router as gamification_router

logging.basicConfig(level=settings().log_level)
logger = logging.getLogger(__name__)
app = FastAPI(title="EKLAVYA")
router = APIRouter(prefix="/api/v1")


DB = Annotated[DatabaseSession, Depends(get_db)]


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    logger.error("Database operation failed for %s (%s)", request.url.path, type(error).__name__)
    return JSONResponse(status_code=503, content={"detail": "Catalog is temporarily unavailable"})


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
app.include_router(router)
