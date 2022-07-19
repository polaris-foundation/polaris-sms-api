from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Generator, List

import pytest
from flask_batteries_included.sqldb import db
from mock import Mock
from pytest_mock import MockFixture

from dhos_sms_api.blueprint_api import controller
from dhos_sms_api.helpers import twilio_client
from dhos_sms_api.models.api_spec import SmsMessageResponse
from dhos_sms_api.models.message import Message


@pytest.mark.usefixtures("app")
class TestMessageController:
    @pytest.fixture
    def existing_messages(self) -> Generator[List[Message], None, None]:
        messages = [
            Message(
                sender="GDm-Health",
                receiver="+447123456789",
                content="Heyo :)",
                status="Sent",
                uuid="5",
                twilio_sid="twilio_sid",
                created=datetime(2019, 11, 14, 0, 0, 0, 0, tzinfo=timezone.utc),
                trustomer_code="tox",
                product_name="gdm",
            ),
            Message(
                sender="GDm-Health",
                receiver="+447777777777",
                content="Hey",
                status="Sent",
                uuid="1",
                twilio_sid="twilio_sid",
                created=datetime(2019, 11, 14, 0, 0, 0, 0, tzinfo=timezone.utc),
                trustomer_code="tox",
                product_name="gdm",
            ),
            Message(
                sender="GDm-Health",
                receiver="+447123456789",
                content="You be ill",
                status="Received",
                uuid="2",
                twilio_sid="twilio_sid",
                created=datetime(2019, 11, 14, 14, 0, 0, 0, tzinfo=timezone.utc),
                trustomer_code="tox",
                product_name="gdm",
            ),
            Message(
                sender="GDm-Health",
                receiver="+447123456789",
                content="waddup",
                status="Read",
                uuid="3",
                twilio_sid="twilio_sid",
                created=datetime(2019, 11, 15, 0, 0, 0, 0, tzinfo=timezone.utc),
                trustomer_code="tox",
                product_name="gdm",
            ),
            Message(
                sender="GDm-Health",
                receiver="+447777777777",
                content="?",
                status="Read",
                uuid="4",
                twilio_sid="twilio_sid",
                created=datetime(2019, 11, 16, 0, 11, 0, 0, tzinfo=timezone.utc),
                trustomer_code="different",
                product_name="different",
            ),
        ]
        db.session.add_all(messages)
        db.session.commit()

        yield messages

        db.session.query(Message).delete()
        db.session.commit()

    def test_create_message(
        self, message: Dict, mock_twilio_send: Mock, assert_valid_schema: Callable
    ) -> None:
        result = controller.create_message(message)
        assert result["content"] == message["content"]
        assert_valid_schema(SmsMessageResponse, result)
        mock_twilio_send.assert_called_with(
            phone_number=message["receiver"],
            content=message["content"],
            sender=message["sender"],
        )

    def test_create_message_with_optional_field(
        self, mock_twilio_send: Mock, assert_valid_schema: Callable
    ) -> None:
        message_optional = {
            "content": "Please submit feedback",
            "sender": "+15005550006",
            "receiver": "+447777777777",
            "trustomer_code": "tox",
            "product_name": "gdm",
            "status": "initiated",
        }
        result = controller.create_message(message_optional)
        assert result["content"] == message_optional["content"]
        assert_valid_schema(SmsMessageResponse, result)
        mock_twilio_send.assert_called_with(
            phone_number=message_optional["receiver"],
            content=message_optional["content"],
            sender=message_optional["sender"],
        )

    def test_get_message_by_uuid(
        self, message: Dict, assert_valid_schema: Callable
    ) -> None:
        message_response = controller.create_message(message)
        result = controller.get_message_by_uuid(message_response["uuid"])
        assert result == message_response
        assert_valid_schema(SmsMessageResponse, result)

    def test_get_all_messages(
        self, existing_messages: List[Dict], assert_valid_schema: Callable
    ) -> None:
        result = controller.get_all_messages()
        assert len(result) == 5
        assert_valid_schema(SmsMessageResponse, result, many=True)

    def test_get_all_messages_filter(
        self, existing_messages: List[Dict], assert_valid_schema: Callable
    ) -> None:
        result = controller.get_all_messages(receiver="+447123456789", limit=2)
        assert len(result) == 2
        assert_valid_schema(SmsMessageResponse, result, many=True)
        assert all(m["receiver"] == "+447123456789" for m in result)
        # Check messages are sorted by most recent.
        created_timestamps = [m["created"] for m in result]
        assert sorted(created_timestamps, reverse=True) == created_timestamps

    def test_sms_callback(self, message: Dict) -> None:
        existing_message = controller.create_message(message)
        controller.sms_callback(
            {
                "MessageSid": existing_message["twilio_sid"],
                "ErrorCode": "1234",
                "MessageStatus": "error",
            }
        )
        resulting_message = Message.query.filter_by(
            uuid=existing_message["uuid"]
        ).first()
        assert resulting_message.error_code == "1234"
        assert resulting_message.status == "error"

    @pytest.mark.parametrize(
        "status,redact_expected",
        [("error", False), ("sent", False), ("delivered", True)],
    )
    def test_sms_callback_redaction(
        self, mocker: MockFixture, message: Dict, status: str, redact_expected: bool
    ) -> None:
        mock_redact: Mock = mocker.patch.object(
            twilio_client, "redact_message_body", return_value=True
        )
        existing_message = controller.create_message(message)
        controller.sms_callback(
            {
                "MessageSid": existing_message["twilio_sid"],
                "MessageStatus": status,
            }
        )
        resulting_message = Message.query.filter_by(
            uuid=existing_message["uuid"]
        ).first()
        assert resulting_message.status == status
        if redact_expected:
            mock_redact.assert_called_with(existing_message["twilio_sid"])
            assert resulting_message.redacted is not None
        else:
            assert mock_redact.call_count == 0
            assert resulting_message.redacted is None

    def test_delete_message(self, message: Dict) -> None:
        existing_message = controller.create_message(message)
        result = controller.delete_message(
            existing_message["uuid"],
            trustomer_code=existing_message["trustomer_code"],
            product_name=existing_message["product_name"],
        )
        assert result["uuid"] == existing_message["uuid"]

    @pytest.mark.freeze_time("2019-11-14T00:00:00.000Z")
    def test_message_status_counts(self, existing_messages: List[Dict]) -> None:
        start_date = "2019-11-13T00:00:00.000Z"
        end_date = "2019-11-16T00:00:00.000Z"
        results = controller.get_message_status_counts(start_date, end_date)
        assert results == {
            "data_type": "sms_status_counts",
            "description": "This is a count of the sms statuses",
            "measurement_timestamp": "2019-11-14T00:00:00.000+00:00",
            "data": {
                "2019-11-14": {"Sent": 2, "Received": 1},
                "2019-11-15": {"Read": 1},
            },
        }

    @pytest.mark.freeze_time("2019-11-14T00:00:00.000Z")
    def test_message_status_counts_including_start_date(
        self, existing_messages: List[Dict]
    ) -> None:
        start_date = "2019-11-14T00:00:00.999Z"
        end_date = "2019-11-17T23:59:59.999Z"
        results = controller.get_message_status_counts(start_date, end_date)
        assert results == {
            "data_type": "sms_status_counts",
            "description": "This is a count of the sms statuses",
            "measurement_timestamp": "2019-11-14T00:00:00.000+00:00",
            "data": {
                "2019-11-14": {"Received": 1},
                "2019-11-15": {"Read": 1},
                "2019-11-16": {"Read": 1},
            },
        }

    @pytest.mark.freeze_time("2019-11-14T00:00:00.000Z")
    def test_message_status_counts_filter_trustomer_product(
        self, existing_messages: List[Dict]
    ) -> None:
        start_date = "1900-01-01T00:00:00.000Z"
        end_date = "2100-01-01T00:00:00.000Z"
        results = controller.get_message_status_counts(
            start_date, end_date, trustomer_code="different", product_name="different"
        )
        assert results == {
            "data_type": "sms_status_counts",
            "description": "This is a count of the sms statuses",
            "measurement_timestamp": "2019-11-14T00:00:00.000+00:00",
            "data": {
                "2019-11-16": {"Read": 1},
            },
        }

    def test_sms_bulk_update_messages(self, mocker: MockFixture) -> None:
        messages = [
            Message(
                sender="GDm-Health",
                receiver="+447123456789",
                content="Heyo :)",
                status="Sent",
                uuid="5",
                twilio_sid="twilio_sid",
                created=datetime.now(tz=timezone.utc) - timedelta(days=2),
                trustomer_code="tox",
                product_name="gdm",
            ),
            Message(
                sender="GDm-Health",
                receiver="+447123456789",
                content="Hey",
                status="Sent",
                uuid="1",
                twilio_sid="twilio_sid",
                created=datetime.now(tz=timezone.utc) - timedelta(days=1),
                trustomer_code="tox",
                product_name="gdm",
            ),
        ]
        db.session.add_all(messages)
        db.session.commit()
        update = {
            "status": "delivered",
            "twilio_sid": "whatever",
            "date_sent": None,
            "error_code": None,
            "error_message": None,
        }
        mock_get: Mock = mocker.patch.object(
            twilio_client, "get_message", return_value=update
        )
        mock_redact: Mock = mocker.patch.object(
            twilio_client, "redact_message_body", return_value=True
        )
        controller.sms_bulk_update()
        assert mock_get.call_count == 2
        assert mock_redact.call_count == 2
        for message in Message.query.all():
            assert message.status == "delivered"
            assert message.redacted is not None

    def test_sms_bulk_update_old_messages_not_updated(
        self, mocker: MockFixture, existing_messages: Dict
    ) -> None:
        """
        Tests that mock is not called when the only messages in the database are more than 7 days old.
        """
        mock_get: Mock = mocker.patch.object(twilio_client, "get_message")
        controller.sms_bulk_update()
        assert len(Message.query.all()) > 0
        assert mock_get.call_count == 0

    def test_sms_bulk_update_messages_errors(self, mocker: MockFixture) -> None:
        message = Message(
            sender="GDm-Health",
            receiver="+447123456789",
            content="Heyo :)",
            status="Sent",
            uuid="5",
            twilio_sid="twilio_sid",
            created=datetime.now(tz=timezone.utc) - timedelta(days=2),
            trustomer_code="tox",
            product_name="gdm",
        )

        db.session.add(message)
        db.session.commit()
        mock_get: Mock = mocker.patch.object(
            twilio_client, "get_message", return_value=None
        )
        controller.sms_bulk_update()
        assert mock_get.call_count == 1

    def test_sms_bulk_update_redaction(self, mocker: MockFixture) -> None:
        message_complete_redacted = Message(
            sender="GDm-Health",
            receiver="+447123456789",
            content="Heyo :)",
            status="delivered",
            uuid="uuid_1",
            twilio_sid="twilio_sid_1",
            created=datetime.now(tz=timezone.utc) - timedelta(days=2),
            trustomer_code="tox",
            product_name="gdm",
            redacted=datetime.utcnow(),
        )
        message_complete_unredacted = Message(
            sender="GDm-Health",
            receiver="+447123456789",
            content="Heyo :)",
            status="delivered",
            uuid="uuid_2",
            twilio_sid="twilio_sid_2",
            created=datetime.now(tz=timezone.utc) - timedelta(days=2),
            trustomer_code="tox",
            product_name="gdm",
        )
        message_incomplete = Message(
            sender="GDm-Health",
            receiver="+447123456789",
            content="Heyo :)",
            status="Sent",
            uuid="uuid_3",
            twilio_sid="twilio_sid_3",
            created=datetime.now(tz=timezone.utc) - timedelta(days=2),
            trustomer_code="tox",
            product_name="gdm",
        )

        db.session.add_all(
            [message_complete_redacted, message_complete_unredacted, message_incomplete]
        )
        db.session.commit()
        update = {
            "status": "sent",
            "twilio_sid": "twilio_sid_3",
            "date_sent": None,
            "error_code": None,
            "error_message": None,
        }
        mock_get: Mock = mocker.patch.object(
            twilio_client, "get_message", return_value=update
        )
        mock_redact: Mock = mocker.patch.object(
            twilio_client, "redact_message_body", return_value=True
        )
        controller.sms_bulk_update()
        assert mock_get.call_count == 1
        assert mock_redact.call_count == 1
        assert mock_redact.call_count == 1
        mock_redact.assert_called_with(message_complete_unredacted.twilio_sid)
        assert (
            Message.query.filter_by(uuid=message_complete_unredacted.uuid)
            .first()
            .redacted
            is not None
        )
