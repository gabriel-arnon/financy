from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts, ai_finance, categories, classification_rules, files, imports, open_finance, reimbursements, statements, transactions
from app.core.config import settings
from app.core.errors import register_exception_handlers


app = FastAPI(title=settings.app_name)
settings.validate_private_files_config()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(imports.router)
app.include_router(files.files_router)
app.include_router(files.transaction_attachments_router)
app.include_router(reimbursements.router)
app.include_router(ai_finance.router)
app.include_router(open_finance.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(accounts.accounts_router)
app.include_router(accounts.cards_router)
app.include_router(classification_rules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
