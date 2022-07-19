from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_batteries_included.helpers.apispec import (
    FlaskBatteriesPlugin,
    Identifier,
    initialise_apispec,
    openapi_schema,
)
from marshmallow import EXCLUDE, Schema, fields
from marshmallow.validate import Length

dhos_sms_api_spec: APISpec = APISpec(
    version="1.1.0",
    openapi_version="3.0.3",
    title="DHOS SMS API",
    info={"description": "The DHOS SMS API is responsible for sending SMS messages."},
    plugins=[FlaskPlugin(), MarshmallowPlugin(), FlaskBatteriesPlugin()],
)

initialise_apispec(dhos_sms_api_spec)


class SmsMessageSchema(Schema):
    class Meta:
        ordered = True

    sender = fields.String(
        required=True,
        description="UUID of the message sender",
        example="c75aa921-efc5-492e-a1c1-199f5bcb37a6",
    )
    receiver = fields.String(
        required=True,
        description="UUID of the message receiver",
        example="76fd30bb-9caf-4e79-8b2b-219ae63e8636",
    )
    content = fields.String(
        required=True,
        description="The message content",
        example="This is an SMS message",
        validate=Length(min=1),
    )
    status = fields.String(
        required=False,
        allow_none=True,
        description="The message status",
        example="sent",
    )
    error_code = fields.String(
        required=False,
        allow_none=True,
        description="The SMS message Twilio error code",
        example="30002",
    )
    error_message = fields.String(
        required=False,
        allow_none=True,
        description="The SMS message Twilio error message",
        example="The account has been suspended",
    )


@openapi_schema(dhos_sms_api_spec)
class SmsMessageRequest(SmsMessageSchema):
    class Meta:
        title = "SMS Message Request"
        unknown = EXCLUDE
        ordered = True


@openapi_schema(dhos_sms_api_spec)
class SmsMessageResponse(SmsMessageSchema, Identifier):
    class Meta:
        title = "SMS Message Response"
        unknown = EXCLUDE
        ordered = True

    twilio_sid = fields.String(
        required=True,
        description="Twilio identifier for the SMS message",
        example="12345678",
    )
    date_sent = fields.String(
        required=False,
        description="ISO8601 date at which SMS message was sent",
        example="2020-01-01T00:00:00.000Z",
    )
    trustomer_code = fields.String(
        required=False,
        description="Trustomer code with which SMS message is associated",
        example="ouh",
    )
    product_name = fields.String(
        required=False,
        description="Product name with which SMS message is associated",
        example="gdm",
    )


@openapi_schema(dhos_sms_api_spec)
class SmsMessageStatusReport(Schema):
    class Meta:
        title = "SMS Message Status Report"
        unknown = EXCLUDE
        ordered = True

    data_type = fields.String(
        required=True, description="The type of report", example="sms_status_counts"
    )
    description = fields.String(
        required=True,
        description="The report description",
        example="This is a count of the sms statuses",
    )
    measurement_timestamp = (
        fields.String(
            required=True,
            description="ISO8601 timestamp for the report's creation",
            example="2020-01-01T00:00:00.000Z",
        ),
    )
    data = fields.Dict(
        keys=fields.String(),
        values=fields.Dict(),
        description="The report data",
        example={"2019-11-14": {"Sent": 2, "Received": 1}, "2019-11-15": {"Read": 1}},
    )


@openapi_schema(dhos_sms_api_spec)
class CallbackRequest(Schema):
    """
    This schema is as described by Twilio, see https://www.twilio.com/docs/sms/twiml#request-parameters
    """

    class Meta:
        title = "Callback request"
        unknown = EXCLUDE
        ordered = True

    MessageSid = fields.String(
        required=True,
        description="A 34 character unique identifier for the message",
        example="AC3e553964a4935f4c505b451f0f3fd64e",
    )
    MessageStatus = fields.String(
        required=True,
        description="The status of the message",
        example="delivered",
    )
    ErrorCode = fields.String(
        required=False,
        allow_none=True,
        description="The error code (if any) associated with the message",
        example="30001",
    )
    ErrorMessage = fields.String(
        required=False,
        allow_none=True,
        description="Message describing the error (if any)",
        example="Failed to deliver",
    )
    DateSend = fields.String(
        required=False,
        allow_none=True,
        description="A string representation of the date the message was",
        example="Failed to deliver",
    )

    # We never use these, but Twilio sends them so we need to be aware.
    SmsSid = fields.String(allow_none=True)
    To = fields.String(allow_none=True)
    From = fields.String(allow_none=True)
    ApiVersion = fields.String(allow_none=True)
    SmsStatus = fields.String(allow_none=True)
    AccountSid = fields.String(allow_none=True)
    MessagingServiceSid = fields.String(allow_none=True)
    Body = fields.String(allow_none=True)
    NumMedia = fields.String(allow_none=True)
    ChannelInstallSid = fields.String(allow_none=True)
    ChannelStatusMessage = fields.String(allow_none=True)
    EventType = fields.String(allow_none=True)
    ChannelPrefix = fields.String(allow_none=True)
