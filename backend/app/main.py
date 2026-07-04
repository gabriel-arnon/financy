from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api import accounts, categories, classification_rules, imports, statements, transactions
from app.core.config import settings
from app.core.errors import register_exception_handlers


app = FastAPI(title=settings.app_name)


@app.middleware("http")
async def log_import_upload_requests(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/imports/upload":
        print(
            "IMPORT_UPLOAD_REQUEST_START",
            {
                "content_length": request.headers.get("content-length"),
                "content_type": request.headers.get("content-type"),
                "origin": request.headers.get("origin"),
            },
            flush=True,
        )
    response = await call_next(request)
    if request.method == "POST" and request.url.path == "/imports/upload":
        print("IMPORT_UPLOAD_REQUEST_END", {"status_code": response.status_code}, flush=True)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(imports.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(accounts.accounts_router)
app.include_router(accounts.cards_router)
app.include_router(classification_rules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
