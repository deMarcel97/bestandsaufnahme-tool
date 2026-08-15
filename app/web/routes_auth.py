from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.config import (
    ENTRA_TENANT_ID,
    ENTRA_CLIENT_ID,
    ENTRA_CLIENT_SECRET,
    ENTRA_REDIRECT_PATH,
    AUTH_ENABLED,
)

router = APIRouter()

oauth = OAuth()
if AUTH_ENABLED:
    oauth.register(
        name="entra",
        client_id=ENTRA_CLIENT_ID,
        client_secret=ENTRA_CLIENT_SECRET,
        server_metadata_url=(
            f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid profile email"},
    )

@router.get("/auth/login")
async def login(request: Request):
    if not AUTH_ENABLED:
        return RedirectResponse(url="/auftrag", status_code=303)
    redirect_uri = request.url_for("auth_callback")
    return await oauth.entra.authorize_redirect(request, str(redirect_uri))

@router.get(ENTRA_REDIRECT_PATH, name="auth_callback")
async def auth_callback(request: Request):
    if not AUTH_ENABLED:
        return RedirectResponse(url="/auftrag", status_code=303)
    token = await oauth.entra.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    request.session["user"] = {
        "sub": userinfo.get("sub"),
        "name": userinfo.get("name"),
        "email": userinfo.get("email") or userinfo.get("preferred_username"),
    }
    return RedirectResponse(url="/auftrag", status_code=303)

@router.get("/auth/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/auftrag", status_code=303)
