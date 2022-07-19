from flask_batteries_included.sqldb import db
from sqlalchemy.orm import Session


def reset_database() -> None:
    session: Session = db.session
    session.execute("TRUNCATE TABLE message")
    session.commit()
    session.close()
