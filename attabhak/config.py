import pathlib
from pydantic_settings import BaseSettings, SettingsConfigDict


DOTENV = pathlib.Path(__file__).parent.parent / ".env"

print("Loading settings from:", DOTENV)


class Settings(BaseSettings):

    DUSTRACT_HOST: str = "192.168.8.88"
    DUSTRACT_PORT: int = 3602

    SANTHINGS_COAP_URI: str = "coap://things.airthai.in.th"
    SANTHINGS_DEVICE_ID: str = "your_device_id"
    SANTHINGS_SECRET_KEY: str = "your_secret_key"

    INTERVAL: int = 60  # seconds

    model_config = SettingsConfigDict(env_file=DOTENV, extra="ignore")


# Create a global instance
settings = Settings()
