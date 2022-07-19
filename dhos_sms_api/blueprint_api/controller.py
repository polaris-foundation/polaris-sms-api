from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import phonenumbers
from flask import current_app
from flask_batteries_included.helpers.timestamp import (
    parse_iso8601_to_datetime_typesafe,
)
from flask_batteries_included.sqldb import db, generate_uuid
from she_logging import logger
from sqlalchemy import String, and_, cast, func

from dhos_sms_api.helpers import twilio_client
from dhos_sms_api.helpers.twilio_client import ProviderResponse
from dhos_sms_api.models.message import Message

# Twilio statuses - accepted, queued, sending, sent, delivered, undelivered, or failed
TWILIO_TERMINAL_SMS_STATUSES = ["delivered", "undelivered", "failed"]


def create_message(message_details: Dict) -> Dict:
    logger.debug("Creating SMS message", extra={"sms_message_data": message_details})
    message_model: Message = Message(uuid=generate_uuid(), **message_details)

    base_number: phonenumbers.PhoneNumber = phonenumbers.parse(
        message_model.receiver, current_app.config["COUNTRY_CODE"]
    )
    e164_phone_number: str = phonenumbers.format_number(
        base_number, phonenumbers.PhoneNumberFormat.E164
    )
    provider_response: ProviderResponse = twilio_client.send_message(
        phone_number=e164_phone_number,
        content=message_model.content,
        sender=message_model.sender,
    )

    message_model.status = provider_response["status"]
    message_model.twilio_sid = provider_response["twilio_sid"]

    if provider_response["date_sent"] is not None:
        message_model.date_sent = provider_response["date_sent"]

    if provider_response["error_code"] is not None:
        message_model.error_code = provider_response["error_code"]
        message_model.error_message = provider_response["error_message"]

    db.session.add(message_model)
    db.session.commit()

    return message_model.to_dict()


def get_message_by_uuid(message_id: str) -> Dict:
    message_model: Message = Message.query.filter_by(uuid=message_id).first_or_404()
    return message_model.to_dict()


def get_all_messages(
    trustomer_code: Optional[str] = None,
    product_name: Optional[str] = None,
    receiver: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict]:
    message_query = Message.query.order_by(Message.created.desc())
    if trustomer_code:
        message_query = message_query.filter(Message.trustomer_code == trustomer_code)
    if product_name:
        message_query = message_query.filter(Message.product_name == product_name)
    if receiver:
        message_query = message_query.filter(Message.receiver == receiver)
    if limit:
        message_query = message_query.limit(limit)
    return [message_model.to_dict() for message_model in message_query]


