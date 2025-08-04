import hmac
import hashlib
import json
import logging
from typing import List, Dict, Any
from config import SHARED_KEY

logger = logging.getLogger(__name__)

class SignatureValidator:
    def __init__(self):
        self.shared_key = SHARED_KEY
    
    def generate_signature(self, lots: List[Dict[str, Any]]) -> str:
        """
        Generate HMAC-SHA256 signature for lots data
        """
        try:
            # Normalize JSON (no spaces, sorted keys)
            normalized = json.dumps(lots, separators=(',', ':'), sort_keys=True)
            
            # Generate HMAC-SHA256
            signature = hmac.new(
                self.shared_key.encode(),
                normalized.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"Signature generation error: {str(e)}")
            raise e
    
    def validate_signature(self, lots: List[Dict[str, Any]], provided_signature: str) -> bool:
        """
        Validate provided signature against lots data
        """
        try:
            expected_signature = self.generate_signature(lots)
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_signature, provided_signature)
            
        except Exception as e:
            logger.error(f"Signature validation error: {str(e)}")
            return False
    
    def validate_webhook_signature(self, lots: List[Dict[str, Any]], provided_signature: str) -> bool:
        """
        Validate webhook signature (same as request signature)
        """
        return self.validate_signature(lots, provided_signature)
