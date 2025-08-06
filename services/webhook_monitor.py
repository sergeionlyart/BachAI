"""
Webhook monitoring and metrics service
Provides real-time monitoring and metrics for webhook delivery system
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func, and_, or_
from database.models import WebhookDelivery, BatchJob

logger = logging.getLogger(__name__)

class WebhookMonitor:
    """
    Monitor webhook delivery system health and performance
    """
    
    def __init__(self, db_session):
        self.session = db_session
    
    def get_delivery_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get webhook delivery metrics for the specified time period
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Total deliveries
            total = self.session.query(func.count(WebhookDelivery.id)).filter(
                WebhookDelivery.created_at >= since
            ).scalar() or 0
            
            # Successful deliveries
            delivered = self.session.query(func.count(WebhookDelivery.id)).filter(
                and_(
                    WebhookDelivery.created_at >= since,
                    WebhookDelivery.status == 'delivered'
                )
            ).scalar() or 0
            
            # Failed deliveries
            failed = self.session.query(func.count(WebhookDelivery.id)).filter(
                and_(
                    WebhookDelivery.created_at >= since,
                    WebhookDelivery.status == 'failed',
                    WebhookDelivery.attempt_count >= 5
                )
            ).scalar() or 0
            
            # Pending deliveries
            pending = self.session.query(func.count(WebhookDelivery.id)).filter(
                and_(
                    WebhookDelivery.status.in_(['pending', 'failed']),
                    WebhookDelivery.attempt_count < 5
                )
            ).scalar() or 0
            
            # Average retry count for successful deliveries
            avg_retries = self.session.query(func.avg(WebhookDelivery.attempt_count)).filter(
                and_(
                    WebhookDelivery.created_at >= since,
                    WebhookDelivery.status == 'delivered'
                )
            ).scalar() or 0
            
            # Average delivery time (for successful deliveries)
            successful_deliveries = self.session.query(WebhookDelivery).filter(
                and_(
                    WebhookDelivery.created_at >= since,
                    WebhookDelivery.status == 'delivered',
                    WebhookDelivery.delivered_at.isnot(None)
                )
            ).all()
            
            if successful_deliveries:
                delivery_times = [
                    (d.delivered_at - d.created_at).total_seconds()
                    for d in successful_deliveries
                    if d.delivered_at
                ]
                avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
            else:
                avg_delivery_time = 0
            
            # Calculate success rate
            success_rate = (delivered / total * 100) if total > 0 else 0
            
            return {
                'period_hours': hours,
                'total_webhooks': total,
                'delivered': delivered,
                'failed': failed,
                'pending': pending,
                'success_rate': round(success_rate, 2),
                'average_retries': round(float(avg_retries), 2),
                'average_delivery_time_seconds': round(avg_delivery_time, 2),
                'metrics_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating webhook metrics: {str(e)}")
            return {
                'error': str(e),
                'metrics_timestamp': datetime.utcnow().isoformat()
            }
    
    def get_failed_webhooks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recently failed webhook deliveries
        """
        try:
            failed_webhooks = self.session.query(WebhookDelivery).filter(
                and_(
                    WebhookDelivery.status == 'failed',
                    WebhookDelivery.attempt_count >= 5
                )
            ).order_by(WebhookDelivery.last_attempt_at.desc()).limit(limit).all()
            
            return [
                {
                    'id': str(webhook.id),
                    'webhook_url': webhook.webhook_url,
                    'attempt_count': webhook.attempt_count,
                    'error_message': webhook.error_message,
                    'last_attempt': webhook.last_attempt_at.isoformat() if webhook.last_attempt_at else None,
                    'created_at': webhook.created_at.isoformat()
                }
                for webhook in failed_webhooks
            ]
            
        except Exception as e:
            logger.error(f"Error getting failed webhooks: {str(e)}")
            return []
    
    def get_webhook_endpoint_health(self) -> List[Dict[str, Any]]:
        """
        Get health metrics per webhook endpoint
        """
        try:
            # Group by webhook URL to get endpoint-specific metrics
            from sqlalchemy import Integer
            endpoint_stats = self.session.query(
                WebhookDelivery.webhook_url,
                func.count(WebhookDelivery.id).label('total'),
                func.sum(func.cast(WebhookDelivery.status == 'delivered', Integer)).label('delivered'),
                func.sum(func.cast(and_(
                    WebhookDelivery.status == 'failed',
                    WebhookDelivery.attempt_count >= 5
                ), Integer)).label('failed')
            ).group_by(WebhookDelivery.webhook_url).all()
            
            results = []
            for url, total, delivered, failed in endpoint_stats:
                delivered = delivered or 0
                failed = failed or 0
                success_rate = (delivered / total * 100) if total > 0 else 0
                
                results.append({
                    'webhook_url': url,
                    'total_attempts': total,
                    'successful': delivered,
                    'failed': failed,
                    'success_rate': round(success_rate, 2)
                })
            
            # Sort by success rate (ascending to show problematic endpoints first)
            results.sort(key=lambda x: x['success_rate'])
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting webhook endpoint health: {str(e)}")
            return []
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for conditions that should trigger alerts
        """
        alerts = []
        
        try:
            # Check success rate in last hour
            metrics_1h = self.get_delivery_metrics(hours=1)
            if metrics_1h.get('total_webhooks', 0) > 10:  # Only alert if sufficient volume
                if metrics_1h.get('success_rate', 100) < 90:
                    alerts.append({
                        'level': 'warning',
                        'message': f"Webhook success rate is {metrics_1h['success_rate']}% in the last hour",
                        'metric': 'success_rate',
                        'value': metrics_1h['success_rate']
                    })
            
            # Check for stuck pending webhooks
            old_pending = self.session.query(func.count(WebhookDelivery.id)).filter(
                and_(
                    WebhookDelivery.status == 'pending',
                    WebhookDelivery.created_at < datetime.utcnow() - timedelta(hours=1)
                )
            ).scalar() or 0
            
            if old_pending > 10:
                alerts.append({
                    'level': 'error',
                    'message': f"{old_pending} webhooks have been pending for over 1 hour",
                    'metric': 'stuck_webhooks',
                    'value': old_pending
                })
            
            # Check for high retry rate
            if metrics_1h.get('average_retries', 0) > 2:
                alerts.append({
                    'level': 'warning',
                    'message': f"Average retry count is {metrics_1h['average_retries']} in the last hour",
                    'metric': 'retry_rate',
                    'value': metrics_1h['average_retries']
                })
            
            # Check for endpoints with consistent failures
            endpoint_health = self.get_webhook_endpoint_health()
            for endpoint in endpoint_health[:3]:  # Check top 3 worst performing
                if endpoint['total_attempts'] > 5 and endpoint['success_rate'] < 50:
                    alerts.append({
                        'level': 'error',
                        'message': f"Webhook endpoint {endpoint['webhook_url']} has {endpoint['success_rate']}% success rate",
                        'metric': 'endpoint_failure',
                        'value': endpoint['success_rate'],
                        'endpoint': endpoint['webhook_url']
                    })
            
        except Exception as e:
            logger.error(f"Error checking alerts: {str(e)}")
            alerts.append({
                'level': 'error',
                'message': f"Error checking webhook alerts: {str(e)}",
                'metric': 'system_error'
            })
        
        return alerts
    
    def get_summary_report(self) -> Dict[str, Any]:
        """
        Get comprehensive webhook system summary report
        """
        try:
            report = {
                'metrics_24h': self.get_delivery_metrics(hours=24),
                'metrics_1h': self.get_delivery_metrics(hours=1),
                'failed_webhooks': self.get_failed_webhooks(limit=5),
                'endpoint_health': self.get_webhook_endpoint_health()[:10],
                'alerts': self.check_alerts(),
                'report_timestamp': datetime.utcnow().isoformat()
            }
            
            # Add overall health score (0-100)
            health_score = 100
            
            # Deduct points for poor success rate
            success_rate_24h = report['metrics_24h'].get('success_rate', 100)
            if success_rate_24h < 95:
                health_score -= min(20, (95 - success_rate_24h) * 2)
            
            # Deduct points for high retry rate
            avg_retries = report['metrics_24h'].get('average_retries', 0)
            if avg_retries > 1.5:
                health_score -= min(15, (avg_retries - 1.5) * 10)
            
            # Deduct points for alerts
            critical_alerts = len([a for a in report['alerts'] if a['level'] == 'error'])
            warning_alerts = len([a for a in report['alerts'] if a['level'] == 'warning'])
            health_score -= (critical_alerts * 10 + warning_alerts * 5)
            
            report['health_score'] = max(0, min(100, health_score))
            report['health_status'] = self._get_health_status(health_score)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating summary report: {str(e)}")
            return {
                'error': str(e),
                'report_timestamp': datetime.utcnow().isoformat()
            }
    
    def _get_health_status(self, score: float) -> str:
        """
        Convert health score to status string
        """
        if score >= 90:
            return 'healthy'
        elif score >= 70:
            return 'degraded'
        elif score >= 50:
            return 'unhealthy'
        else:
            return 'critical'