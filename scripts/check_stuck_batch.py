#!/usr/bin/env python3
"""
Script to check and potentially recover stuck translation batches
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def check_batch_status(batch_id):
    """Check OpenAI batch status"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    response = requests.get(
        f"https://api.openai.com/v1/batches/{batch_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to get batch status: {response.text}")
        return None

def cancel_batch(batch_id):
    """Cancel a stuck batch"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    response = requests.post(
        f"https://api.openai.com/v1/batches/{batch_id}/cancel",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to cancel batch: {response.text}")
        return None

def main():
    batch_id = "batch_6892745f36ec8190b1d23eac3b3c1e6a"
    
    # Check batch status
    status = check_batch_status(batch_id)
    if not status:
        logger.error("Could not get batch status")
        return
    
    print(f"Batch ID: {batch_id}")
    print(f"Status: {status['status']}")
    print(f"Created: {status['created_at']}")
    print(f"Request counts: {status['request_counts']}")
    
    # Check if batch is stuck (more than 6 hours)
    created_at = datetime.fromtimestamp(status['created_at'])
    age = datetime.now() - created_at
    print(f"Batch age: {age}")
    
    if status['status'] == 'in_progress' and age > timedelta(hours=6):
        print("\n⚠️ This batch appears to be stuck!")
        print("The batch has been running for over 6 hours, which is unusual for 40 translation requests.")
        print("\nOptions:")
        print("1. Wait longer (OpenAI Batch API can take up to 24 hours)")
        print("2. Cancel this batch and retry with a new one")
        print("3. Mark job as completed with English-only results")
        
        # For now, just report the issue
        print("\nRecommendation: Cancel the batch and complete the job with English results")
        print(f"To cancel, run: curl -X POST https://api.openai.com/v1/batches/{batch_id}/cancel -H 'Authorization: Bearer $OPENAI_API_KEY'")

if __name__ == "__main__":
    main()