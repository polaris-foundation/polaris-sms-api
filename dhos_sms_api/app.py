from pathlib import Path

import connexion
from connexion import FlaskApp
from flask import Flask
from flask_batteries_included import augment_app as fbi_augment_app
from flask_batteries_included.config import is_not_production_environment
from flask_batteries_included.sqldb import db, init_db
from she_logging import logger

from dhos_sms_api.blueprint_api import api_blueprint
from dhos_sms_api.blueprint_development import development
from dhos_sms_api.config import init_config
from dhos_sms_api.helpers.cli import add_cli_command


def create_app(
    testing: bool = False, use_pgsql: bool = True, use_sqlite: bool = False
) -> Flask:
    openapi_dir: Path = Path(__file__).parent / "openapi"
    connexion_app: FlaskApp = connexion.App(
        __name__,
        specification_dir=openapi_dir,
        options={"swagger_ui": is_not_production_environment()},
    )
    connexion_app.add_api("openapi.yaml", strict_validation=True)
    app: Flask = fbi_augment_app(
        app=connexion_app.app,
        use_pgsql=use_pgsql,
        use_sqlite=use_sqlite,
        use_auth0=False,
        testing=testing,
        use_jwt=False,
    )

    # Configure the SQL database
    init_db(app=app, testing=testing)

    init_config(app)

    # API blueprint registration
    app.register_blueprint(api_blueprint)
    app.logger.info("Registered API blueprint")

    # Register development endpoint if in a lower environment
    if is_not_production_environment():
        app.register_blueprint(development)
        logger.info("Registered development blueprint")

    if testing:
        with app.app_context():
            db.create_all()

    add_cli_command(app)

    logger.info("App ready to serve requests")

    return app
