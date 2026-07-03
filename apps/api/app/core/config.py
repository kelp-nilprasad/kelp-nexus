"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
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
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    dev_login: bool = True  # enable /auth/dev-login + seeded local accounts

    # --- MSAL / Entra ID (Microsoft sign-in) ------------------------------
    msal_client_id: str | None = None
    msal_tenant_id: str | None = None
    msal_client_secret: str | None = None  # omit for a public client (PKCE only)
    msal_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"
    msal_scopes: list[str] = ["User.Read"]

    # --- Azure Blob storage ----------------------------------------------
    # Preferred: account name + key (real Azure). Falls back to the Azurite
    # connection string for local dev when account name/key are not set.
    # Aliases accept the user's env names: AZURE_ACCOUNT, AZURE_CONTAINER_PATH.
    azure_account_name: str | None = Field(
        default=None, validation_alias=AliasChoices("azure_account_name", "azure_account")
    )
    azure_account_key: str | None = None
    azure_blob_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("azure_blob_endpoint", "azure_container_path"),
    )
    azure_blob_container: str = "reports"
    azure_storage_connection_string: str = (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
        "K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;"
    )

    # --- Storage backend --------------------------------------------------
    # "azure" (Azure Blob) or "sharepoint" (Microsoft Graph, delegated user token).
    storage_backend: str = "azure"

    # --- SharePoint (Microsoft Graph, delegated) --------------------------
    # `sharepoint_site` may be a plain site name (resolved via Graph search, e.g.
    # "KelpNexus") or an explicit "hostname:/sites/Name" path. `sharepoint_library`
    # is the document library (drive) display name; the site's default drive is used
    # when unset. Files are stored under `sharepoint_root_folder` inside it.
    sharepoint_site: str = "KelpNexus"
    sharepoint_library: str | None = None
    sharepoint_root_folder: str = "reports"
    # Delegated Graph scope needed to read/write the site's document library.
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
    def use_sharepoint(self) -> bool:
        return self.storage_backend.lower() == "sharepoint"

    @property
    def login_scopes(self) -> list[str]:
        """Scopes requested during MSAL sign-in (adds Graph scopes for SharePoint)."""
        scopes = list(self.msal_scopes)
        if self.use_sharepoint:
            scopes += [s for s in self.graph_scopes if s not in scopes]
        return scopes

    @property
    def azure_blob_account_url(self) -> str | None:
        if self.azure_blob_endpoint:
            return self.azure_blob_endpoint
        if self.azure_account_name:
            return f"https://{self.azure_account_name}.blob.core.windows.net"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
