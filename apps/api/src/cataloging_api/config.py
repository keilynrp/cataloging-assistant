from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "DSpace Cataloging Assistant"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://cataloging:cataloging@localhost:5432/cataloging"
    dspace_base_url: str = Field(
        default="http://132.248.101.240:8080/server/api",
        validation_alias="DSpace_BASE_URL",
    )
    dspace_pilot_collection_uuid: str = Field(
        default="e9a8f44f-a8d3-4d22-b02a-cf590285bac6",
        validation_alias="DSpace_PILOT_COLLECTION_UUID",
    )
    dspace_pilot_collection_handle: str = Field(
        default="123456789/4",
        validation_alias="DSpace_PILOT_COLLECTION_HANDLE",
    )
    dspace_page_size: int = Field(default=20, ge=1, le=100)
    dspace_max_concurrency: int = Field(default=4, ge=1, le=10)
    dspace_timeout_seconds: float = Field(default=20, gt=0, le=120)
    dspace_max_retries: int = Field(default=4, ge=0, le=8)
    dspace_read_username: str = ""
    dspace_read_password: str = ""
    catalog_required_fields: str = ""
    catalog_review_token: str = ""
    catalog_web_origin: str = "http://localhost:3000"

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(
            field.strip() for field in self.catalog_required_fields.split(",") if field.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
