"""
Webhook monitoring API endpoints
Provides health metrics and monitoring for webhook delivery system
"""

from flask import Blueprint, jsonify, request
from services.webhook_monitor import WebhookMonitor
from database.models import db
import logging

logger = logging.getLogger(__name__)

webhook_monitoring_bp = Blueprint('webhook_monitoring', __name__)

@webhook_monitoring_bp.route('/api/v1/webhook-metrics', methods=['GET'])
def get_webhook_metrics():
    """
    Get webhook delivery metrics
    Query parameters:
    - hours: Number of hours to look back (default: 24)
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        monitor = WebhookMonitor(db.session)
        metrics = monitor.get_delivery_metrics(hours=hours)
        
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting webhook metrics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get webhook metrics'
        }), 500

@webhook_monitoring_bp.route('/api/v1/webhook-health', methods=['GET'])
def get_webhook_health():
    """
    Get comprehensive webhook system health report
    """
    try:
        monitor = WebhookMonitor(db.session)
        report = monitor.get_summary_report()
        
        return jsonify({
            'success': True,
            'report': report
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting webhook health report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get webhook health report'
        }), 500

@webhook_monitoring_bp.route('/api/v1/webhook-failures', methods=['GET'])
def get_webhook_failures():
    """
    Get recently failed webhook deliveries
    Query parameters:
    - limit: Number of failed webhooks to return (default: 10)
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        monitor = WebhookMonitor(db.session)
        failures = monitor.get_failed_webhooks(limit=limit)
        
        return jsonify({
            'success': True,
            'failed_webhooks': failures
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting webhook failures: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get webhook failures'
        }), 500

@webhook_monitoring_bp.route('/api/v1/webhook-endpoints', methods=['GET'])
def get_webhook_endpoints():
    """
    Get health metrics per webhook endpoint
    """
    try:
        monitor = WebhookMonitor(db.session)
        endpoints = monitor.get_webhook_endpoint_health()
        
        return jsonify({
            'success': True,
            'endpoints': endpoints
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting webhook endpoint health: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get webhook endpoint health'
        }), 500

@webhook_monitoring_bp.route('/api/v1/webhook-alerts', methods=['GET'])
def get_webhook_alerts():
    """
    Get current webhook system alerts
    """
    try:
        monitor = WebhookMonitor(db.session)
        alerts = monitor.check_alerts()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'alert_count': len(alerts)
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking webhook alerts: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to check webhook alerts'
        }), 500