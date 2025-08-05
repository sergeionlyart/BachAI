import hashlib
import hmac
import logging
from flask import request
from config import SHARED_KEY

logger = logging.getLogger(__name__)

def verify_signature(request_obj) -> bool:
    """
    Verify HMAC-SHA256 signature for request authentication
    """
    try:
        # Get signature from header
        signature = request_obj.headers.get('X-Signature')
        if not signature:
            logger.warning("Missing X-Signature header")
            return False
        
        # Get request body
        body = request_obj.get_data()
        if not body:
            logger.warning("Missing request body for signature verification")
            return False
        
        # Calculate expected signature
        expected_signature = hmac.new(
            SHARED_KEY.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        return False

def generate_signature(payload: bytes) -> str:
    """
    Generate HMAC-SHA256 signature for payload
    """
    try:
        signature = hmac.new(
            SHARED_KEY.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return signature
    except Exception as e:
        logger.error(f"Error generating signature: {str(e)}")
        raise e