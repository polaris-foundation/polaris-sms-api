from typing import Dict

from _pytest.logging import LogCaptureFixture
from flask import Flask
from flask.testing import FlaskClient
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import ServiceUnavailableException
from mock import Mock
from pytest_mock import MockFixture
from twilio.request_validator import RequestValidator

from dhos_sms_api.blueprint_api import controller
from dhos_sms_api.helpers import twilio_client


class TestApi:
    def _generate_twilio_signature(self, config: Dict, params: Dict) -> str:
        return RequestValidator(token=config["TWILIO_AUTH_TOKEN"]).compute_signature(
            uri=config["TWILIO_CALL_BACK_URL"], params=params
        )

    def test_create_message(
        self, client: FlaskClient, mocker: MockFixture, message: Dict
    ) -> None:
        mock_get: Mock = mocker.patch.object(
            controller,
            "create_message",
            return_value={**message, "uuid": generate_uuid()},
        )
        response = client.post(
            "/dhos/v1/sms",
            json=message,
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        mock_get.assert_called_with(
            {
                **message,
                "trustomer_code": "some_trustomer_code",
                "product_name": "some_product_name",
            }
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["content"] == message["content"]

    def test_create_message_no_headers(
        self, client: FlaskClient, message: Dict
    ) -> None:
        response = client.post("/dhos/v1/sms", json=message)
        assert response.status_code == 400

    def test_create_message_with_optional_field(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        message_optional = {
            "content": "Please submit feedback",
            "sender": "+15005550006",
            "receiver": "+447777777777",
            "status": "initiated",
        }
        mock_get: Mock = mocker.patch.object(
            controller,
            "create_message",
            return_value={**message_optional, "uuid": generate_uuid()},
        )
        response = client.post(
            "/dhos/v1/sms",
            json=message_optional,
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        mock_get.assert_called_with(
            {
                **message_optional,
                "trustomer_code": "some_trustomer_code",
                "product_name": "some_product_name",
            }
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["content"] == message_optional["content"]

    def test_create_message_with_bad_field(self, client: FlaskClient) -> None:
        message_bad = {
            "content": "Please submit feedback",
            "sender": "+15005550006",
            "receiver": "+447777777777",
            "bad": "rubbish",
        }
        response = client.post(
            "/dhos/v1/sms",
            json=message_bad,
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        assert response.status_code == 400

    def test_create_message_with_empty_field(self, client: FlaskClient) -> None:
        message_empty = {
            "content": "",
            "sender": "+15005550006",
            "receiver": "+447777777777",
        }
        response = client.post(
            "/dhos/v1/sms",
            json=message_empty,
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        assert response.status_code == 400

    def test_create_message_with_error(self, client: FlaskClient) -> None:
        message_twilio_error = {
            "content": "",
            "sender": "+123",
            "receiver": "+447777777777",
        }
        response = client.post(
            "/dhos/v1/sms",
            json=message_twilio_error,
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        assert response.status_code == 400

    def test_create_message_post_twilio_client_failure(
        self, client: FlaskClient, message: Dict, mock_twilio_send: Mock
    ) -> None:
        mock_twilio_send.side_effect = ServiceUnavailableException
        response = client.post(
            "/dhos/v1/sms",
            json=message,
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        assert response.status_code == 503

    def test_get_message_by_uuid(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        expected = {"some": "message"}
        message_uuid: str = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            controller, "get_message_by_uuid", return_value=expected
        )
        response = client.get(f"/dhos/v1/sms/{message_uuid}")
        mock_get.assert_called_with(message_uuid)
        assert response.status_code == 200
        assert response.json == expected

    def test_get_all_messages(self, client: FlaskClient, mocker: MockFixture) -> None:
        mock_get: Mock = mocker.patch.object(
            controller, "get_all_messages", return_value=[{"uuid": generate_uuid()}]
        )
        response = client.get(
            "/dhos/v1/sms",
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        assert mock_get.call_count == 1
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json) == 1

    def test_get_all_messages_filtered(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        mock_get: Mock = mocker.patch.object(
            controller, "get_all_messages", return_value=[{"uuid": generate_uuid()}]
        )
        response = client.get(
            "/dhos/v1/sms?receiver=%2B447123456789&limit=5",
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        assert mock_get.call_count == 1
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json) == 1
        mock_get.assert_called_with(
            trustomer_code="some_trustomer_code",
            product_name="some_product_name",
            receiver="+447123456789",
            limit=5,
        )

    def test_sms_callback(
        self, app: Flask, client: FlaskClient, mocker: MockFixture
    ) -> None:
        mock_callback: Mock = mocker.patch.object(controller, "sms_callback")
        params = {
            "MessageSid": "twilio_sid",
            "ErrorCode": "1234",
            "ErrorMessage": "Wow an error",
            "MessageStatus": "error",
        }
        callback_response = client.post(
            "/dhos/v1/sms/callback",
            data=params,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Twilio-Signature": self._generate_twilio_signature(
                    app.config, params
                ),
            },
        )
        assert callback_response.status_code == 204
        assert mock_callback.call_count == 1
        mock_callback.assert_called_with(params)

    def test_sms_callback_missing_sid(self, app: Flask, client: FlaskClient) -> None:
        params = {"status": "error"}
        callback_response = client.post(
            "/dhos/v1/sms/callback",
            data=params,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Twilio-Signature": self._generate_twilio_signature(
                    app.config, params
                ),
            },
        )
        assert callback_response.status_code == 400

    def test_sms_callback_wrong_security_header(
        self, client: FlaskClient, caplog: LogCaptureFixture
    ) -> None:
        params = {
            "MessageSid": "twilio_sid",
            "ErrorCode": "1234",
            "ErrorMessage": "Wow an error",
            "MessageStatus": "error",
        }
        callback_response = client.post(
            "/dhos/v1/sms/callback",
            data=params,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Twilio-Signature": "abcde",
            },
        )
        assert callback_response.status_code == 403
        assert (
            f"No valid {twilio_client.SECURITY_HEADER_NAME} header supplied"
            in caplog.text
        )

    def test_delete_message(self, client: FlaskClient, mocker: MockFixture) -> None:
        message_uuid: str = generate_uuid()
        mock_delete: Mock = mocker.patch.object(
            controller, "delete_message", return_value={"uuid": message_uuid}
        )
        response = client.delete(
            f"/dhos/v1/sms/{message_uuid}",
            headers={
                "X-Trustomer": "some_trustomer_code",
                "X-Product": "some_product_name",
            },
        )
        mock_delete.assert_called_with(
            message_uuid,
            trustomer_code="some_trustomer_code",
            product_name="some_product_name",
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == message_uuid

    def test_delete_message_no_trustomer_header(self, client: FlaskClient) -> None:
        message_uuid: str = generate_uuid()
        response = client.delete(
            f"/dhos/v1/sms/{message_uuid}",
            headers={
                "X-Product": "some_product_name",
            },
        )
        assert response.status_code == 400

    def test_get_message_status_counts(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        expected = {"some": "data"}
        mock_get: Mock = mocker.patch.object(
            controller, "get_message_status_counts", return_value=expected
        )
        response = client.get(
            f"/dhos/v1/sms_status_counts?start_date=2019-11-13T00:00:00.000Z&end_date=2019-11-16T00:00:00.000Z&trustomer_code=test&product_name=tst"
        )
        mock_get.assert_called_with(
            "2019-11-13T00:00:00.000Z",
            "2019-11-16T00:00:00.000Z",
            trustomer_code="test",
            product_name="tst",
        )
        assert response.status_code == 200
        assert response.json == expected

    def test_sms_bulk_update(self, client: FlaskClient, mocker: MockFixture) -> None:
        mock_update: Mock = mocker.patch.object(
            controller,
            "sms_bulk_update",
        )
        response = client.post("/dhos/v1/sms/bulk_update")
        assert mock_update.call_count == 1
        assert response.status_code == 204