def get_message_status_counts(
    start_date: str,
    end_date: str,
    trustomer_code: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Dict:
    start_dt: datetime = parse_iso8601_to_datetime_typesafe(start_date)
    end_dt: datetime = parse_iso8601_to_datetime_typesafe(end_date)

    counts_query = Message.query.with_entities(
        Message.status,
        func.substr(cast(Message.created, String()), 1, 10),
        func.count(Message.status),
    ).filter(and_(start_dt <= Message.created, Message.created <= end_dt))

    if trustomer_code:
        counts_query = counts_query.filter(Message.trustomer_code == trustomer_code)
    if product_name:
        counts_query = counts_query.filter(Message.product_name == product_name)

    message_counts: List[List] = counts_query.group_by(
        Message.status, func.substr(cast(Message.created, String()), 1, 10)
    ).all()
    data_dictionary: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for count in message_counts:
        # This is to convert the "data" key:value pair from list of tuples to change it to
        # a dictionary of dictionaries like this:
        # "data": {
        #     "2019-11-14": {"delivered": 2, "undelivered": 1},
        #     "2019-11-15": {"sent": 1},
        # }
        status: str = count[0]
        count_integer: int = count[2]
        date = count[1]
        data_dictionary[date][status] = count_integer

    return {
        "data_type": "sms_status_counts",
        "description": "This is a count of the sms statuses",
        "measurement_timestamp": datetime.now(tz=timezone.utc).isoformat(
            timespec="milliseconds"
        ),
        "data": data_dictionary,
    }


def delete_message(
    message_id: str, trustomer_code: str, product_name: str
) -> Dict[str, Any]:
    message: Message = Message.query.filter_by(uuid=message_id).first_or_404()
    if message.trustomer_code != trustomer_code or message.product_name != product_name:
        raise PermissionError(
            "Cannot modify an SMS message sent by another trustomer/product"
        )
    return message.delete()


def sms_callback(request_data: Dict) -> None:
    """
    Updates a single message with information from Twilio.
    """
    message_sid = request_data["MessageSid"]
    logger.info("Received callback for message with SID %s", message_sid)
    message: Optional[Message] = Message.query.filter_by(twilio_sid=message_sid).first()

    if not message:
        raise ValueError(f"Twilio SID {message_sid} not found")

    message.status = request_data.get("MessageStatus") or message.status
    message.date_sent = request_data.get("DateSend") or message.date_sent
    message.error_code = request_data.get("ErrorCode") or message.error_code
    message.error_message = request_data.get("ErrorMessage") or message.error_message
    db.session.commit()

    # If message status is terminal, attempt to redact the message body in Twilio.
    if message.status in TWILIO_TERMINAL_SMS_STATUSES:
        logger.debug("SMS message status is terminal, redacting body in Twilio")
        success: bool = twilio_client.redact_message_body(message.twilio_sid)
        if success:
            message.redacted = datetime.utcnow()
            db.session.commit()
        else:
            # Don't raise an exception here because we can retry later.
            logger.error("Failed to redact message in Twilio")


def sms_bulk_update() -> None:
    """
    Updates the status of all known incomplete Messages in the database that were created
    less than 7 days ago. Uses the Twilio API to ask for their most recent status.
    Also attempts to redact any un-redacted complete SMS messages in Twilio.
    """
    datetime_7_days_ago: datetime = datetime.now(tz=timezone.utc) - timedelta(days=7)
    incomplete_messages: List[Message] = (
        Message.query.filter(Message.status.notin_(TWILIO_TERMINAL_SMS_STATUSES))
        .filter(Message.created > datetime_7_days_ago)
        .all()
    )
    logger.info("Found %d incomplete SMS messages to update", len(incomplete_messages))
    for sms in incomplete_messages:
        logger.debug(
            "Requesting update for message %s (SID %s)", sms.uuid, sms.twilio_sid
        )
        message_update: Optional[ProviderResponse] = twilio_client.get_message(
            sms.twilio_sid
        )
        if message_update is None:
            logger.debug(
                "No update available for message %s (SID %s)", sms.uuid, sms.twilio_sid
            )
            continue

        sms.status = message_update["status"] or sms.status
        sms.date_sent = message_update["date_sent"] or sms.date_sent
        sms.error_code = message_update["error_code"] or sms.error_code
        sms.error_message = message_update["error_code"] or sms.error_message
        logger.debug("Updated message %s (SID %s)", sms.uuid, sms.twilio_sid)
    db.session.commit()

    unredacted_messages: List[Message] = (
        Message.query.filter(Message.status.in_(TWILIO_TERMINAL_SMS_STATUSES))
        .filter(Message.created > datetime_7_days_ago)
        .filter(Message.redacted.is_(None))
        .all()
    )
    logger.info(
        "Found %d un-redacted complete SMS messages to redact", len(unredacted_messages)
    )
    for sms in unredacted_messages:
        logger.debug(
            "Attempting to redact message %s (SID %s)", sms.uuid, sms.twilio_sid
        )
        success: bool = twilio_client.redact_message_body(sms.twilio_sid)
        if success:
            sms.redacted = datetime.utcnow()
        else:
            # Don't raise an exception here because we can retry later.
            logger.error("Failed to redact message in Twilio")
    db.session.commit()
