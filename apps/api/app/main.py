from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

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


@app.on_event("startup")
def startup_event():
    if settings.schema_management_mode == "bootstrap":
        Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "user_links" not in inspector.get_table_names():
        return

    db = SessionLocal()
    try:
        seed_if_empty(db)
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True, "provider": settings.app_provider}


app.include_router(router)
