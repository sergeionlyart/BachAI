import json
import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import OPENAI_API_KEY, VISION_SYSTEM_PROMPT
from utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        # Configure client with proper timeout settings to prevent worker timeouts
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=60.0,  # 60 second timeout for individual requests
            max_retries=2
        )
    
    @retry_with_backoff()
    def generate_vision_description(self, images: List[str], additional_info: str = "") -> str:
        """
        Generate car description using OpenAI o4-mini model via Responses API
        """
        try:
            # Log request start for debugging timeout issues
            start_time = time.time()
            logger.info(f"Starting vision description generation for {len(images)} images")
            
            # Prepare the user prompt with additional context
            user_prompt = f"{VISION_SYSTEM_PROMPT}\n\nAdditional context: {additional_info}" if additional_info else VISION_SYSTEM_PROMPT
            
            # For now, use text-only input until multimodal support in Responses API is stable
            # Format all information including image URLs as text input
            if len(images) == 0:
                input_content = user_prompt
            else:
                # Include image URLs in text format for now
                image_list = "\n".join([f"Image {i+1}: {url}" for i, url in enumerate(images)])
                input_content = f"{user_prompt}\n\nProvided images:\n{image_list}\n\nNote: Analyze based on the context provided above."
            
            # Make request to Responses API using o4-mini model
            # the newest OpenAI model is "o4-mini" which was released after knowledge cutoff.
            # do not change this unless explicitly requested by the user
            response = self.client.responses.create(
                model="o4-mini",
                reasoning={"effort": "medium"},
                input=input_content,
                max_output_tokens=2048
            )
            
            # Log completion time
            duration = time.time() - start_time
            logger.info(f"Vision description completed in {duration:.2f} seconds")
            
            if response.status == "incomplete":
                logger.warning(f"Incomplete response: {response.incomplete_details}")
                if response.output_text:
                    return response.output_text
                else:
                    raise Exception("Response incomplete during reasoning phase")
            
            return response.output_text or ""
            
        except Exception as e:
            try:
                duration = time.time() - start_time
            except NameError:
                duration = 0
            logger.error(f"Vision API error after {duration:.2f}s: {str(e)}")
            
            if "context_length" in str(e).lower():
                # Try with fewer images or shorter prompt
                if len(images) > 1:
                    logger.info("Retrying with first image only due to context length")
                    return self.generate_vision_description(images[:1], additional_info)
            raise e
    
    @retry_with_backoff()
    def translate_text(self, text: str, target_language: str) -> str:
        """
        Translate text to target language using gpt-4.1-mini via Responses API
        """
        try:
            # Skip translation if target is English
            if target_language.lower() == 'en':
                return text
            
            # Log translation start for debugging timeout issues
            start_time = time.time()
            logger.info(f"Starting translation to {target_language}")
            
            # Prepare input for Responses API as simple text
            input_content = f"Translate the following text into {target_language} only. Maintain the original formatting and meaning:\n\n{text}"
            
            # Use gpt-4.1-mini via Responses API for translation
            # Note: gpt-4.1-mini doesn't support reasoning parameter
            response = self.client.responses.create(
                model="gpt-4.1-mini",
                input=input_content,
                max_output_tokens=2048
            )
            
            # Log completion time
            duration = time.time() - start_time
            logger.info(f"Translation to {target_language} completed in {duration:.2f} seconds")
            
            if response.status == "incomplete":
                logger.warning(f"Translation incomplete: {response.incomplete_details}")
                if response.output_text:
                    return response.output_text
                else:
                    # Fallback to original text if translation fails
                    logger.warning(f"Translation failed, returning original text")
                    return text
            
            return response.output_text or text
            
        except Exception as e:
            try:
                duration = time.time() - start_time
            except NameError:
                duration = 0
            logger.error(f"Translation API error for {target_language} after {duration:.2f}s: {str(e)}")
            # Return original text instead of raising error to prevent total failure
            logger.warning(f"Translation failed, returning original text for {target_language}")
            return text
    
    def create_batch_file(self, requests: List[Dict[str, Any]]) -> str:
        """
        Create JSONL file for batch processing
        """
        jsonl_content = []
        for req in requests:
            jsonl_content.append(json.dumps(req, separators=(',', ':')))
        
        return '\n'.join(jsonl_content)
    
    def submit_batch_job(self, jsonl_content: str, description: str) -> str:
        """
        Submit batch job to OpenAI with proper file handling
        """
        try:
            # Create file with proper filename parameter
            import io
            file_obj = io.BytesIO(jsonl_content.encode('utf-8'))
            
            file_response = self.client.files.create(
                file=(f"batch_{int(time.time())}.jsonl", file_obj, "application/jsonl"),
                purpose="batch"
            )
            
            # Create batch job targeting Responses API
            batch_response = self.client.batches.create(
                input_file_id=file_response.id,
                endpoint="/v1/responses",
                completion_window="24h",
                metadata={"description": description}
            )
            
            logger.info(f"Created batch job {batch_response.id} with file {file_response.id}")
            return batch_response.id
            
        except Exception as e:
            logger.error(f"Batch submission error: {str(e)}")
            raise e
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get batch job status
        """
        try:
            batch = self.client.batches.retrieve(batch_id)
            return {
                "id": batch.id,
                "status": batch.status,
                "completed_at": batch.completed_at,
                "failed_at": batch.failed_at,
                "output_file_id": batch.output_file_id,
                "error_file_id": batch.error_file_id,
                "request_counts": batch.request_counts.__dict__ if batch.request_counts else None
            }
        except Exception as e:
            logger.error(f"Batch status error: {str(e)}")
            raise e
    
    def download_batch_results(self, file_id: str) -> str:
        """
        Download batch results file
        """
        try:
            file_response = self.client.files.content(file_id)
            return file_response.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Batch download error: {str(e)}")
            raise e
