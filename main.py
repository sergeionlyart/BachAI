import os
from app import app, start_background_services

# For deployment compatibility
if os.environ.get('DEPLOYMENT_TARGET') == 'autoscale':
    # In deployment, background services are handled by gunicorn config
    pass
elif __name__ == '__main__':
    # Start background services when running directly in development
    with app.app_context():
        start_background_services()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
