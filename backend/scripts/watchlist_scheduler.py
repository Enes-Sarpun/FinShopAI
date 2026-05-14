"""
Watchlist Price Check Scheduler
================================
Tüm kullanıcıların takip listelerini periyodik olarak kontrol eden arka plan görevi.

Çalıştırma:
    python -m scripts.watchlist_scheduler

Ortam değişkeni ile aralık ayarlanabilir:
    WATCHLIST_CHECK_INTERVAL_MINUTES=60  (varsayılan: 60 dakika)
"""

import asyncio
import os
import sys

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.agents.watchlist_agent import WatchlistAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.logger import get_logger

logger = get_logger("watchlist_scheduler")

# Kontrol aralığı (dakika) — .env'den veya varsayılan
CHECK_INTERVAL_MINUTES = int(os.getenv("WATCHLIST_CHECK_INTERVAL_MINUTES", "60"))


async def check_all_users() -> None:
    """Sistemdeki tüm aktif kullanıcıların takip listelerini kontrol eder."""
    logger.info("Tüm kullanıcı fiyat kontrolü başladı")

    db = SupabaseService()
    llm = LLMService()

    try:
        # Aktif takip listesi olan distinct user_id'leri çek
        result = (
            db.client.table("watchlist")
            .select("user_id")
            .eq("is_active", True)
            .execute()
        )

        if not result.data:
            logger.info("Hiçbir kullanıcının aktif takip listesi yok.")
            return

        # Unique user_id'leri al
        user_ids = list({row["user_id"] for row in result.data})
        logger.info(f"Kontrol edilecek kullanıcı sayısı: {len(user_ids)}")

        agent = WatchlistAgent(llm=llm, db=db)

        for user_id in user_ids:
            try:
                outcome = await agent.execute({
                    "user_id": user_id,
                    "mode": "check"
                })
                logger.info(
                    f"user={user_id} | checked={outcome.get('checked')} "
                    f"| alerts={outcome.get('alerts_triggered')}"
                )
            except Exception as e:
                logger.error(f"Kullanıcı kontrol hatası [{user_id}]: {e}")

        logger.info("Tüm kullanıcı fiyat kontrolü tamamlandı")

    except Exception as e:
        logger.error(f"Scheduler genel hata: {e}")


async def run_scheduler() -> None:
    """Sonsuza kadar her N dakikada bir check_all_users() çalıştırır."""
    logger.info(
        f"WatchlistScheduler başlatıldı | "
        f"Aralık: {CHECK_INTERVAL_MINUTES} dakika"
    )

    while True:
        try:
            await check_all_users()
        except Exception as e:
            logger.error(f"Scheduler döngü hatası: {e}")

        logger.info(f"Sonraki kontrol {CHECK_INTERVAL_MINUTES} dakika sonra")
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    asyncio.run(run_scheduler())
