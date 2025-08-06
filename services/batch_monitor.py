import logging
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from services.openai_client import OpenAIClient
from services.database_manager import DatabaseManager
from services.webhook_sender import WebhookSender
from database.models import db, BatchLot

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
            
            # Check vision batch status (including failed jobs with completed OpenAI batches)
            if job.openai_vision_batch_id and job.status in ['processing', 'failed']:
                self._check_vision_batch(job)
            
            # Check translation batch status
            elif job.openai_translation_batch_id and job.status in ['translating', 'failed']:
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
                logger.info(f"Vision batch completed for job {job.id} (was {job.status})")
                # Reset job status to processing for successful recovery
                if job.status == 'failed':
                    self.db_manager.update_batch_job_status(str(job.id), 'processing')
                    job.status = 'processing'  # Update local object
                    logger.info(f"Recovered failed job {job.id} - OpenAI batch completed successfully")
                
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
            vision_results = self._parse_batch_results(results_content)
            
            # Update database with vision results
            self._save_vision_results(job, vision_results)
            
            # If no translations needed, complete the job
            if not job.languages or job.languages == ['en']:
                self._finalize_job_results(job)
                self.db_manager.update_batch_job_status(str(job.id), 'completed')
                self._trigger_webhook(job)
            else:
                # Mark job as processing for translation step and clear error
                self.db_manager.update_batch_job_status(str(job.id), 'processing', None)
                logger.info(f"Starting translation batch for job {job.id} with languages {job.languages}")
                
                # Start translation batch
                # Convert parsed results to expected format
                vision_results_dict = {'results': vision_results}
                self._start_translation_batch(job, vision_results_dict)
                
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
            translation_results = self._parse_batch_results(results_content)
            self._save_translation_results(job, translation_results)
            
            # Finalize job with all results
            self._finalize_job_results(job)
            
        except Exception as e:
            logger.error(f"Error processing translation results for job {job.id}: {str(e)}")
            self.db_manager.update_batch_job_status(str(job.id), 'failed', str(e))
    
    def _save_vision_results(self, job, vision_results: list):
        """Save vision results to database"""
        try:
            # Get all lots for this job
            lots = self.db_manager.session.query(BatchLot).filter(
                BatchLot.batch_job_id == job.id
            ).all()
            
            lot_map = {lot.lot_id: lot for lot in lots}
            logger.info(f"Processing {len(vision_results)} vision results for job {job.id} with {len(lots)} lots")
            
            for result in vision_results:
                if not isinstance(result, dict):
                    logger.warning(f"Skipping non-dict result: {type(result)}")
                    continue
                    
                custom_id = result.get('custom_id', '')
                logger.debug(f"Processing result with custom_id: {custom_id}")
                
                if not custom_id.startswith('vision:'):
                    logger.debug(f"Skipping non-vision result: {custom_id}")
                    continue
                
                # Parse custom_id: supports both "vision:lot_id" and "vision:job_id:lot_id"
                parts = custom_id.split(':')
                if len(parts) == 2:
                    # New format: "vision:lot_id"
                    lot_id = parts[1]
                elif len(parts) >= 3:
                    # Old format: "vision:job_id:lot_id"
                    lot_id = parts[2]
                else:
                    logger.warning(f"Invalid custom_id format: {custom_id}")
                    continue
                response_data = result.get('response', {})
                logger.info(f"Processing lot {lot_id}")
                logger.info(f"Response keys: {list(response_data.keys()) if response_data else 'None'}")
                
                # Extract vision text from response
                vision_text = ''
                if isinstance(response_data, dict):
                    body = response_data.get('body', {})
                    logger.info(f"Body keys: {list(body.keys()) if body else 'None'}")
                    
                    if isinstance(body, dict):
                        # For OpenAI Responses API - the actual text is in output field
                        # Structure: body.output[0].content[0].text
                        output = body.get('output', [])
                        
                        if output and isinstance(output, list) and len(output) > 0:
                            first_output = output[0]
                            if isinstance(first_output, dict):
                                content = first_output.get('content', [])
                                if content and isinstance(content, list) and len(content) > 0:
                                    first_content = content[0]
                                    if isinstance(first_content, dict):
                                        vision_text = first_content.get('text', '')
                                        if vision_text:
                                            logger.info(f"Extracted text from output field for lot {lot_id}: {len(vision_text)} chars")
                                        else:
                                            logger.warning(f"No text in content for lot {lot_id}")
                                    else:
                                        logger.warning(f"First content is not dict for lot {lot_id}: {type(first_content)}")
                                else:
                                    logger.warning(f"No content in output for lot {lot_id}")
                            else:
                                logger.warning(f"First output is not dict for lot {lot_id}: {type(first_output)}")
                        else:
                            # Legacy fallback to choices format (for older chat completions)
                            choices = body.get('choices', [])
                            logger.info(f"Trying choices fallback, choices count: {len(choices) if choices else 0}")
                            if choices and len(choices) > 0:
                                message = choices[0].get('message', {})
                                content = message.get('content', '')
                                if content:
                                    vision_text = content
                                    logger.info(f"Found content in choices for lot {lot_id}: {len(content)} chars")
                                else:
                                    logger.warning(f"No content in message for lot {lot_id}")
                            else:
                                # Final fallback - check if text field has actual content (not just format)
                                text = body.get('text', '')
                                if isinstance(text, str) and text and not text.startswith('{'):
                                    vision_text = text
                                    logger.info(f"Found text string in text field for lot {lot_id}: {len(text)} chars")
                                else:
                                    logger.warning(f"No valid output or choices for lot {lot_id}")
                    else:
                        logger.warning(f"Body is not dict for lot {lot_id}: {type(body)}")
                else:
                    logger.warning(f"Response_data is not dict for lot {lot_id}: {type(response_data)}")
                
                # Log final vision_text status
                if vision_text:
                    logger.info(f"SUCCESS: Got vision text for lot {lot_id}: {len(vision_text)} characters")
                else:
                    logger.error(f"FAILED: No vision text extracted for lot {lot_id}")
                
                # Update lot with vision result
                if lot_id in lot_map:
                    lot = lot_map[lot_id]
                    if vision_text and isinstance(vision_text, str):
                        setattr(lot, 'vision_result', vision_text)
                        setattr(lot, 'status', 'processing')  # Will be completed after translations
                        setattr(lot, 'updated_at', datetime.utcnow())
                        logger.info(f"Vision result saved for lot {lot_id}: {len(vision_text)} characters")
                    else:
                        setattr(lot, 'status', 'failed')
                        setattr(lot, 'error_message', f'No valid vision result: {type(vision_text)} - {str(vision_text)[:100]}')
                        setattr(lot, 'updated_at', datetime.utcnow())
                        logger.error(f"No vision result for lot {lot_id}: {type(vision_text)} - {str(vision_text)[:100]}")
                else:
                    logger.warning(f"Lot {lot_id} not found in job {job.id}")
            
            # Update job progress
            successful_lots = len([lot for lot in lots if getattr(lot, 'vision_result', None)])
            setattr(job, 'processed_lots', successful_lots)
            setattr(job, 'updated_at', datetime.utcnow())
            
            # Commit changes
            self.db_manager.session.commit()
            logger.info(f"Saved vision results for job {job.id}: {successful_lots}/{len(lots)} lots processed")
            
            # If we have results but no successful lots, there's a parsing issue
            if len(vision_results) > 0 and successful_lots == 0:
                logger.error(f"All vision results failed to parse for job {job.id}! Check custom_id format.")
                    
        except Exception as e:
            self.db_manager.session.rollback()
            logger.error(f"Error saving vision results: {str(e)}")
            raise
    
    def _save_translation_results(self, job, translation_results: list):
        """Save translation results to database"""
        try:
            # Get all lots for this job
            lots = self.db_manager.session.query(BatchLot).filter(
                BatchLot.batch_job_id == job.id
            ).all()
            
            lot_map = {lot.lot_id: lot for lot in lots}
            
            for result in translation_results:
                if not isinstance(result, dict):
                    continue
                    
                custom_id = result.get('custom_id', '')
                if not custom_id.startswith('translate:'):
                    continue
                
                # Parse custom_id: "translate:job_id:lot_id:language"
                parts = custom_id.split(':')
                if len(parts) < 4:
                    continue
                
                lot_id = parts[2]
                language = parts[3]
                response_data = result.get('response', {})
                
                # Extract translated text from response
                translated_text = ''
                if isinstance(response_data, dict):
                    body = response_data.get('body', {})
                    if isinstance(body, dict):
                        choices = body.get('choices', [{}])
                        if choices and len(choices) > 0:
                            translated_text = choices[0].get('message', {}).get('content', '')
                
                # Update lot with translation
                if lot_id in lot_map and translated_text:
                    lot = lot_map[lot_id]
                    current_translations = getattr(lot, 'translations', None) or {}
                    current_translations[language] = translated_text
                    setattr(lot, 'translations', current_translations)
                    setattr(lot, 'updated_at', datetime.utcnow())
                    logger.info(f"Translation saved for lot {lot_id} in {language}: {len(translated_text)} characters")
            
            # Mark all lots as completed
            for lot in lots:
                if getattr(lot, 'vision_result', None):  # Only mark as completed if has vision result
                    setattr(lot, 'status', 'completed')
            
            # Update job to reflect completion
            completed_lots = len([lot for lot in lots if getattr(lot, 'status', None) == 'completed'])
            failed_lots = len([lot for lot in lots if getattr(lot, 'status', None) == 'failed'])
            setattr(job, 'processed_lots', completed_lots)
            setattr(job, 'failed_lots', failed_lots)
            setattr(job, 'updated_at', datetime.utcnow())
            
            # Commit changes
            self.db_manager.session.commit()
            logger.info(f"Saved translation results for job {job.id}")
                    
        except Exception as e:
            self.db_manager.session.rollback()
            logger.error(f"Error saving translation results: {str(e)}")
            raise
    
    def _finalize_job_results(self, job):
        """Create final API format results"""
        try:
            # Get all lots for this job
            lots = self.db_manager.session.query(BatchLot).filter(
                BatchLot.batch_job_id == job.id
            ).all()
            
            # Build results structure
            results_data = {
                'job_id': str(job.id),
                'status': 'completed',
                'lots': []
            }
            
            for lot in lots:
                lot_result = {
                    'lot_id': getattr(lot, 'lot_id'),
                    'status': getattr(lot, 'status'),
                    'vision_result': getattr(lot, 'vision_result'),
                    'translations': getattr(lot, 'translations') or {},
                    'error_message': getattr(lot, 'error_message'),
                    'missing_images': lot.missing_images
                }
                results_data['lots'].append(lot_result)
            
            # Save results using database manager
            self.db_manager.save_batch_results(str(job.id), results_data)
            logger.info(f"Finalized results for job {job.id} with {len(lots)} lots")
            
        except Exception as e:
            logger.error(f"Error finalizing job results: {str(e)}")
            raise
    
    def _parse_batch_results(self, results_content: str) -> list:
        """Parse batch results from JSONL content"""
        results = []
        try:
            import json
            for line in results_content.strip().split('\n'):
                if line.strip():
                    result = json.loads(line)
                    results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error parsing batch results: {str(e)}")
            return []
    
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
    
    def _start_translation_batch(self, job, vision_results: Dict[str, Any]):
        """Start translation batch for non-English languages"""
        try:
            # Get lots with vision results from database
            lots = self.db_manager.session.query(BatchLot).filter(
                BatchLot.batch_job_id == job.id,
                BatchLot.vision_result.isnot(None)
            ).all()
            
            logger.info(f"Creating translation requests for {len(lots)} lots with vision results")
            
            # Create translation requests
            translation_requests = []
            
            for lot in lots:
                english_text = getattr(lot, 'vision_result', None)
                if not english_text or not isinstance(english_text, str):
                    logger.warning(f"Skipping lot {getattr(lot, 'lot_id')}: no valid vision result")
                    continue
                
                for lang in job.languages:
                    if lang == 'en':
                        continue
                    
                    request = {
                        "custom_id": f"translate:{job.id}:{lot.lot_id}:{lang}",
                        "method": "POST",
                        "url": "/v1/responses",
                        "body": {
                            "model": "gpt-4.1-mini",
                            "input": f"Translate the following text into {lang} only. Maintain the original formatting and meaning:\\n\\n{english_text}",
                            "max_output_tokens": 2048
                        }
                    }
                    translation_requests.append(request)
                    
            logger.info(f"Created {len(translation_requests)} translation requests for job {job.id}")
            
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

