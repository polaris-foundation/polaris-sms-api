from datetime import datetime
from typing import Any, Dict

import requests
from environs import Env
from requests import Response
from twilio.request_validator import RequestValidator


def _get_base_url() -> str:
    base_url: str = Env().str("DHOS_SMS_BASE_URL", "http://dhos-sms-api:5000")
    return f"{base_url}/dhos/v1/sms"


def _get_auth_headers() -> Dict[str, str]:
    return {
        "X-Trustomer": Env().str("CUSTOMER_CODE").lower(),
        "X-Product": Env().str("PRODUCT_NAME").lower(),
    }


def create_message(message_details: Dict) -> Response:
    return requests.post(
        _get_base_url(),
        timeout=15,
        headers=_get_auth_headers(),
        json=message_details,
    )


def get_message(message_uuid: str) -> Response:
    return requests.get(
        f"{_get_base_url()}/{message_uuid}",
        timeout=15,
        headers=_get_auth_headers(),
    )


def get_all_messages() -> Response:
    return requests.get(
        _get_base_url(),
        timeout=15,
        headers=_get_auth_headers(),
    )


def get_message_count(start_date: datetime, end_date: datetime) -> Response:
    counts_base_url: str = Env().str("DHOS_SMS_BASE_URL", "http://dhos-sms-api:5000")
    return requests.get(
        f"{counts_base_url}/dhos/v1/sms_status_counts",
        params={
            "start_date": start_date.isoformat(timespec="milliseconds"),
            "end_date": end_date.isoformat(timespec="milliseconds"),
        },
        timeout=15,
        headers=_get_auth_headers(),
    )


def bulk_update_messages() -> Response:
    return requests.get(
        f"{_get_base_url()}/bulk_update",
        timeout=15,
        headers=_get_auth_headers(),
    )


def process_message_callback(callback_details: Dict[str, Any]) -> Response:
    return requests.post(
        f"{_get_base_url()}/callback",
        timeout=15,
        headers={
            "X-Twilio-Signature": _calculate_twilio_signature(callback_details),
        },
        data=callback_details,
    )


def delete_message(message_uuid: str) -> Response:
    return requests.delete(
        f"{_get_base_url()}/{message_uuid}",
        timeout=15,
        headers=_get_auth_headers(),
    )


def _calculate_twilio_signature(params: Dict[str, Any]) -> str:
    env = Env()
    validator: RequestValidator = RequestValidator(env.str("TWILIO_AUTH_TOKEN"))
    return validator.compute_signature(env.str("TWILIO_CALL_BACK_URL"), params)
