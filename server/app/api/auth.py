from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import httpx

from ..core.security import get_current_user, ClerkUser, get_current_admin
from ..core.logging import get_logger
from ..db.mongodb import MongoDB
from ..core.config import get_settings

logger = get_logger("api.auth")
router = APIRouter()
settings = get_settings()

# ---------------------------
# Modèles existants
# ---------------------------
class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    profile_completed: bool = False
    metadata: Optional[dict] = None

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    company_name: Optional[str] = None

# ---------------------------
# Modèles pour sign-in
# ---------------------------
class SignInRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False

class SignInResponse(BaseModel):
    user: UserResponse
    session_token: str
    expires_at: int

# ---------------------------
# Endpoints existants
# ---------------------------
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: ClerkUser = Depends(get_current_user)):
    """Obtenir les informations de l'utilisateur courant"""
    users_collection = MongoDB.get_collection("users")
    user_data = await users_collection.find_one({"clerk_id": current_user.id})

    if user_data:
        profile_completed = user_data.get("profile_completed", False)
        metadata = {
            **(current_user.metadata or {}),
            **(user_data.get("metadata", {}))
        }
    else:
        profile_completed = False
        metadata = current_user.metadata

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        profile_completed=profile_completed,
        metadata=metadata
    )

@router.put("/me/profile", response_model=UserResponse)
async def update_user_profile(
    profile: UserProfileUpdate,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Met à jour les informations du profil de l'utilisateur"""
    users_collection = MongoDB.get_collection("users")
    user_data = await users_collection.find_one({"clerk_id": current_user.id})

    update_data = {
        "clerk_id": current_user.id,
        "email": current_user.email,
        "first_name": profile.first_name or current_user.first_name,
        "last_name": profile.last_name or current_user.last_name,
        "profile_completed": True,
        "metadata": {
            "phone_number": profile.phone_number,
            "job_title": profile.job_title,
            "department": profile.department,
            "company_name": profile.company_name
        }
    }

    if user_data:
        await users_collection.update_one(
            {"clerk_id": current_user.id},
            {"$set": update_data}
        )
    else:
        await users_collection.insert_one(update_data)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=update_data["first_name"],
        last_name=update_data["last_name"],
        role=current_user.role,
        profile_completed=True,
        metadata=update_data["metadata"]
    )

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(current_user: ClerkUser = Depends(get_current_admin)):
    """Obtenir la liste de tous les utilisateurs (admin uniquement)"""
    users_collection = MongoDB.get_collection("users")
    users = await users_collection.find().to_list(length=100)

    return [
        UserResponse(
            id=user.get("clerk_id", ""),
            email=user.get("email", ""),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            role=user.get("role", "user"),
            profile_completed=user.get("profile_completed", False),
            metadata=user.get("metadata", {})
        )
        for user in users
    ]

@router.get("/users/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_users_from_clerk(current_user: ClerkUser = Depends(get_current_admin)):
    """
    Synchronise les utilisateurs de Clerk vers notre base de données (admin uniquement)
    
    En production, cet endpoint devrait appeler l'API de Clerk pour récupérer tous les utilisateurs
    et mettre à jour notre base de données.
    """
    return {
        "message": "La synchronisation des utilisateurs a démarré",
        "status": "processing"
    }

# ---------------------------
# Nouvel endpoint: sign-in
# ---------------------------
@router.post("/sign-in", response_model=SignInResponse)
async def sign_in(sign_in_data: SignInRequest, response: Response):
    try:
        clerk_instance = settings.CLERK_INSTANCE_ID

        async with httpx.AsyncClient() as client:
            clerk_response = await client.post(
                f"https://{clerk_instance}.clerk.accounts.dev/v1/client/sign_ins",
                json={
                    "identifier": sign_in_data.email,
                    "password": sign_in_data.password,
                    "strategy": "password"
                },
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}
            )

            if clerk_response.status_code != 200:
                error_data = clerk_response.json()
                logger.error(f"Erreur lors de la connexion avec Clerk : {error_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Identifiants invalides"
                )

            clerk_data = clerk_response.json()
            logger.info(f"Réponse Clerk complète : {clerk_data}")

            # Extraction de l'identifiant utilisateur directement au niveau racine
            clerk_user_id = clerk_data.get("id")
            if not clerk_user_id:
                logger.error(f"La réponse de Clerk ne contient pas d'identifiant utilisateur: {clerk_data}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="La réponse de Clerk ne contient pas d'identifiant utilisateur."
                )

            # Récupération ou création de l'utilisateur dans la base MongoDB
            users_collection = MongoDB.get_collection("users")
            user_data = await users_collection.find_one({"clerk_id": clerk_user_id})

            if not user_data:
                # Extraction de l'email à partir de l'array 'email_addresses'
                primary_email = ""
                if clerk_data.get("email_addresses") and isinstance(clerk_data["email_addresses"], list):
                    primary_email = clerk_data["email_addresses"][0].get("email_address", "")
                    
                # Si first_name et last_name ne sont pas renseignés, on peut vérifier dans unsafe_metadata
                unsafe_metadata = clerk_data.get("unsafe_metadata", {})
                first_name = clerk_data.get("first_name") or unsafe_metadata.get("firstName", "")
                last_name = clerk_data.get("last_name") or unsafe_metadata.get("lastName", "")

                user_doc = {
                    "clerk_id": clerk_user_id,
                    "email": primary_email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": "user",
                    "profile_completed": False,
                    "last_login": datetime.utcnow(),
                }
                await users_collection.insert_one(user_doc)
                user_role = "user"
                profile_completed = False
                metadata = {}
            else:
                await users_collection.update_one(
                    {"clerk_id": clerk_user_id},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                user_role = user_data.get("role", "user")
                profile_completed = user_data.get("profile_completed", False)
                metadata = user_data.get("metadata", {})

            # Construire la réponse utilisateur
            primary_email = ""
            if clerk_data.get("email_addresses") and isinstance(clerk_data["email_addresses"], list):
                primary_email = clerk_data["email_addresses"][0].get("email_address", "")
            unsafe_metadata = clerk_data.get("unsafe_metadata", {})
            first_name = clerk_data.get("first_name") or unsafe_metadata.get("firstName", "")
            last_name = clerk_data.get("last_name") or unsafe_metadata.get("lastName", "")

            user_response = UserResponse(
                id=clerk_user_id,
                email=primary_email,
                first_name=first_name,
                last_name=last_name,
                role=user_role,
                profile_completed=profile_completed,
                metadata=metadata
            )

            # Gestion du cookie si "remember_me" est activé
            if sign_in_data.remember_me:
                response.set_cookie(
                    key="session_token",
                    value=clerk_data["token"],
                    httponly=True,
                    secure=settings.ENVIRONMENT != "development",
                    samesite="lax"
                )

            return SignInResponse(
                user=user_response,
                session_token=clerk_data["token"],
                expires_at=clerk_data["expires_at"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la connexion : {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur est survenue pendant la connexion"
        )
