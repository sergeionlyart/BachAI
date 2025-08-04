import json
import logging
import time
import requests
from typing import List, Dict, Any
from services.signature_validator import SignatureValidator
from utils.retry import exponential_backoff
from config import WEBHOOK_RETRY_ATTEMPTS, WEBHOOK_BASE_DELAY

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self):
        self.signature_validator = SignatureValidator()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Generation-Service/1.0.0'
        })
    
    def send_webhook(self, webhook_url: str, lots_data: List[Dict[str, Any]]):
        """
        Send webhook with retry logic
        """
        try:
            # Prepare webhook payload
            payload = {
                "version": "1.0.0",
                "lots": lots_data
            }
            
            # Generate signature
            payload["signature"] = self.signature_validator.generate_signature(lots_data)
            
            # Send with retry logic
            self._send_with_retry(webhook_url, payload)
            
        except Exception as e:
            logger.error(f"Webhook sending failed for {webhook_url}: {str(e)}")
    
    def _send_with_retry(self, webhook_url: str, payload: Dict[str, Any]):
        """
        Send webhook with exponential backoff retry
        """
        last_exception = None
        
        for attempt in range(WEBHOOK_RETRY_ATTEMPTS):
            try:
                response = self.session.post(
                    webhook_url,
                    json=payload,
                    timeout=30
                )
                
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook sent successfully to {webhook_url} on attempt {attempt + 1}")
                    return
                else:
                    logger.warning(f"Webhook failed with status {response.status_code} for {webhook_url}")
                    last_exception = Exception(f"HTTP {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"Webhook attempt {attempt + 1} failed for {webhook_url}: {str(e)}")
                last_exception = e
            
            # Calculate delay for next attempt
            if attempt < WEBHOOK_RETRY_ATTEMPTS - 1:
                delay = exponential_backoff(attempt, WEBHOOK_BASE_DELAY)
                logger.info(f"Retrying webhook in {delay} seconds")
                time.sleep(delay)
        
        # All retries failed
        logger.error(f"All webhook retry attempts failed for {webhook_url}. Last error: {str(last_exception)}")
        if last_exception:
            raise last_exception
        else:
            raise Exception("All webhook retry attempts failed")
