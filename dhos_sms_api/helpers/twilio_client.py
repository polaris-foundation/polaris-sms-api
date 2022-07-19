from datetime import datetime
from typing import Dict, Optional, TypedDict

from flask import current_app
from flask_batteries_included.config import is_not_production_environment
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import ServiceUnavailableException
from she_logging import logger
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.rest.api.v2010.account.message import MessageInstance

SECURITY_HEADER_NAME = "X-Twilio-Signature"


class ProviderResponse(TypedDict):
    status: Optional[str]
    twilio_sid: Optional[str]
    date_sent: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]


def send_message(phone_number: str, content: str, sender: str) -> ProviderResponse:
    if (
        is_not_production_environment()
        and current_app.config["TWILIO_DISABLED"] is True
    ):
        logger.info("Skipping Twilio request due to config")
        return _generate_mock_response()
    client = Client(
        current_app.config["TWILIO_ACCOUNT_SID"],
        current_app.config["TWILIO_AUTH_TOKEN"],
    )
    try:
        message: MessageInstance = client.messages.create(
            phone_number,
            body=content,
            from_=sender,
            status_callback=current_app.config["TWILIO_CALL_BACK_URL"],
        )
    except TwilioRestException as e:
        logger.exception(
            "Twilio failed to accept SMS request (status %d, code %d)", e.status, e.code
        )
        raise ServiceUnavailableException(e)
    response: ProviderResponse = {
        "status": None if message.status is None else str(message.status),
        "twilio_sid": message.sid,
        "date_sent": None if message.date_sent is None else str(message.date_sent),
        "error_code": message.error_code,
        "error_message": message.error_message,
    }
    logger.debug(
        "Sent message to Twilio (SID %s)",
        message.sid,
        extra={"twilio_details": response},
    )
    return response


def get_message(twilio_sid: str) -> Optional[ProviderResponse]:
    """
    Gets an update dict from the Twilio API. Returns `None` if there was an error getting the update.
    """
    if (
        is_not_production_environment()
        and current_app.config["TWILIO_DISABLED"] is True
    ):
        logger.info("Skipping Twilio request due to config")
        return _generate_mock_response(twilio_sid)
    client: Client = Client(
        current_app.config["TWILIO_ACCOUNT_SID"],
        current_app.config["TWILIO_AUTH_TOKEN"],
    )
    try:
        message: MessageInstance = client.messages.get(twilio_sid).fetch()
    except TwilioRestException:
        logger.warning(
            "Could not get updated status from Twilio for SID %s (error %s)",
            twilio_sid,
            exc_info=True,
        )
        return None
    response: ProviderResponse = {
        "status": None if message.status is None else str(message.status),
        "twilio_sid": message.sid,
        "date_sent": None if message.date_sent is None else str(message.date_sent),
        "error_code": message.error_code,
        "error_message": message.error_message,
    }
    logger.debug(
        "Got message from Twilio (SID %s)",
        message.sid,
        extra={"twilio_details": response},
    )
    return response


def redact_message_body(twilio_sid: str) -> bool:
    if (
        is_not_production_environment()
        and current_app.config["TWILIO_DISABLED"] is True
    ):
        logger.info("Skipping Twilio request due to config")
        return True
    client: Client = Client(
        current_app.config["TWILIO_ACCOUNT_SID"],
        current_app.config["TWILIO_AUTH_TOKEN"],
    )
    try:
        client.messages(twilio_sid).update(body="")
    except TwilioRestException as e:
        logger.exception(
            "Could not update SMS message in Twilio (status %d, code %d)",
            e.status,
            e.code,
        )
        return False
    logger.debug("Redacted message body in Twilio (SID %s)", twilio_sid)
    return True


def validate_twilio_signature(headers: Dict, params: Dict) -> None:
    """
    Twilio should have signed the request as described here:
    https://www.twilio.com/docs/usage/security#validating-requests
    """
    twilio_signature: str = headers.get(SECURITY_HEADER_NAME, "")
    is_valid: bool = RequestValidator(
        token=current_app.config["TWILIO_AUTH_TOKEN"]
    ).validate(
        uri=current_app.config["TWILIO_CALL_BACK_URL"],
        params=params,
        signature=twilio_signature,
    )
    if not is_valid:
        logger.info(
            "No valid %s header supplied",
            SECURITY_HEADER_NAME,
            extra={
                "request_url": current_app.config["TWILIO_CALL_BACK_URL"],
                "request_params": str(params),
                "twilio_signature": twilio_signature,
            },
        )
        raise PermissionError(f"No valid {SECURITY_HEADER_NAME} header supplied")


def _generate_mock_response(twilio_sid: Optional[str] = None) -> ProviderResponse:
    if twilio_sid is None:
        twilio_sid = generate_uuid()
    response: ProviderResponse = {
        "status": "sent",
        "twilio_sid": twilio_sid,
        "date_sent": str(datetime.utcnow()),
        "error_code": None,
        "error_message": None,
    }
    logger.debug(
        "Generated mock (SID %s)", twilio_sid, extra={"twilio_details": response}
    )
    return response
