from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    ADMIN_ID: int

    DB_URL: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    ENCRYPTION_KEY: SecretStr
    ORDERS_CHANNEL_ID: int

    # To'lov ma'lumotlari
    PAYMENT_CARD: str = "8600 0000 0000 0000"       # Karta raqami
    PAYMENT_CARD_OWNER: str = "Karta egasi"          # Karta egasining ismi
    PAYMENT_PHONE: str = ""                          # To'lov rekvizitlari telefoni
    SUPPORT_URL: str = "https://t.me/entelli_sale" # Qo'llab-quvvatlash havolasi

    # Referal tizimi
    REFERRAL_BONUS_UZS: int = 2000                   # Referal bonusi (UZS)

    # Bot nomi (xabarlarda ko'rinadi)
    BOT_USERNAME: str = "entellibot"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        url = self.DB_URL
        if "?" in url:
            url = url.split("?")[0]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


config = Settings()
