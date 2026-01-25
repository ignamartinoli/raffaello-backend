from fastapi import FastAPI

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.router import api_router

app = FastAPI()

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
