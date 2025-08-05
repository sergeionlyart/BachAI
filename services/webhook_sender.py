import logging
import hashlib
import hmac
import json
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
from config import SHARED_KEY

logger = logging.getLogger(__name__)

class WebhookSender:
    def __init__(self, db_session):
        self.session = db_session
        self.shared_key = SHARED_KEY
    
    def send_completion_webhook(self, job_id: str) -> bool:
        """Send webhook notification for completed job"""
        try:
            # Import here to avoid circular imports
            from database.models import BatchJob
            
            job = self.session.query(BatchJob).filter(BatchJob.id == job_id).first()
            if not job or not job.webhook_url:
                return False
            
            # Create webhook payload
            payload = {
                "job_id": job_id,
                "status": job.status,
                "timestamp": datetime.utcnow().isoformat(),
                "total_lots": job.total_lots,
                "completed_lots": job.processed_lots,
                "failed_lots": job.failed_lots,
                "result_url": f"/api/v1/batch-results/{job_id}"
            }
            
            # Generate HMAC signature
            signature = self._generate_signature(payload)
            
            # Create webhook delivery record
            delivery_id = self._create_delivery_record(job_id, job.webhook_url, payload, signature)
            
            # Attempt delivery
            return self._attempt_delivery(delivery_id)
            
        except Exception as e:
            logger.error(f"Error sending completion webhook for job {job_id}: {str(e)}")
            return False
    
    def process_pending_deliveries(self):
        """Process all pending webhook deliveries"""
        try:
            # Import here to avoid circular imports
            from database.models import WebhookDelivery
            
            pending_deliveries = self.session.query(WebhookDelivery).filter(
                WebhookDelivery.status.in_(['pending', 'failed']),
                WebhookDelivery.attempt_count < 5,
                WebhookDelivery.next_attempt_at <= datetime.utcnow()
            ).all()
            
            logger.debug(f"Processing {len(pending_deliveries)} pending webhook deliveries")
            
            for delivery in pending_deliveries:
                self._attempt_delivery(str(delivery.id))
                
        except Exception as e:
            logger.error(f"Error processing pending webhook deliveries: {str(e)}")
    
    def _create_delivery_record(self, job_id: str, webhook_url: str, payload: Dict[str, Any], signature: str) -> str:
        """Create webhook delivery record in database"""
        try:
            # Import here to avoid circular imports
            from database.models import WebhookDelivery
            import uuid
            
            delivery = WebhookDelivery(
                id=uuid.uuid4(),
                batch_job_id=job_id,
                webhook_url=webhook_url,
                payload=payload,
                signature=signature,
                next_attempt_at=datetime.utcnow()
            )
            
            self.session.add(delivery)
            self.session.commit()
            
            return str(delivery.id)
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating webhook delivery record: {str(e)}")
            raise e
    
    def _attempt_delivery(self, delivery_id: str) -> bool:
        """Attempt webhook delivery"""
        try:
            # Import here to avoid circular imports
            from database.models import WebhookDelivery
            
            delivery = self.session.query(WebhookDelivery).filter(
                WebhookDelivery.id == delivery_id
            ).first()
            
            if not delivery:
                return False
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Signature': delivery.signature,
                'User-Agent': 'Generation-Service-Webhook/1.0'
            }
            
            # Make HTTP request
            response = requests.post(
                delivery.webhook_url,
                json=delivery.payload,
                headers=headers,
                timeout=10,
                allow_redirects=False
            )
            
            # Update delivery status based on response
            if 200 <= response.status_code < 300:
                self._update_delivery_status(
                    delivery_id, 'delivered', 
                    response.status_code, response.text[:1000]
                )
                logger.info(f"Webhook delivered successfully: {delivery_id}")
                return True
            else:
                self._update_delivery_status(
                    delivery_id, 'failed',
                    response.status_code, response.text[:1000],
                    f"HTTP {response.status_code}"
                )
                logger.warning(f"Webhook delivery failed with HTTP {response.status_code}: {delivery_id}")
                return False
                
        except requests.exceptions.Timeout:
            self._update_delivery_status(delivery_id, 'failed', None, None, "Request timeout")
            logger.warning(f"Webhook delivery timeout: {delivery_id}")
            return False
            
        except requests.exceptions.ConnectionError:
            self._update_delivery_status(delivery_id, 'failed', None, None, "Connection error")
            logger.warning(f"Webhook delivery connection error: {delivery_id}")
            return False
            
        except Exception as e:
            self._update_delivery_status(delivery_id, 'failed', None, None, str(e))
            logger.error(f"Webhook delivery error: {delivery_id}: {str(e)}")
            return False
    
    def _update_delivery_status(self, delivery_id: str, status: str, 
                               response_status: int = None, response_body: str = None, 
                               error_message: str = None):
        """Update webhook delivery status"""
        try:
            # Import here to avoid circular imports
            from database.models import WebhookDelivery
            
            delivery = self.session.query(WebhookDelivery).filter(
                WebhookDelivery.id == delivery_id
            ).first()
            
            if not delivery:
                return
            
            delivery.status = status
            delivery.attempt_count += 1
            delivery.last_attempt_at = datetime.utcnow()
            
            if status == 'delivered':
                delivery.delivered_at = datetime.utcnow()
            elif status == 'failed' and delivery.attempt_count < 5:
                # Schedule next retry with exponential backoff
                delay_seconds = 2 ** delivery.attempt_count
                delivery.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
            
            if response_status is not None:
                delivery.response_status = response_status
            if response_body:
                delivery.response_body = response_body[:1000]  # Limit size
            if error_message:
                delivery.error_message = error_message[:500]  # Limit size
            
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating webhook delivery status: {str(e)}")
    
    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        """Generate HMAC signature for webhook payload"""
        try:
            payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            signature = hmac.new(
                self.shared_key.encode(),
                payload_json.encode(),
                hashlib.sha256
            ).hexdigest()
            return signature
        except Exception as e:
            logger.error(f"Error generating webhook signature: {str(e)}")
            raise e
    
    def deliver_webhook(self, webhook_delivery) -> bool:
        """
        Deliver single webhook and return success status
        """
        try:
            import json
            import requests
            
            # Prepare payload
            payload_json = json.dumps(webhook_delivery.payload, separators=(',', ':'))
            
            # Send HTTP request
            response = requests.post(
                webhook_delivery.webhook_url,
                data=payload_json,
                headers={
                    'Content-Type': 'application/json',
                    'X-Signature': webhook_delivery.signature,
                    'User-Agent': 'Generation-Service/1.0'
                },
                timeout=30
            )
            
            # Check response
            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook delivered successfully to {webhook_delivery.webhook_url}")
                return True
            else:
                logger.warning(f"Webhook delivery failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"Webhook delivery timeout to {webhook_delivery.webhook_url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Webhook delivery failed to {webhook_delivery.webhook_url}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error delivering webhook: {str(e)}")
            return False