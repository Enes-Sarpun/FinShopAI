from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("main")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="FinShop AI",
    description="Cüzdanını Bilen Akıllı Alışveriş Asistanı",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import personality, auth, budget, products, chat
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(personality.router, prefix="/api/personality", tags=["personality"])
app.include_router(budget.router, prefix="/api/budget", tags=["budget"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "FinShop AI"}