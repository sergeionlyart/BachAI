from app import app, start_background_services

if __name__ == '__main__':
    # Start background services when running directly
    with app.app_context():
        start_background_services()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
