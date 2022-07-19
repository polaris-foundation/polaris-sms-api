from datetime import datetime
from typing import Any, Dict

from flask_batteries_included.sqldb import ModelIdentifier, db

from dhos_sms_api.query.softdelete import QueryWithSoftDelete


class Message(ModelIdentifier, db.Model):
    query_class = QueryWithSoftDelete

    # required
    sender = db.Column(db.String, unique=False, nullable=False)
    receiver = db.Column(db.String, unique=False, nullable=False, index=True)
    content = db.Column(db.String, unique=False, nullable=False)
    twilio_sid = db.Column(db.String, unique=False, nullable=False)
    trustomer_code = db.Column(db.String, unique=False, nullable=False, index=True)
    product_name = db.Column(db.String, unique=False, nullable=False, index=True)

    # optional
    status = db.Column(db.String, unique=False, nullable=True, index=True)
    error_code = db.Column(db.String, unique=False, nullable=True)
    error_message = db.Column(db.String, unique=False, nullable=True)
    date_sent = db.Column(db.String, unique=False, nullable=True)

    # system
    deleted = db.Column(db.DateTime, unique=False, nullable=True)
    redacted = db.Column(db.DateTime, unique=False, nullable=True, index=True)

    def __init__(self, **kwargs: Any) -> None:
        # Constructor to satisfy linters.
        super(Message, self).__init__(**kwargs)

    @staticmethod
    def schema() -> Dict:
        return {
            "optional": {
                "status": str,
                "error_code": str,
                "error_message": str,
                "twilio_sid": str,
                "date_sent": str,
            },
            "required": {
                "sender": str,
                "receiver": str,
                "content": str,
                "trustomer_code": str,
                "product_name": str,
            },
            "updatable": {
                "status": str,
                "error_code": str,
                "error_message": str,
                "date_sent": str,
            },
        }

    def to_dict(self) -> Dict:
        schema = self.schema()
        message = {}
        for key in schema["required"]:
            message[key] = getattr(self, key)

        for key in schema["optional"]:
            value = getattr(self, key)
            if value is not None:
                message[key] = value

        if self.deleted is not None:
            message["deleted"] = self.deleted
        if self.redacted is not None:
            message["redacted"] = self.redacted
        msg = {**message, **self.pack_identifier()}

        return msg

    def to_redacted_dict(self) -> Dict[str, Any]:
        return {"uuid": self.uuid, "twilio_sid": self.twilio_sid, "status": self.status}

    def delete(self) -> Dict[str, Any]:
        self.deleted = datetime.utcnow()
        db.session.commit()
        return self.to_dict()
