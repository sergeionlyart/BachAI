import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.logging_config import setup_logging
from routes.api import api_bp

# Setup logging
setup_logging()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Register blueprints
app.register_blueprint(api_bp)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
