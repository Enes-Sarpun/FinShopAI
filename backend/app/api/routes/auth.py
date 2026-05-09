from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import RegisterRequest, LoginRequest, UserResponse
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger("auth")


@router.post("/register")
async def register(body: RegisterRequest):
    """Yeni kullanıcı kaydı. Supabase Auth üzerinden yapılır."""
    client = SupabaseService().client
    try:
        result = client.auth.sign_up({
            "email": body.email,
            "password": body.password,
            "options": {
                "data": {"full_name": body.full_name}
            }
        })
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not result.user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kayıt başarısız")

    return {
        "message": "Kayıt başarılı. E-posta doğrulaması gerekebilir.",
        "user_id": result.user.id,
        "email": result.user.email,
    }


@router.post("/login")
async def login(body: LoginRequest):
    """Kullanıcı girişi. Supabase access token döner."""
    client = SupabaseService().client
    try:
        result = client.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya şifre hatalı")

    if not result.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş başarısız")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
        "user_id": result.user.id,
        "email": result.user.email,
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Token'dan mevcut kullanıcı bilgisini döner."""
    db = SupabaseService()
    profile = await db.get_profile(current_user["sub"])
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil bulunamadı")
    return profile
