import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.logging_config import setup_logging
from routes.api import api_bp
from routes.polling_api import polling_bp
from database.models import db

# Setup logging
setup_logging()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Initialize models and create tables
with app.app_context():
    # Import models to register them with db
    from database.models import BatchJob, BatchLot, BatchResult, WebhookDelivery  # noqa: F401
    
    # Create all tables
    db.create_all()
    logging.info("Database tables created successfully")

# Register blueprints
app.register_blueprint(api_bp)
app.register_blueprint(polling_bp, url_prefix='/api/v1')

# Import and register simple jobs API for polling clients
from routes.jobs_api import jobs_bp
app.register_blueprint(jobs_bp)

# Import and register webhook monitoring API
from routes.webhook_monitoring import webhook_monitoring_bp
app.register_blueprint(webhook_monitoring_bp)

# Import and register test webhook endpoint for testing
from routes.test_webhook import test_webhook_bp
app.register_blueprint(test_webhook_bp)

# Root route for documentation
@app.route('/')
def index():
    from flask import render_template
    return render_template('index.html')

@app.route('/docs')
def api_docs():
    from flask import render_template
    return render_template('api_docs.html')

# Health check endpoint
@app.route('/health')
def health():
    return {"status": "healthy", "service": "generation-service"}, 200

# Start background worker
def start_background_services():
    """Start background services for production"""
    try:
        from services.background_worker import BackgroundWorker
        global _background_worker
        _background_worker = BackgroundWorker(flask_app=app)
        _background_worker.start()
        logging.info("Background worker started successfully")
    except Exception as e:
        logging.error(f"Failed to start background worker: {str(e)}")

# Global background worker instance
_background_worker = None

# Initialize background services
start_background_services()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
