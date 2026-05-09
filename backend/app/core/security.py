from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from app.core.config import settings

security = HTTPBearer()


def get_supabase_user(token: str) -> dict:
    """Supabase access token'ı doğrular ve kullanıcı bilgisini döner."""
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        result = client.auth.get_user(token)
        if not result or not result.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token")
        return {"sub": result.user.id, "email": result.user.email}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz veya süresi dolmuş token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    return get_supabase_user(credentials.credentials)
