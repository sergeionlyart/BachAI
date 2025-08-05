import json
import logging
import uuid
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
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
        
        # In-memory storage for batch jobs (in production, use Redis/Database)
        self.active_jobs = {}
    
    def create_batch_job(self, lots: List[Dict[str, Any]], languages: List[str]) -> str:
        """
        Create and submit batch processing job
        """
        job_id = str(uuid.uuid4())
        
        try:
            # Validate batch size limits
            if len(lots) > MAX_LINES:
                raise ValueError(f"Too many lots: {len(lots)} > {MAX_LINES}")
            
            # Process and validate images for all lots
            processed_lots = []
            for lot in lots:
                image_urls = [img['url'] for img in lot.get('images', [])]
                valid_urls, unreachable_urls = self.image_validator.validate_images(image_urls)
                
                # Check if we have enough valid images
                if not self.image_validator.check_image_threshold(len(image_urls), len(valid_urls)):
                    # Mark lot for error file
                    processed_lots.append({
                        'lot_id': lot['lot_id'],
                        'status': 'error',
                        'error': 'image_unreachable',
                        'missing_images': unreachable_urls,
                        'webhook': lot.get('webhook')
                    })
                    continue
                
                processed_lots.append({
                    'lot_id': lot['lot_id'],
                    'valid_images': valid_urls,
                    'missing_images': unreachable_urls,
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
                
                # Create input content in text format with image URLs for now
                # Until multimodal support in Responses API is fully stable
                image_list = "\n".join([f"Image {i+1}: {url}" for i, url in enumerate(lot['valid_images'])])
                input_text = f"Analyze these car images and provide a detailed damage assessment.\n\nAdditional info: {lot['additional_info']}\n\nProvided images:\n{image_list}\n\nNote: Analyze based on the context provided above."
                
                vision_request = {
                    "custom_id": vision_custom_id,
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": {
                        "model": "o4-mini",
                        "reasoning": {"effort": "medium"},
                        "input": input_text,
                        "max_output_tokens": 1024
                    }
                }
                vision_requests.append(vision_request)
            
            # Submit vision batch job
            vision_batch_id = None
            if vision_requests:
                vision_jsonl = self.openai_client.create_batch_file(vision_requests)
                
                # Check file size limits
                if len(vision_jsonl.encode()) > MAX_FILE_BYTES:
                    raise ValueError(f"Batch file too large: {len(vision_jsonl.encode())} > {MAX_FILE_BYTES}")
                
                vision_batch_id = self.openai_client.submit_batch_job(
                    vision_jsonl, 
                    f"Vision processing for job {job_id}"
                )
            
            # Store job information
            self.active_jobs[job_id] = {
                'job_id': job_id,
                'status': 'processing',
                'created_at': datetime.utcnow(),
                'lots': processed_lots,
                'languages': languages,
                'vision_batch_id': vision_batch_id,
                'translation_batch_id': None,
                'vision_results': {},
                'translation_results': {}
            }
            
            logger.info(f"Created batch job {job_id} with vision batch {vision_batch_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Batch job creation failed: {str(e)}")
            raise e
    
    def check_batch_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Check status of batch job
        """
        if job_id not in self.active_jobs:
            return None
        
        job = self.active_jobs[job_id]
        
        try:
            # Check vision batch status
            if job['vision_batch_id'] and job['status'] == 'processing':
                vision_status = self.openai_client.get_batch_status(job['vision_batch_id'])
                
                if vision_status['status'] == 'completed':
                    # Download and process vision results
                    self._process_vision_results(job_id, vision_status)
                elif vision_status['status'] == 'failed':
                    job['status'] = 'failed'
                    job['error'] = 'Vision batch processing failed'
            
            # Check translation batch status
            if job['translation_batch_id'] and job['status'] == 'translating':
                translation_status = self.openai_client.get_batch_status(job['translation_batch_id'])
                
                if translation_status['status'] == 'completed':
                    # Download and process translation results
                    self._process_translation_results(job_id, translation_status)
                    job['status'] = 'completed'
                    
                    # Send webhooks
                    self._send_webhooks(job_id)
                elif translation_status['status'] == 'failed':
                    job['status'] = 'failed'
                    job['error'] = 'Translation batch processing failed'
            
            return {
                'job_id': job_id,
                'status': job['status'],
                'created_at': job['created_at'].isoformat(),
                'error': job.get('error')
            }
            
        except Exception as e:
            logger.error(f"Batch status check failed for {job_id}: {str(e)}")
            job['status'] = 'failed'
            job['error'] = str(e)
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _process_vision_results(self, job_id: str, vision_status: Dict[str, Any]):
        """
        Process completed vision batch results
        """
        job = self.active_jobs[job_id]
        
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
            
            job['vision_results'] = vision_results
            
            # Now submit translation batch if needed
            translation_languages = [lang for lang in job['languages'] if lang.lower() != 'en']
            
            if translation_languages and vision_results:
                self._submit_translation_batch(job_id, vision_results, translation_languages)
                job['status'] = 'translating'
            else:
                # No translation needed, job is complete
                job['status'] = 'completed'
                self._send_webhooks(job_id)
            
        except Exception as e:
            logger.error(f"Vision results processing failed for {job_id}: {str(e)}")
            job['status'] = 'failed'
            job['error'] = f"Vision results processing failed: {str(e)}"
    
    def _submit_translation_batch(self, job_id: str, vision_results: Dict[str, str], languages: List[str]):
        """
        Submit translation batch job
        """
        job = self.active_jobs[job_id]
        
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
                job['translation_batch_id'] = translation_batch_id
                logger.info(f"Submitted translation batch {translation_batch_id} for job {job_id}")
            
        except Exception as e:
            logger.error(f"Translation batch submission failed for {job_id}: {str(e)}")
            raise e
    
    def _process_translation_results(self, job_id: str, translation_status: Dict[str, Any]):
        """
        Process completed translation batch results
        """
        job = self.active_jobs[job_id]
        
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
                                    translation_results[lot_id][language] = job['vision_results'].get(lot_id, "Translation failed")
                            else:
                                logger.error(f"Translation failed for {lot_id}:{language}: {result.get('error', 'Unknown error')}")
                                translation_results[lot_id][language] = job['vision_results'].get(lot_id, "Translation failed")
            
            job['translation_results'] = translation_results
            
        except Exception as e:
            logger.error(f"Translation results processing failed for {job_id}: {str(e)}")
            raise e
    
    def _send_webhooks(self, job_id: str):
        """
        Send webhook notifications for completed job
        """
        job = self.active_jobs[job_id]
        
        try:
            # Group lots by webhook URL
            webhook_groups = {}
            
            for lot in job['lots']:
                webhook_url = lot.get('webhook')
                if webhook_url:
                    if webhook_url not in webhook_groups:
                        webhook_groups[webhook_url] = []
                    
                    lot_id = lot['lot_id']
                    
                    # Prepare descriptions
                    descriptions = []
                    
                    # Add English description
                    if lot_id in job['vision_results']:
                        descriptions.append({
                            'language': 'en',
                            'damages': f"<p>{job['vision_results'][lot_id]}</p>"
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
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        jobs_to_remove = []
        
        for job_id, job in self.active_jobs.items():
            if job['created_at'] < cutoff_time and job['status'] in ['completed', 'failed']:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            logger.info(f"Cleaned up old job {job_id}")
