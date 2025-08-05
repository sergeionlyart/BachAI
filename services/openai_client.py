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
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=60.0,  # 60 second timeout for API calls
            max_retries=2
        )
    
    @retry_with_backoff()
    def generate_vision_description(self, images: List[str], additional_info: str = "") -> str:
        """
        Generate car description using OpenAI Vision model (gpt-4o)
        """
        try:
            # Prepare the user prompt with additional context
            user_prompt = f"{VISION_SYSTEM_PROMPT}\n\nAdditional context: {additional_info}" if additional_info else VISION_SYSTEM_PROMPT
            
            # For vision tasks, we use gpt-4o which supports image analysis
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt}
                    ] + [
                        {"type": "image_url", "image_url": {"url": img_url, "detail": "low"}}
                        for img_url in images
                    ]
                }
            ]
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1024,
                temperature=0.3  # Lower temperature for more consistent output
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"Vision API error: {str(e)}")
            if "context_length" in str(e).lower():
                # Try with fewer images or shorter prompt
                if len(images) > 1:
                    logger.info("Retrying with first image only due to context length")
                    return self.generate_vision_description(images[:1], additional_info)
            raise e
    
    @retry_with_backoff()
    def translate_text(self, text: str, target_language: str) -> str:
        """
        Translate text to target language using gpt-4o-mini
        """
        try:
            # Skip translation if target is English
            if target_language.lower() == 'en':
                return text
            
            system_prompt = f"Translate the following text into {target_language} only. Maintain the original formatting and meaning."
            
            # Use gpt-4o-mini for translation which is more cost-effective
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                max_tokens=2048,
                temperature=0.3  # Lower temperature for more consistent translations
            )
            
            return response.choices[0].message.content or text
            
        except Exception as e:
            logger.error(f"Translation API error for {target_language}: {str(e)}")
            raise e
    
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
        Submit batch job to OpenAI
        """
        try:
            # Create file with proper filename
            import io
            file_obj = io.BytesIO(jsonl_content.encode())
            file_obj.name = "batch_requests.jsonl"  # Add filename for proper file handling
            
            file_response = self.client.files.create(
                file=file_obj,
                purpose="batch"
            )
            
            # Create batch job
            batch_response = self.client.batches.create(
                input_file_id=file_response.id,
                endpoint="/v1/chat/completions",  # Use chat completions endpoint
                completion_window="24h",
                metadata={"description": description}
            )
            
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
