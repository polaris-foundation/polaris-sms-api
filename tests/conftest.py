import json
from typing import Callable, Dict, Generator, List, Type, Union

import pytest
from flask import Flask
from flask_batteries_included.sqldb import db
from marshmallow import RAISE, Schema
from mock import Mock
from pytest_mock import MockFixture

from dhos_sms_api.helpers import twilio_client
from dhos_sms_api.helpers.twilio_client import ProviderResponse
from dhos_sms_api.models.message import Message


@pytest.fixture(scope="session")
def session_app() -> Flask:
    import dhos_sms_api.app

    return dhos_sms_api.app.create_app(testing=True)


@pytest.fixture
def app() -> Flask:
    """ "Fixture that creates app for testing"""
    from dhos_sms_api.app import create_app

    current_app = create_app(testing=True, use_pgsql=False, use_sqlite=True)
    return current_app


@pytest.fixture
def app_context(app: Flask) -> Generator[None, None, None]:
    with app.app_context():
        yield


@pytest.fixture
def assert_valid_schema(
    app: Flask,
) -> Callable[[Type[Schema], Union[Dict, List], bool], None]:
    def verify_schema(
        schema: Type[Schema], value: Union[Dict, List], many: bool = False
    ) -> None:
        # Roundtrip through JSON to convert datetime values to strings.
        serialised = json.loads(json.dumps(value, cls=app.json_encoder))
        schema().load(serialised, many=many, unknown=RAISE)

    return verify_schema


@pytest.fixture
def mock_twilio_send(mocker: MockFixture) -> Mock:
    return_value: ProviderResponse = {
        "status": "some_status",
        "twilio_sid": "some_sid",
        "date_sent": "some_date",
        "error_code": None,
        "error_message": None,
    }
    return mocker.patch.object(twilio_client, "send_message", return_value=return_value)


@pytest.fixture
def mock_twilio_get(mocker: MockFixture) -> Mock:
    return_value: ProviderResponse = {
        "status": "some_status",
        "twilio_sid": "some_sid",
        "date_sent": "some_date",
        "error_code": None,
        "error_message": None,
    }
    return mocker.patch.object(twilio_client, "get_message", return_value=return_value)


@pytest.fixture
def message() -> Generator[Dict, None, None]:
    yield {
        "content": "Please submit feedback",
        "sender": "+15005550006",
        "receiver": "+447777777777",
        "trustomer_code": "tox",
        "product_name": "gdm",
    }
    db.session.query(Message).delete()
    db.session.commit()
