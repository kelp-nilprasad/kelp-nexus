"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Kelp Nexus"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]
    web_base_url: str = "http://localhost:3000"

    # --- Database ---------------------------------------------------------
    # Either set DATABASE_URL directly, or provide the discrete DB_* parts and
    # they are assembled below. Discrete parts win only when DATABASE_URL is unset.
    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "kelp_nexus"
    db_user: str = "kelp"
    db_password: str = "kelp"
    db_enable_ssl: bool = False

    # --- Auth (app session) ----------------------------------------------
    # Sign-in is Microsoft Entra ID (MSAL SSO) only — there is no local password login.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- MSAL / Entra ID (Microsoft sign-in) ------------------------------
    msal_client_id: str | None = None
    msal_tenant_id: str | None = None
    msal_client_secret: str | None = None  # required for SharePoint (app-only Graph)
    msal_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"
    msal_scopes: list[str] = ["User.Read"]

    # --- SharePoint (Microsoft Graph, app-only / client-credentials) ------
    # Report assets (HTML/PDF/video) are stored in a SharePoint document library
    # and accessed with an APP-ONLY Graph token (the app's own identity, via
    # MSAL_CLIENT_SECRET) — no per-user token, so every signed-in user can
    # upload/view. Requires the Entra app to hold the APPLICATION permission
    # `Sites.ReadWrite.All` with admin consent granted.
    #
    # `sharepoint_site` may be a plain site name (resolved via Graph search, e.g.
    # "KelpNexus") or an explicit "hostname:/sites/Name" path. `sharepoint_library`
    # is the document library (drive) display name; the site's default drive is used
    # when unset. Files are stored under `sharepoint_root_folder` inside it.
    sharepoint_site: str = "KelpNexus"
    sharepoint_library: str | None = None
    sharepoint_root_folder: str = "reports"
    # Application Graph permission the app must be granted + admin-consented.
    # (The app-only token itself is requested with the ".default" scope.)
    graph_scopes: list[str] = ["Sites.ReadWrite.All"]

    # --- AI (Claude) — features degrade gracefully if unset ---------------
    anthropic_api_key: str | None = None
    ai_model: str = "claude-opus-4-8"
    embedding_dim: int = 1536
    enable_ai: bool = False

    @model_validator(mode="after")
    def _assemble_database_url(self) -> "Settings":
        if not self.database_url:
            sslmode = "?sslmode=require" if self.db_enable_ssl else ""
            self.database_url = (
                f"postgresql+psycopg://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}{sslmode}"
            )
        return self

    @property
    def msal_authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.msal_tenant_id}"

    @property
    def msal_configured(self) -> bool:
        return bool(self.msal_client_id and self.msal_tenant_id)

    @property
    def sharepoint_configured(self) -> bool:
        """App-only SharePoint access needs the app's client credentials."""
        return bool(self.msal_configured and self.msal_client_secret)

    @property
    def login_scopes(self) -> list[str]:
        """Scopes requested during Microsoft sign-in (app session profile only)."""
        return list(self.msal_scopes)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
