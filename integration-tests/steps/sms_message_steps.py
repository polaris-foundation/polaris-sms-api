import operator
from datetime import datetime, timedelta, timezone
from itertools import accumulate
from typing import Dict

from behave import step, then, use_step_matcher
from behave.runner import Context
from clients import database_client, sms_message_client
from environs import Env
from helpers import sms_message as message_helper
from requests import Response, codes

use_step_matcher("re")


@step("(?:an|another) SMS message is sent")
def send_new_message(context: Context) -> None:
    context.message_body = message_helper.get_body()
    response: Response = sms_message_client.create_message(
        message_details=context.message_body
    )
    response.raise_for_status()
    response_json: dict = response.json()

    assert "uuid" in response_json
    context.message_uuid = response_json["uuid"]
    assert "twilio_sid" in response_json
    context.twilio_sid = response_json["twilio_sid"]
    context.sent_messages.append(response_json)


@step("an SMS message has been delivered but not redacted")
def add_delivered_unredacted_message(context: Context) -> None:
    context.message_body = message_helper.get_body()
    context.message_body["status"] = "delivered"
    post_response: Response = sms_message_client.create_message(
        message_details=context.message_body
    )
    post_response.raise_for_status()

    # We have to go directly into the database to mark the message as delivered to get around the mocking.
    database_client.execute_query(
        "UPDATE message SET status='delivered' WHERE message.uuid=%(message_uuid)s",
        params={"message_uuid": post_response.json()["uuid"]},
    )

    get_response = sms_message_client.get_message(
        message_uuid=post_response.json()["uuid"]
    )
    get_response.raise_for_status()
    response_json: dict = get_response.json()

    assert "uuid" in response_json
    context.message_uuid = response_json["uuid"]
    assert "twilio_sid" in response_json
    assert "redacted" not in response_json
    assert response_json["status"] == "delivered"
    context.twilio_sid = response_json["twilio_sid"]
    context.sent_messages.append(response_json)


@step("the message (?P<can_or_can_not>.+) be retrieved by its uuid")
def get_message_by_uuid(context: Context, can_or_can_not: str) -> None:
    response: Response = sms_message_client.get_message(
        message_uuid=context.message_uuid
    )

    if can_or_can_not == "can":
        response.raise_for_status()
        context.api_message_body = response.json()
    else:
        assert response.status_code == codes.not_found


@step("the message (?P<can_or_can_not>.+) be seen in all messages")
def assert_message_in_all_messages(context: Context, can_or_can_not: str) -> None:
    response: Response = sms_message_client.get_all_messages()
    response.raise_for_status()
    all_ids: list = [q["uuid"] for q in response.json()]

    if can_or_can_not == "can":
        assert context.message_uuid in all_ids
    else:
        assert context.message_uuid not in all_ids


@step("the message matches that previously created")
def assert_message_body(context: Context) -> None:
    _assert_messages_are_identical(context.message_body, context.api_message_body)
    assert context.api_message_body["product_name"] == Env().str("PRODUCT_NAME").lower()
    assert (
        context.api_message_body["trustomer_code"] == Env().str("CUSTOMER_CODE").lower()
    )


@step('a message callback is received with status "(?P<status>\w+)"')
def update_message(context: Context, status: str) -> None:
    context.callback_update_body = {
        "MessageSid": context.twilio_sid,
        "MessageStatus": status,
    }
    response: Response = sms_message_client.process_message_callback(
        callback_details=context.callback_update_body
    )
    response.raise_for_status()
    assert response.status_code == codes.no_content


@step("a bulk update call is received")
def bulk_update(context: Context) -> None:
    response: Response = sms_message_client.bulk_update_messages()
    response.raise_for_status()


@step("the status of all incomplete messages is updated")
def assert_bulk_update_status(context: Context) -> None:
    response: Response = sms_message_client.get_all_messages()
    response.raise_for_status()

    all_statuses: dict = {m["uuid"]: m["status"] for m in response.json()}
    # Note that in test environment our client does not call twilio directly but instead returns
    # a mock message whose status is "sent". Assert that status of _all incomplete_ messages has been
    # changed to "sent" after bulk update.
    assert False not in [
        "sent" == all_statuses[m["uuid"]]
        for m in context.sent_messages
        if m["status"] not in ["delivered", "undelivered", "failed"]
    ]


@step("all complete message have been marked as redacted")
def assert_complete_messages_redacted(context: Context) -> None:
    response: Response = sms_message_client.get_all_messages()
    response.raise_for_status()
    assert all(
        m["redacted"] is not None
        for m in response.json()
        if m["status"] in ["delivered", "undelivered", "failed"]
    )


@step("the message status is updated accordingly")
def assert_message_status_updated(context: Context) -> None:
    response: Response = sms_message_client.get_message(
        message_uuid=context.message_uuid
    )
    response.raise_for_status()
    response_body: dict = response.json()
    assert response_body["status"] == context.callback_update_body["MessageStatus"]


@then("the message body has been marked as redacted")
def assert_message_body_redacted(context: Context) -> None:
    response: Response = sms_message_client.get_message(
        message_uuid=context.message_uuid
    )
    response.raise_for_status()
    response_body: dict = response.json()
    assert response_body["redacted"] is not None


@step("the message is deleted")
def delete_message(context: Context) -> None:
    response: Response = sms_message_client.delete_message(
        message_uuid=context.message_uuid
    )
    response.raise_for_status()


@step("(?:a|an) (?P<initial_or_final>initial|final) message count is taken")
def get_message_counts(context: Context, initial_or_final: str) -> None:
    response: Response = sms_message_client.get_message_count(
        start_date=datetime.now(tz=timezone.utc) - timedelta(minutes=5),
        end_date=datetime.now(tz=timezone.utc),
    )
    response.raise_for_status()
    response_json: dict = response.json()
    assert "data" in response_json
    setattr(context, f"{initial_or_final}_message_count", response_json["data"])


@step(
    'there (?:is|are) (?P<increment>\d+) new messages? with status "(?P<status>\w+)" counted'
)
def assert_message_count_incremented(
    context: Context,
    increment: str,
    status: str,
) -> None:
    assert _get_count_by_status(context.initial_message_count, status) + int(
        increment
    ) == _get_count_by_status(context.final_message_count, status)


def _get_count_by_status(counts: Dict[str, Dict], status: str) -> int:
    # discard the dates, in case we run just around the midnight
    return list(
        accumulate(
            [counts[date][status] if status in counts[date] else 0 for date in counts],
            operator.add,
        )
    ).pop()


def _assert_messages_are_identical(expected: dict, actual: dict) -> None:
    for attribute in expected:
        assert expected[attribute] == actual[attribute]
