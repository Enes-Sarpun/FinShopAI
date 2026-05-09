from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("main")

app = FastAPI(
    title="FinShop AI",
    description="Cüzdanını Bilen Akıllı Alışveriş Asistanı",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import personality, auth
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(personality.router, prefix="/api/personality", tags=["personality"])

# Diğer route'lar agent'lar tamamlandıkça eklenecek
# from app.api.routes import budget, chat, products
# app.include_router(budget.router, prefix="/api/budget", tags=["budget"])
# app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
# app.include_router(products.router, prefix="/api/products", tags=["products"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "FinShop AI"}
