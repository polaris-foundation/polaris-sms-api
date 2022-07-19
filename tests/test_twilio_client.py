import pytest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from flask import Flask
from mock import Mock
from pytest_mock import MockFixture

from dhos_sms_api.helpers import twilio_client


class TestTwilioClient:
    @pytest.fixture
    def mock_twilio_client(self, mocker: MockFixture) -> Mock:
        return mocker.patch("dhos_sms_api.helpers.twilio_client.Client")

    def test_send_message_disabled(
        self,
        app: Flask,
        mock_twilio_client: Mock,
        monkeypatch: MonkeyPatch,
        caplog: LogCaptureFixture,
    ) -> None:
        monkeypatch.setitem(app.config, "TWILIO_DISABLED", True)
        actual = twilio_client.send_message(
            phone_number="07777777777", content="some content", sender="GDm-Health"
        )
        assert mock_twilio_client.call_count == 0
        assert isinstance(actual, dict)
        assert "status" in actual
        assert "Generated mock" in caplog.messages[-1]

    def test_send_message_enabled(
        self,
        app: Flask,
        mock_twilio_client: Mock,
        monkeypatch: MonkeyPatch,
        caplog: LogCaptureFixture,
    ) -> None:
        monkeypatch.setitem(app.config, "TWILIO_DISABLED", False)
        actual = twilio_client.send_message(
            phone_number="07777777777", content="some content", sender="GDm-Health"
        )
        assert mock_twilio_client.call_count == 1
        assert isinstance(actual, dict)
        assert "status" in actual
        assert "Sent message to Twilio" in caplog.messages[-1]

    def test_get_message_disabled(
        self,
        app: Flask,
        mock_twilio_client: Mock,
        monkeypatch: MonkeyPatch,
        caplog: LogCaptureFixture,
    ) -> None:
        monkeypatch.setitem(app.config, "TWILIO_DISABLED", True)
        actual = twilio_client.get_message(twilio_sid="something")
        assert mock_twilio_client.call_count == 0
        assert isinstance(actual, dict)
        assert "status" in actual
        assert "Generated mock" in caplog.messages[-1]

    def test_get_message_enabled(
        self,
        app: Flask,
        mock_twilio_client: Mock,
        monkeypatch: MonkeyPatch,
        caplog: LogCaptureFixture,
    ) -> None:
        monkeypatch.setitem(app.config, "TWILIO_DISABLED", False)
        actual = twilio_client.get_message(twilio_sid="something")
        assert mock_twilio_client.call_count == 1
        assert isinstance(actual, dict)
        assert "status" in actual
        assert "Got message from Twilio" in caplog.messages[-1]

    def test_redact_message_body_disabled(
        self,
        app: Flask,
        mock_twilio_client: Mock,
        monkeypatch: MonkeyPatch,
        caplog: LogCaptureFixture,
    ) -> None:
        monkeypatch.setitem(app.config, "TWILIO_DISABLED", True)
        actual = twilio_client.redact_message_body(twilio_sid="something")
        assert mock_twilio_client.call_count == 0
        assert actual is True

    def test_redact_message_body_enabled(
        self,
        app: Flask,
        mock_twilio_client: Mock,
        monkeypatch: MonkeyPatch,
        caplog: LogCaptureFixture,
    ) -> None:
        monkeypatch.setitem(app.config, "TWILIO_DISABLED", False)
        actual = twilio_client.redact_message_body(twilio_sid="something")
        assert mock_twilio_client.call_count == 1
        assert actual is True
        assert "Redacted message body in Twilio" in caplog.messages[-1]
