"""
Test webhook receiver for testing webhook delivery system
"""

from flask import Flask, request, jsonify
import logging
import json
import hmac
import hashlib
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store received webhooks for verification
received_webhooks = []

@app.route('/test-webhook', methods=['POST'])
def receive_webhook():
    """
    Test endpoint to receive webhooks
    """
    try:
        # Get headers
        signature = request.headers.get('X-Signature')
        user_agent = request.headers.get('User-Agent')
        content_type = request.headers.get('Content-Type')
        
        # Get body
        body = request.get_data(as_text=True)
        
        # Log receipt
        logger.info(f"Received webhook at {datetime.utcnow().isoformat()}")
        logger.info(f"Signature: {signature}")
        logger.info(f"User-Agent: {user_agent}")
        logger.info(f"Content-Type: {content_type}")
        logger.info(f"Body length: {len(body)} bytes")
        
        # Parse JSON
        data = json.loads(body) if body else {}
        
        # Store webhook
        webhook_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'signature': signature,
            'user_agent': user_agent,
            'data': data,
            'raw_body': body[:500]  # Store first 500 chars
        }
        received_webhooks.append(webhook_record)
        
        # Log webhook content
        if 'job_id' in data:
            logger.info(f"Job ID: {data['job_id']}")
        if 'status' in data:
            logger.info(f"Status: {data['status']}")
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Webhook received successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Invalid JSON payload'
        }), 400
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/webhooks/status', methods=['GET'])
def webhook_status():
    """
    Get status of received webhooks
    """
    return jsonify({
        'total_received': len(received_webhooks),
        'webhooks': received_webhooks[-10:]  # Last 10 webhooks
    }), 200

@app.route('/webhooks/clear', methods=['POST'])
def clear_webhooks():
    """
    Clear stored webhooks
    """
    global received_webhooks
    received_webhooks = []
    return jsonify({'success': True, 'message': 'Webhooks cleared'}), 200

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'service': 'test-webhook-receiver',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

if __name__ == '__main__':
    logger.info("Starting test webhook receiver on port 5001")
    app.run(host='0.0.0.0', port=5001, debug=True)