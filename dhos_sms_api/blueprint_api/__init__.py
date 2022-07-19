from typing import Dict, Optional

from flask import Blueprint, Response, jsonify, make_response, request

from dhos_sms_api.blueprint_api import controller
from dhos_sms_api.helpers import twilio_client

api_blueprint = Blueprint("api", __name__)


@api_blueprint.route("/dhos/v1/sms", methods=["POST"])
def create_message(message_details: Dict) -> Response:
    """
    ---
    post:
      summary: Send SMS message
      description: Create and send an SMS message with the details provided in the request body
      tags: [sms]
      requestBody:
        description: SMS message details
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SmsMessageRequest'
              x-body-name: message_details
      parameters:
        - description: Trustomer code
          in: header
          name: X-Trustomer
          required: true
          schema:
            example: ouh
            type: string
        - description: Product name
          in: header
          name: X-Product
          required: true
          schema:
            example: gdm
            type: string
      responses:
        '200':
          description: Sent SMS message
          content:
            application/json:
              schema: SmsMessageResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    message_details["trustomer_code"] = request.headers["X-Trustomer"].lower()
    message_details["product_name"] = request.headers["X-Product"].lower()
    return jsonify(controller.create_message(message_details))


@api_blueprint.route("/dhos/v1/sms/<message_id>", methods=["GET"])
def get_message_by_uuid(message_id: str) -> Response:
    """
    ---
    get:
      summary: Get SMS message by UUID
      description: Get the SMS message with the UUID provided in the request
      tags: [sms]
      parameters:
        - name: message_id
          in: path
          description: Message UUID
          required: true
          schema:
            type: string
            example: acd39afe-4583-401c-ae99-62227d0a86ed
      responses:
        '200':
          description: The SMS message
          content:
            application/json:
              schema: SmsMessageResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(controller.get_message_by_uuid(message_id))


@api_blueprint.route("/dhos/v1/sms", methods=["GET"])
def get_all_messages(
    receiver: Optional[str] = None,
    limit: Optional[int] = None,
) -> Response:
    """
    ---
    get:
      summary: Get all SMS messages
      description: Get all SMS messages including details of when they were sent and their status.
      tags: [sms]
      parameters:
        - description: Trustomer code
          in: header
          name: X-Trustomer
          required: true
          schema:
            example: ouh
            type: string
        - description: Product name
          in: header
          name: X-Product
          required: true
          schema:
            example: gdm
            type: string
        - name: receiver
          in: query
          description: SMS receiver phone number to filter SMS messages to
          required: false
          schema:
            type: string
            example: '+447123456789'
        - name: limit
          in: query
          description: Number of SMS messages to limit response to (defaults to no limit)
          required: false
          schema:
            type: integer
            example: 5
      responses:
        '200':
          description: List of SMS messages
          content:
            application/json:
              schema:
                type: array
                items: SmsMessageResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    trustomer_code: str = request.headers["X-Trustomer"].lower()
    product_name: str = request.headers["X-Product"].lower()
    return jsonify(
        controller.get_all_messages(
            trustomer_code=trustomer_code,
            product_name=product_name,
            receiver=receiver,
            limit=limit,
        )
    )


@api_blueprint.route("/dhos/v1/sms_status_counts", methods=["GET"])
def get_message_status_counts(
    start_date: str,
    end_date: str,
    trustomer_code: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Response:
    """
    ---
    get:
      summary: Get SMS message status report
      description: >-
        Get a summary of the SMS messages sent between two dates. The results are
        reported per day, and include the SMS message statuses.
      tags: [sms]
      parameters:
        - name: start_date
          description: ISO8601 start date for SMS message counts
          in: query
          required: true
          schema:
            type: string
            example: 2020-01-01T00:00:00.000Z
        - name: end_date
          description: ISO8601 end date for SMS message counts
          in: query
          required: true
          schema:
            type: string
            example: 2020-02-01T00:00:00.000Z
        - name: trustomer_code
          in: query
          description: Trustomer code to filter SMS messages to
          required: false
          schema:
            type: string
            example: ouh
        - name: product_name
          in: query
          description: Product name to filter SMS messages to
          required: false
          schema:
            type: string
            example: gdm
      responses:
        200:
          description: SMS message status report
          content:
            application/json:
              schema: SmsMessageStatusReport
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.get_message_status_counts(
            start_date,
            end_date,
            trustomer_code=trustomer_code,
            product_name=product_name,
        )
    )


@api_blueprint.route("/dhos/v1/sms/<message_id>", methods=["DELETE"])
def delete_message(message_id: str) -> Response:
    """
    ---
    delete:
      summary: Delete message by UUID
      description: Delete the message with the provided UUID
      tags: [sms]
      parameters:
        - name: message_id
          in: path
          description: Message UUID
          required: true
          schema:
            type: string
            example: acd39afe-4583-401c-ae99-62227d0a86ed
        - description: Trustomer code
          in: header
          name: X-Trustomer
          required: true
          schema:
            example: ouh
            type: string
        - description: Product name
          in: header
          name: X-Product
          required: true
          schema:
            example: gdm
            type: string
      responses:
        '200':
          description: The deleted SMS message
          content:
            application/json:
              schema: SmsMessageResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.delete_message(
            message_id,
            trustomer_code=request.headers["X-Trustomer"].lower(),
            product_name=request.headers["X-Product"].lower(),
        )
    )


@api_blueprint.route("/dhos/v1/sms/callback", methods=["POST"])
def sms_callback() -> Response:
    """
    ---
    post:
      summary: Update SMS message status
      description: >-
        Update the status of an SMS message. This is the callback endpoint which Twilio is asked to
        hit when the status of a message in Twilio is updated. Note the Twilio authentication via
        header.
      tags: [sms]
      requestBody:
        description: SMS message update
        required: true
        content:
          application/x-www-form-urlencoded:
            schema: CallbackRequest
      responses:
        '204':
          description: Status updated
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    # Authorise request - check there is a valid signature in the header.
    twilio_client.validate_twilio_signature(
        headers=dict(request.headers), params=dict(request.values)
    )

    controller.sms_callback(request.values.to_dict())
    return make_response("", 204)


@api_blueprint.route("/dhos/v1/sms/bulk_update", methods=["POST"])
def sms_bulk_update() -> Response:
    """
    ---
    get:
      summary: Bulk update SMS message status from Twilio
      description: >-
        Update the status of all known incomplete SMS messages using the Twilio API.
        Note: only updates messages sent in the last 7 days.
      tags: [sms]
      responses:
        '204':
          description: Status updated
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    controller.sms_bulk_update()
    return make_response("", 204)
