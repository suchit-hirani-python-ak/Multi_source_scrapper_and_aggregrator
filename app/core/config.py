from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    algorithm: str
    mongo_url: str
    redis_url: str
    access_token: SecretStr
    refresh_token: SecretStr
    access_expire_in_minutes: int 
    refresh_expire_in_days: int 
    encription: str
    admin_name: SecretStr
    admin_pass: SecretStr
    cookie_same_site: str
    cookie_secure: bool
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
        
settings = Settings() # type: ignore