from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.db.database import Base, SessionLocal, engine
from app.services.services import seed_if_empty

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def token_guard(request: Request, call_next):
    exempt_paths = {"/health", "/api/events/stream"}
    if request.url.path.startswith("/api") and request.method != "OPTIONS" and request.url.path not in exempt_paths:
        token = request.headers.get("x-api-token")
        if token != settings.api_token:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True, "provider": settings.app_provider}


app.include_router(router)
