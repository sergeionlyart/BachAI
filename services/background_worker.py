import logging
import time
import threading
from typing import Dict, Any
from datetime import datetime, timedelta
from flask import current_app
from services.database_manager import DatabaseManager
from services.batch_monitor import BatchMonitor
from services.webhook_sender import WebhookSender
from database.models import db, BatchJob


logger = logging.getLogger(__name__)

class BackgroundWorker:
    """
    Background worker service for monitoring batch jobs and sending webhooks
    """
    
    def __init__(self, flask_app=None):
        self.flask_app = flask_app
        self.running = False
        self.worker_thread = None
        
        # Configuration
        self.check_interval = 30  # Check every 30 seconds
        self.max_webhook_retries = 5
        
    def start(self):
        """
        Start background worker in separate thread
        """
        if self.running:
            logger.warning("Background worker already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Background worker started")
    
    def stop(self):
        """
        Stop background worker
        """
        if not self.running:
            return
        
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        logger.info("Background worker stopped")
    
    def _worker_loop(self):
        """
        Main worker loop - monitors jobs and sends webhooks
        """
        logger.info("Background worker loop started")
        
        while self.running:
            try:
                # Use Flask application context for database operations
                if self.flask_app:
                    with self.flask_app.app_context():
                        # Initialize services within app context
                        db_manager = DatabaseManager(db.session)
                        batch_monitor = BatchMonitor()
                        webhook_sender = WebhookSender(db.session)
                        
                        # Monitor active batch jobs
                        self._monitor_batch_jobs(db_manager, batch_monitor)
                        
                        # Process pending webhooks
                        self._process_pending_webhooks(db_manager, webhook_sender)
                else:
                    logger.error("Flask app not initialized, skipping background worker iteration")
                
                # Sleep before next iteration
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Background worker error: {str(e)}")
                time.sleep(5)  # Short sleep on error before retrying
    
    def _monitor_batch_jobs(self, db_manager, batch_monitor):
        """
        Monitor active batch jobs and update their status
        """
        try:
            # Get active jobs from database
            active_jobs = db_manager.get_active_batch_jobs()
            
            for job in active_jobs:
                try:
                    # Check job status with OpenAI
                    updated_job = batch_monitor.check_job_status(str(job.id))
                    
                    if updated_job and updated_job.status == 'completed':
                        # Job completed - create webhook delivery
                        self._create_webhook_delivery(updated_job, db_manager)
                        
                except Exception as e:
                    logger.error(f"Error monitoring job {job.id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error getting active batch jobs: {str(e)}")
    
    def _process_pending_webhooks(self, db_manager, webhook_sender):
        """
        Process pending webhook deliveries
        """
        try:
            # Get pending webhook deliveries
            pending_webhooks = db_manager.get_pending_webhook_deliveries()
            
            for webhook in pending_webhooks:
                try:
                    # Check if it's time to retry
                    if webhook.next_attempt_at is not None and datetime.utcnow() < webhook.next_attempt_at:
                        continue
                    
                    # Check retry limit
                    if webhook.attempt_count >= self.max_webhook_retries:
                        db_manager.mark_webhook_failed(str(webhook.id), "Max retries exceeded")
                        continue
                    
                    # Attempt delivery
                    success = webhook_sender.deliver_webhook(webhook)
                    
                    if success:
                        db_manager.mark_webhook_delivered(str(webhook.id))
                        logger.info(f"Webhook delivered successfully to {webhook.webhook_url}")
                    else:
                        # Schedule retry
                        retry_delay = min(300, 30 * (2 ** min(int(webhook.attempt_count), 10)))  # Exponential backoff, max 5 minutes
                        next_attempt = datetime.utcnow() + timedelta(seconds=retry_delay)
                        
                        db_manager.update_webhook_attempt(
                            str(webhook.id), 
                            int(webhook.attempt_count) + 1,
                            next_attempt,
                            "Delivery failed, will retry"
                        )
                        
                except Exception as e:
                    logger.error(f"Error processing webhook {webhook.id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error processing pending webhooks: {str(e)}")
    
    def _create_webhook_delivery(self, job: BatchJob, db_manager):
        """
        Create webhook delivery entries for completed job  
        """
        try:
            # Get job results
            results = db_manager.get_batch_results(str(job.id))
            if not results:
                logger.warning(f"No results found for completed job {job.id}")
                return
            
            # Group lots by webhook URL
            webhook_groups = {}
            
            for lot in job.lots:
                if lot.webhook_url:
                    if lot.webhook_url not in webhook_groups:
                        webhook_groups[lot.webhook_url] = []
                    
                    # Prepare lot result
                    lot_result = {
                        'lot_id': lot.lot_id,
                        'status': lot.status,
                        'descriptions': []
                    }
                    
                    # Add English description
                    if lot.vision_result:
                        lot_result['descriptions'].append({
                            'language': 'en',
                            'damages': f"<p>{lot.vision_result}</p>"
                        })
                    
                    # Add translations
                    if lot.translations:
                        for lang, translation in lot.translations.items():
                            lot_result['descriptions'].append({
                                'language': lang,
                                'damages': f"<p>{translation}</p>"
                            })
                    
                    webhook_groups[lot.webhook_url].append(lot_result)
            
            # Create webhook deliveries
            for webhook_url, lots in webhook_groups.items():
                payload = {
                    'job_id': str(job.id),
                    'status': 'completed',
                    'completed_at': job.updated_at.isoformat(),
                    'lots': lots
                }
                
                # Create webhook delivery record
                db_manager.create_webhook_delivery(
                    job_id=str(job.id),
                    webhook_url=webhook_url,
                    payload=payload
                )
                
            logger.info(f"Created webhook deliveries for job {job.id}")
            
        except Exception as e:
            logger.error(f"Error creating webhook deliveries for job {job.id}: {str(e)}")

# Global worker instance
_background_worker = None

def start_background_worker():
    """
    Start the global background worker
    """
    global _background_worker
    if _background_worker is None:
        _background_worker = BackgroundWorker()
        _background_worker.start()

def stop_background_worker():
    """
    Stop the global background worker
    """
    global _background_worker
    if _background_worker:
        _background_worker.stop()
        _background_worker = None

def get_background_worker():
    """
    Get the global background worker instance
    """
    return _background_worker