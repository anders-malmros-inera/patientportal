from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Patientportal - Lakemedelskollen"
    api_prefix: str = "/api"
    jwt_secret: str = "replace-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    lakemedelskollen_direct_enabled: bool = False
    lakemedelskollen_base_url: str = "https://api.lakemedelskollen.example"
    lakemedelskollen_prescriptions_path: str = "/v1/prescriptions"
    lakemedelskollen_api_token: str = ""
    lakemedelskollen_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(env_prefix="PATIENTPORTAL_", case_sensitive=False)


settings = Settings()
