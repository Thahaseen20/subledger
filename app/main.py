from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import create_tables
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.routes.billing import router as billing_router
from app.routes.catalog import router as catalog_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    description="A layered subscription billing and ledger backend foundation.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(catalog_router, prefix=settings.api_prefix)
app.include_router(billing_router, prefix=settings.api_prefix)


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(_: Request, exc: BusinessRuleError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}
