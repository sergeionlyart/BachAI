#!/usr/bin/env python3
"""
Production deployment entry point
"""

import os
from app import app, start_background_services

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('ENABLE_BACKGROUND_SERVICES', 'true')

# Enhanced health check for deployment (separate from app.py)
@app.route('/deploy-health')
def deploy_health_check():
    """Enhanced health check for deployment"""
    try:
        # Check database connection
        from database.models import db
        from sqlalchemy import text
        with app.app_context():
            db.session.execute(text('SELECT 1'))
        
        return {
            "status": "healthy",
            "service": "generation-service",
            "version": "2.0",
            "database": "connected"
        }, 200
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "generation-service",
            "error": str(e)
        }, 503

if __name__ == '__main__':
    # Start background services for production
    with app.app_context():
        start_background_services()
    
    # Run with gunicorn settings
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))