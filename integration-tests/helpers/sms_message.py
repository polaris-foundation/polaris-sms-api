from typing import Any, Dict, Optional

from faker import Faker


def get_body(**kwargs: Optional[Dict]) -> Dict:
    fake: Faker = Faker()
    default_body: Dict[str, Any] = {
        "content": fake.text(),
        "error_code": str(fake.random_number(digits=5)),
        "error_message": fake.sentence(),
        "receiver": fake.phone_number(),
        "sender": fake.phone_number(),
        "status": "sent",
    }
    return {**default_body, **kwargs}
