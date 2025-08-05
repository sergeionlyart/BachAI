import logging
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from services.openai_client import OpenAIClient
from services.database_manager import DatabaseManager
from services.webhook_sender import WebhookSender
from database.models import db

logger = logging.getLogger(__name__)

class BatchMonitor:
    def __init__(self, interval: int = 30):
        self.interval = interval
        self.running = False
        self.thread = None
        
        # Initialize services
        self.openai_client = OpenAIClient()
        self.db_manager = DatabaseManager(db.session)
        self.webhook_sender = WebhookSender(db.session)
        
    def start(self):
        """Start background monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info(f"Batch monitor started with {self.interval}s interval")
    
    def stop(self):
        """Stop background monitoring"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info("Batch monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_active_batches()
                self._process_webhook_deliveries()
                self._cleanup_old_data()
                
                # Sleep for interval
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"Error in batch monitor loop: {str(e)}")
                # Continue monitoring even if there's an error
                time.sleep(self.interval)
    
    def _check_active_batches(self):
        """Check status of active batch jobs"""
        try:
            active_jobs = self.db_manager.get_active_batch_jobs()
            logger.debug(f"Checking {len(active_jobs)} active batch jobs")
            
            for job in active_jobs:
                self._check_job_status(job)
                
        except Exception as e:
            logger.error(f"Error checking active batches: {str(e)}")
    
    def _check_job_status(self, job):
        """Check status of individual batch job"""
        try:
            job_id = str(job.id)
            
            # Check vision batch status
            if job.openai_vision_batch_id and job.status == 'processing':
                self._check_vision_batch(job)
            
            # Check translation batch status
            elif job.openai_translation_batch_id and job.status == 'translating':
                self._check_translation_batch(job)
                
        except Exception as e:
            logger.error(f"Error checking job {job.id}: {str(e)}")
            # Mark job as failed
            self.db_manager.update_batch_job_status(str(job.id), 'failed', str(e))
    
    def _check_vision_batch(self, job):
        """Check OpenAI vision batch status"""
        try:
            batch_status = self.openai_client.get_batch_status(job.openai_vision_batch_id)
            
            if batch_status['status'] == 'completed':
                logger.info(f"Vision batch completed for job {job.id}")
                self._process_vision_results(job, batch_status)
                
            elif batch_status['status'] == 'failed':
                logger.error(f"Vision batch failed for job {job.id}")
                self.db_manager.update_batch_job_status(
                    str(job.id), 'failed', 'OpenAI vision batch failed'
                )
                
        except Exception as e:
            logger.error(f"Error checking vision batch for job {job.id}: {str(e)}")
    
    def _check_translation_batch(self, job):
        """Check OpenAI translation batch status"""
        try:
            batch_status = self.openai_client.get_batch_status(job.openai_translation_batch_id)
            
            if batch_status['status'] == 'completed':
                logger.info(f"Translation batch completed for job {job.id}")
                self._process_translation_results(job, batch_status)
                
                # Mark job as completed and send webhook
                self.db_manager.update_batch_job_status(str(job.id), 'completed')
                self._trigger_webhook(job)
                
            elif batch_status['status'] == 'failed':
                logger.error(f"Translation batch failed for job {job.id}")
                self.db_manager.update_batch_job_status(
                    str(job.id), 'failed', 'OpenAI translation batch failed'
                )
                
        except Exception as e:
            logger.error(f"Error checking translation batch for job {job.id}: {str(e)}")
    
    def _process_vision_results(self, job, batch_status: Dict[str, Any]):
        """Process completed vision batch results"""
        try:
            # Download results from OpenAI
            results_content = self.openai_client.download_batch_results(
                batch_status['output_file_id']
            )
            
            # Parse and save vision results
            vision_results = self.openai_client.parse_batch_results(results_content)
            
            # Update database with vision results
            self._save_vision_results(job, vision_results)
            
            # If no translations needed, complete the job
            if not job.languages or job.languages == ['en']:
                self._finalize_job_results(job)
                self.db_manager.update_batch_job_status(str(job.id), 'completed')
                self._trigger_webhook(job)
            else:
                # Start translation batch
                self._start_translation_batch(job, vision_results)
                
        except Exception as e:
            logger.error(f"Error processing vision results for job {job.id}: {str(e)}")
            self.db_manager.update_batch_job_status(str(job.id), 'failed', str(e))
    
    def _process_translation_results(self, job, batch_status: Dict[str, Any]):
        """Process completed translation batch results"""
        try:
            # Download translation results
            results_content = self.openai_client.download_batch_results(
                batch_status['output_file_id']
            )
            
            # Parse and save translation results
            translation_results = self.openai_client.parse_batch_results(results_content)
            self._save_translation_results(job, translation_results)
            
            # Finalize job with all results
            self._finalize_job_results(job)
            
        except Exception as e:
            logger.error(f"Error processing translation results for job {job.id}: {str(e)}")
            self.db_manager.update_batch_job_status(str(job.id), 'failed', str(e))
    
    def _save_vision_results(self, job, vision_results: Dict[str, Any]):
        """Save vision results to database"""
        # Implementation will be added when we have proper models working
        pass
    
    def _save_translation_results(self, job, translation_results: Dict[str, Any]):
        """Save translation results to database"""
        # Implementation will be added when we have proper models working
        pass
    
    def _finalize_job_results(self, job):
        """Create final API format results"""
        # Implementation will be added when we have proper models working
        pass
    
    def _start_translation_batch(self, job, vision_results: Dict[str, Any]):
        """Start translation batch for non-English languages"""
        try:
            # Create translation requests
            translation_requests = []
            
            for lot_result in vision_results.get('results', []):
                english_text = lot_result.get('vision_result', '')
                if not english_text:
                    continue
                
                for lang in job.languages:
                    if lang == 'en':
                        continue
                    
                    request = {
                        "custom_id": f"translate:{job.id}:{lot_result['lot_id']}:{lang}",
                        "method": "POST",
                        "url": "/v1/responses",
                        "body": {
                            "model": "gpt-4.1-mini",
                            "input": f"Translate the following text into {lang} only. Maintain the original formatting and meaning:\\n\\n{english_text}",
                            "max_output_tokens": 2048
                        }
                    }
                    translation_requests.append(request)
            
            if translation_requests:
                # Submit translation batch
                jsonl_content = self.openai_client.create_batch_file(translation_requests)
                translation_batch_id = self.openai_client.submit_batch_job(
                    jsonl_content, f"Translation for job {job.id}"
                )
                
                # Update job with translation batch ID
                self.db_manager.update_batch_job_openai_id(
                    str(job.id), translation_batch_id, 'translation'
                )
                self.db_manager.update_batch_job_status(str(job.id), 'translating')
                
                logger.info(f"Started translation batch {translation_batch_id} for job {job.id}")
            
        except Exception as e:
            logger.error(f"Error starting translation batch for job {job.id}: {str(e)}")
            self.db_manager.update_batch_job_status(str(job.id), 'failed', str(e))
    
    def _trigger_webhook(self, job):
        """Trigger webhook notification if configured"""
        if job.webhook_url:
            try:
                self.webhook_sender.send_completion_webhook(str(job.id))
                logger.info(f"Webhook triggered for job {job.id}")
            except Exception as e:
                logger.error(f"Error triggering webhook for job {job.id}: {str(e)}")
    
    def _process_webhook_deliveries(self):
        """Process pending webhook deliveries"""
        try:
            self.webhook_sender.process_pending_deliveries()
        except Exception as e:
            logger.error(f"Error processing webhook deliveries: {str(e)}")
    
    def _cleanup_old_data(self):
        """Clean up old completed jobs periodically"""
        try:
            # Run cleanup once per hour
            if hasattr(self, '_last_cleanup'):
                if datetime.utcnow() - self._last_cleanup < timedelta(hours=1):
                    return
            
            cleaned_count = self.db_manager.cleanup_old_jobs(days=7)
            self._last_cleanup = datetime.utcnow()
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old batch jobs")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

# Global monitor instance
batch_monitor = None

def get_batch_monitor(interval: int = 30) -> BatchMonitor:
    """Get or create global batch monitor instance"""
    global batch_monitor
    if batch_monitor is None:
        batch_monitor = BatchMonitor(interval)
    return batch_monitor

# Add missing method to BatchMonitor class
def add_check_job_status_method():
    """Add check_job_status method to BatchMonitor class"""
    def check_job_status(self, job_id: str):
        """Check single job status and return updated job"""
        try:
            job = self.db_manager.get_batch_job(job_id)
            if not job:
                return None
            
            self._check_job_status(job)
            return self.db_manager.get_batch_job(job_id)  # Return updated job
        
        except Exception as e:
            logger.error(f"Error checking job status {job_id}: {str(e)}")
            return None
    
    BatchMonitor.check_job_status = check_job_status

# Apply the method addition
add_check_job_status_method()