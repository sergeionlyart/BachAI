"""
Test webhook endpoint integrated into main application
"""

from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

test_webhook_bp = Blueprint('test_webhook', __name__)

# Store received webhooks in memory for testing
test_webhooks_storage = []

@test_webhook_bp.route('/test/webhook-receiver', methods=['POST'])
def test_webhook_receiver():
    """
    Test endpoint to receive and verify webhooks
    """
    try:
        # Get headers
        headers = {
            'X-Signature': request.headers.get('X-Signature'),
            'User-Agent': request.headers.get('User-Agent'),
            'Content-Type': request.headers.get('Content-Type')
        }
        
        # Get body
        body = request.get_data(as_text=True)
        data = json.loads(body) if body else {}
        
        # Log receipt
        logger.info(f"TEST WEBHOOK RECEIVED at {datetime.utcnow().isoformat()}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Body preview: {body[:200]}...")
        
        # Store webhook
        webhook_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'headers': headers,
            'data': data,
            'success': True
        }
        test_webhooks_storage.append(webhook_record)
        
        # Keep only last 50 webhooks
        if len(test_webhooks_storage) > 50:
            test_webhooks_storage.pop(0)
        
        return jsonify({
            'success': True,
            'message': 'Test webhook received successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in test webhook receiver: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@test_webhook_bp.route('/test/webhook-status', methods=['GET'])
def test_webhook_status():
    """
    Get status of test webhooks received
    """
    return jsonify({
        'total_received': len(test_webhooks_storage),
        'last_5_webhooks': test_webhooks_storage[-5:] if test_webhooks_storage else []
    }), 200

@test_webhook_bp.route('/test/webhook-clear', methods=['POST'])
def test_webhook_clear():
    """
    Clear test webhook storage
    """
    global test_webhooks_storage
    test_webhooks_storage = []
    return jsonify({
        'success': True,
        'message': 'Test webhook storage cleared'
    }), 200