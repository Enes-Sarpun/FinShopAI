from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from app.models.user import RegisterRequest, LoginRequest, UserResponse
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger("auth")


# ~2.7 MB base64 ≈ 2 MB binary. Frontend zaten 2 MB sınırı uyguluyor; biraz
# margin bırakıyoruz çünkü base64 ~%33 büyütüyor.
MAX_AVATAR_LENGTH = 3_000_000


class AvatarUpdateRequest(BaseModel):
    avatar_url: str | None = Field(default=None)


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


@router.patch("/me/avatar")
async def update_avatar(
    body: AvatarUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Kullanıcının profil fotoğrafını günceller.
    avatar_url: base64 data URL (örn. 'data:image/png;base64,...') veya null (kaldırmak için).
    """
    user_id = current_user["sub"]
    avatar = body.avatar_url

    if avatar is not None:
        avatar = avatar.strip()
        if avatar == "":
            avatar = None
        else:
            if not avatar.startswith("data:image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="avatar_url 'data:image/...' formatında olmalı",
                )
            if len(avatar) > MAX_AVATAR_LENGTH:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Görsel çok büyük (en fazla ~2 MB).",
                )

    try:
        db = SupabaseService()
        await db.update_avatar(user_id, avatar)
        return {"success": True, "avatar_url": avatar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
