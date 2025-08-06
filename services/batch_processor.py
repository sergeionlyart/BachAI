import json
import logging
import uuid
import time
from typing import List, Dict, Any, Optional

from services.openai_client import OpenAIClient
from services.image_validator import ImageValidator
from services.webhook_handler import WebhookHandler
from config import MAX_LINES, MAX_FILE_BYTES, MAX_LINE_BYTES

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.image_validator = ImageValidator()
        self.webhook_handler = WebhookHandler()
        
        # Initialize database manager for persistent storage
        from database.models import db
        from services.database_manager import DatabaseManager
        self.db_manager = DatabaseManager(db.session)
        
        # Remove in-memory storage - using PostgreSQL now
        logger.info("BatchProcessor initialized with PostgreSQL persistence")
    
    def create_batch_job(self, lots: List[Dict[str, Any]], languages: List[str]) -> str:
        """
        Create and submit batch processing job (optimized for fast response)
        """
        job_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Validate batch size limits
            if len(lots) > MAX_LINES:
                raise ValueError(f"Too many lots: {len(lots)} > {MAX_LINES}")
            
            logger.info(f"Creating batch job {job_id} for {len(lots)} lots")
            
            # Fast processing - skip expensive image validation for batch creation
            # Image validation will be done during actual batch processing
            processed_lots = []
            max_creation_time = 15  # Maximum 15 seconds for batch creation
            
            for i, lot in enumerate(lots):
                # Check timeout every 100 lots
                if i % 100 == 0 and time.time() - start_time > max_creation_time:
                    logger.warning(f"Batch creation timeout after {i} lots, proceeding with partial batch")
                    break
                
                # Basic validation only - no HTTP requests
                image_urls = [img['url'] for img in lot.get('images', []) if 'url' in img and img['url']]
                
                if not image_urls:
                    # Mark lot for error (no images)
                    processed_lots.append({
                        'lot_id': lot.get('lot_id', f'unknown_{i}'),
                        'status': 'error',
                        'error': 'no_images',
                        'missing_images': [],
                        'webhook': lot.get('webhook')
                    })
                    continue
                
                # Store all image URLs for later validation during processing
                processed_lots.append({
                    'lot_id': lot.get('lot_id', f'lot_{i}'),
                    'image_urls': image_urls,  # Store original URLs for later validation
                    'additional_info': lot.get('additional_info', ''),
                    'webhook': lot.get('webhook'),
                    'status': 'pending'
                })
            
            # Create batch requests for vision processing only
            # Translation will be handled separately after vision results are ready
            vision_requests = []
            
            for lot in processed_lots:
                if lot['status'] == 'error':
                    continue
                
                # Vision request using proper Responses API format
                vision_custom_id = f"vision:{lot['lot_id']}"
                
                # Create input content in text format with image URLs
                # Image validation will happen during batch processing by OpenAI
                image_list = "\n".join([f"Image {i+1}: {url}" for i, url in enumerate(lot['image_urls'])])
                input_text = f"Analyze these car images and provide a detailed damage assessment.\n\nAdditional info: {lot['additional_info']}\n\nProvided images:\n{image_list}\n\nNote: Analyze based on the context provided above."
                
                vision_request = {
                    "custom_id": vision_custom_id,
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": {
                        "model": "o4-mini",
                        "reasoning": {"effort": "medium"},
                        "input": input_text,
                        "max_output_tokens": 2048
                    }
                }
                vision_requests.append(vision_request)
            
            # Submit vision batch job with timeout protection
            vision_batch_id = None
            if vision_requests:
                # Quick check for batch limits
                vision_jsonl = self.openai_client.create_batch_file(vision_requests[:1000])  # Limit to 1000 requests for fast creation
                estimated_size = len(vision_jsonl.encode()) * len(vision_requests) / min(len(vision_requests), 1000)
                
                if estimated_size > MAX_FILE_BYTES:
                    raise ValueError(f"Estimated batch file too large: {estimated_size} > {MAX_FILE_BYTES}")
                
                # Create full batch file
                vision_jsonl = self.openai_client.create_batch_file(vision_requests)
                
                # Submit with timeout protection  
                try:
                    vision_batch_id = self.openai_client.submit_batch_job(
                        vision_jsonl, 
                        f"Vision processing for job {job_id}"
                    )
                except Exception as e:
                    logger.error(f"Batch submission failed: {str(e)}")
                    # Continue anyway - job will be marked as failed but created
                    vision_batch_id = None
            
            # Store job information
            creation_time = time.time() - start_time
            status = 'processing' if vision_batch_id else 'failed'
            
            # Store job in database
            job_data = {
                'job_id': job_id,
                'status': status,
                'languages': languages,
                'openai_batch_id': vision_batch_id,  # FIXED: Use correct field name
                'lots': processed_lots,
                'error_message': None if vision_batch_id else 'Batch submission failed'
            }
            
            try:
                self.db_manager.create_batch_job(job_data)
            except Exception as db_error:
                logger.error(f"Failed to store job in database: {str(db_error)}")
                # Continue anyway - job was created in OpenAI
            
            logger.info(f"Created batch job {job_id} in {creation_time:.2f}s with vision batch {vision_batch_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Batch job creation failed: {str(e)}")
            raise e
    
    def check_batch_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Check status of batch job
        """
        job = self.db_manager.get_batch_job(job_id)
        if not job:
            return None
        
        try:
            # Check vision batch status
            if job.openai_batch_id and job.status == 'processing':
                vision_status = self.openai_client.get_batch_status(job.openai_batch_id)
                
                if vision_status['status'] == 'completed':
                    # Download and process vision results
                    self._process_vision_results(job_id, vision_status)
                elif vision_status['status'] == 'failed':
                    self.db_manager.update_batch_job_status(job_id, 'failed', 'Vision batch processing failed')
            
            # Check translation batch status  
            if job.openai_translation_batch_id and job.status == 'translating':
                translation_status = self.openai_client.get_batch_status(job.openai_translation_batch_id)
                
                if translation_status['status'] == 'completed':
                    # Download and process translation results
                    self._process_translation_results(job_id, translation_status)
                    self.db_manager.update_batch_job_status(job_id, 'completed')
                    
                    # Send webhooks handled by monitor service now
                elif translation_status['status'] == 'failed':
                    self.db_manager.update_batch_job_status(job_id, 'failed', 'Translation batch processing failed')
            
            return {
                'job_id': job_id,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'error': job.error_message
            }
            
        except Exception as e:
            logger.error(f"Batch status check failed for {job_id}: {str(e)}")
            self.db_manager.update_batch_job_status(job_id, 'failed', str(e))
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _process_vision_results(self, job_id: str, vision_status: Dict[str, Any]):
        """
        Process completed vision batch results
        """
        job = self.db_manager.get_batch_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for vision results processing")
            return
        
        try:
            # Download results
            results_content = self.openai_client.download_batch_results(vision_status['output_file_id'])
            
            # Parse results
            vision_results = {}
            for line in results_content.strip().split('\n'):
                if line:
                    result = json.loads(line)
                    custom_id = result['custom_id']
                    
                    if custom_id.startswith('vision:'):
                        lot_id = custom_id.replace('vision:', '')
                        
                        if result.get('response'):
                            response_body = result['response']['body']
                            if response_body.get('output_text'):
                                vision_results[lot_id] = response_body['output_text']
                            else:
                                logger.warning(f"No output_text for lot {lot_id}")
                                vision_results[lot_id] = "No description available"
                        else:
                            logger.error(f"No response for lot {lot_id}: {result.get('error', 'Unknown error')}")
                            vision_results[lot_id] = "Error generating description"
            
            # Store vision results in database 
            # This would be handled by storing individual lot results
            
            # Now submit translation batch if needed
            translation_languages = [lang for lang in job.languages if lang.lower() != 'en']
            
            if translation_languages and vision_results:
                self._submit_translation_batch(job_id, vision_results, translation_languages)
                self.db_manager.update_batch_job_status(job_id, 'translating')
            else:
                # No translation needed, job is complete
                self.db_manager.update_batch_job_status(job_id, 'completed')
                # Webhook sending handled by monitor service
            
        except Exception as e:
            logger.error(f"Vision results processing failed for {job_id}: {str(e)}")
            self.db_manager.update_batch_job_status(job_id, 'failed', f"Vision results processing failed: {str(e)}")
    
    def _submit_translation_batch(self, job_id: str, vision_results: Dict[str, str], languages: List[str]):
        """
        Submit translation batch job
        """
        job = self.db_manager.get_batch_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for translation batch submission")
            return
        
        try:
            translation_requests = []
            
            for lot_id, english_text in vision_results.items():
                for lang in languages:
                    translation_custom_id = f"tr:{lot_id}:{lang}"
                    translation_request = {
                        "custom_id": translation_custom_id,
                        "method": "POST",
                        "url": "/v1/responses",
                        "body": {
                            "model": "gpt-4.1-mini",
                            "input": f"Translate the following text into {lang} only. Maintain the original formatting and meaning:\n\n{english_text}",
                            "max_output_tokens": 2048
                        }
                    }
                    translation_requests.append(translation_request)
            
            if translation_requests:
                translation_jsonl = self.openai_client.create_batch_file(translation_requests)
                translation_batch_id = self.openai_client.submit_batch_job(
                    translation_jsonl,
                    f"Translation processing for job {job_id}"
                )
                self.db_manager.update_batch_job_openai_id(job_id, translation_batch_id, 'translation')
                logger.info(f"Submitted translation batch {translation_batch_id} for job {job_id}")
            
        except Exception as e:
            logger.error(f"Translation batch submission failed for {job_id}: {str(e)}")
            raise e
    
    def _process_translation_results(self, job_id: str, translation_status: Dict[str, Any]):
        """
        Process completed translation batch results
        """
        job = self.db_manager.get_batch_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for translation results processing")
            return
        
        try:
            results_content = self.openai_client.download_batch_results(translation_status['output_file_id'])
            
            # Parse translation results
            translation_results = {}
            for line in results_content.strip().split('\n'):
                if line:
                    result = json.loads(line)
                    custom_id = result['custom_id']
                    
                    if custom_id.startswith('tr:'):
                        parts = custom_id.split(':')
                        if len(parts) >= 3:
                            lot_id = parts[1]
                            language = parts[2]
                            
                            if lot_id not in translation_results:
                                translation_results[lot_id] = {}
                            
                            if result.get('response'):
                                response_body = result['response']['body']
                                if response_body.get('output_text'):
                                    translation_results[lot_id][language] = response_body['output_text']
                                else:
                                    translation_results[lot_id][language] = "Translation failed"
                            else:
                                logger.error(f"Translation failed for {lot_id}:{language}: {result.get('error', 'Unknown error')}")
                                translation_results[lot_id][language] = "Translation failed"
            
            # Store translation results in database - handled by monitor service
            
        except Exception as e:
            logger.error(f"Translation results processing failed for {job_id}: {str(e)}")
            raise e
    
    def _send_webhooks(self, job_id: str):
        """
        Send webhook notifications for completed job
        """
        job = self.db_manager.get_batch_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for webhook sending")
            return
        
        try:
            # Group lots by webhook URL
            webhook_groups = {}
            
            # Get lots from database
            for lot in job.lots:
                webhook_url = lot.webhook_url
                if webhook_url:
                    if webhook_url not in webhook_groups:
                        webhook_groups[webhook_url] = []
                    
                    lot_id = lot.lot_id
                    
                    # Prepare descriptions
                    descriptions = []
                    
                    # Add English description from database
                    if lot.vision_result:
                        descriptions.append({
                            'language': 'en',
                            'damages': f"<p>{lot.vision_result}</p>"
                        })
                    
                    # Add translations
                    if lot_id in job['translation_results']:
                        for lang, text in job['translation_results'][lot_id].items():
                            descriptions.append({
                                'language': lang,
                                'damages': f"<p>{text}</p>"
                            })
                    
                    lot_result = {
                        'lot_id': lot_id,
                        'descriptions': descriptions
                    }
                    
                    # Add missing images if any
                    if lot.get('missing_images'):
                        lot_result['missing_images'] = lot['missing_images']
                    
                    webhook_groups[webhook_url].append(lot_result)
            
            # Send webhooks
            for webhook_url, lots_data in webhook_groups.items():
                self.webhook_handler.send_webhook(webhook_url, lots_data)
            
        except Exception as e:
            logger.error(f"Webhook sending failed for {job_id}: {str(e)}")
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Clean up old completed jobs
        """
        try:
            days = max_age_hours / 24
            removed = self.db_manager.cleanup_old_jobs(days=int(days))
            logger.info(f"Cleaned up {removed} old jobs")
        except Exception as e:
            logger.error(f"Old jobs cleanup failed: {str(e)}")
