from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import imports, transactions
from app.core.config import settings
from app.core.errors import register_exception_handlers


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(imports.router)
app.include_router(transactions.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
