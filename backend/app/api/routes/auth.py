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


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)


@router.post("/register")
async def register(body: RegisterRequest):
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

    db = SupabaseService()
    await db.upsert_profile({
        "id": result.user.id,
        "email": result.user.email,
        "full_name": body.full_name,
    })

    return {
        "message": "Kayıt başarılı. E-posta doğrulaması gerekebilir.",
        "user_id": result.user.id,
        "email": result.user.email,
    }


@router.post("/login")
async def login(body: LoginRequest):
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

    db = SupabaseService()
    user_id = result.user.id
    personality = await db.get_personality(user_id)
    budget = await db.get_budget(user_id)

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": result.user.email,
        "has_personality": personality is not None,
        "has_budget": budget is not None,
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    db = SupabaseService()
    profile = await db.get_profile(current_user["sub"])
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil bulunamadı")
    return profile


@router.patch("/me/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        await db.upsert_profile({"id": user_id, "full_name": body.full_name.strip()})
        return {"success": True, "full_name": body.full_name.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/me/avatar")
async def update_avatar(
    body: AvatarUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
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
