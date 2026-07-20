from flask import Flask

from support_api.api.blueprints.tickets import bp as ticket_bp
from support_api.logging import configure_logging

def create_app() -> Flask:
    """Main entrypoint for the creation of the flask app."""
    # on app startup first we want to configure our logs so that resource logs are
    # owned by structlog.
    configure_logging()

    # __name__ tells flask where it is in our file structure
    app = Flask(__name__)

    # mount the blueprints to the flask app to allow them to be accessable.
    app.register_blueprint(ticket_bp, url_prefix="/tickets") # localhost:5000/tickets
    # url_prefix defines what the routes for this registration start with

    # tiny top level route for smoke-testing
    @app.route("/", methods=["GET"]) # root
    def index() -> dict[str, str]:
        return {"service": "support-api", "version": "1.0.0"}
    
    return app
