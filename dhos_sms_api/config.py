from environs import Env
from flask import Flask


class Configuration:
    env = Env()
    TWILIO_ACCOUNT_SID: str = env.str("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = env.str("TWILIO_AUTH_TOKEN")
    TWILIO_CALL_BACK_URL: str = env.str("TWILIO_CALL_BACK_URL")
    COUNTRY_CODE: str = env.str("COUNTRY_CODE")
    TWILIO_DISABLED: bool = env.bool("TWILIO_DISABLED", False)


def init_config(app: Flask) -> None:
    app.config.from_object(Configuration)
