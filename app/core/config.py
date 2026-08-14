import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root123"
    DB_NAME: str = "fastapi_modules"
    SECRET_KEY: str = "supersecretjwtkeythatis256bitlongforsecuritypurpose12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    EXTERNAL_API_URL: str = "https://jsonplaceholder.typicode.com/posts/1"

    @property
    def database_url(self) -> str:
        if os.getenv("TESTING") == "1":
            return "sqlite:///:memory:"
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
