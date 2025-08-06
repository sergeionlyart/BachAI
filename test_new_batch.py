#!/usr/bin/env python3
"""Test script to create a new batch and verify the fix works"""

import requests
import json
import time
import hmac
import hashlib

# Configuration
BASE_URL = "http://localhost:5000"
SHARED_KEY = "dev-secret-key-for-testing-2024"

def generate_signature(payload: str) -> str:
    """Generate HMAC-SHA256 signature"""
    return hmac.new(
        SHARED_KEY.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# Test data - simple batch with 2 cars
test_data = {
    "version": "1.0.0",
    "languages": ["en"],  # English only for quick test
    "lots": [
        {
            "lot_id": "TEST_CAR_001",
            "images": [
                "https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=800",  # Ferrari
                "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800"   # Chevrolet
            ]
        },
        {
            "lot_id": "TEST_CAR_002", 
            "images": [
                "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=800",  # Mustang
                "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800"   # Porsche
            ]
        }
    ]
}

# Generate signature based on the complete JSON payload
payload_str = json.dumps(test_data)
signature = generate_signature(payload_str)
test_data["signature"] = signature

print("Creating test batch...")
response = requests.post(
    f"{BASE_URL}/api/v1/generate-descriptions",
    json=test_data,
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    result = response.json()
    job_id = result.get("job_id")
    print(f"✓ Batch created successfully!")
    print(f"  Job ID: {job_id}")
    print(f"  Status: {result.get('status')}")
    print(f"  Processing mode: {result.get('processing_mode')}")
    
    # Wait a bit for processing
    print("\nWaiting 30 seconds for batch to process...")
    time.sleep(30)
    
    # Check status
    status_payload = json.dumps({"job_id": job_id})
    status_signature = generate_signature(status_payload)
    
    print("\nChecking batch status...")
    status_response = requests.get(
        f"{BASE_URL}/api/v1/batch-status/{job_id}",
        headers={"X-Signature": status_signature}
    )
    
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"  Status: {status.get('status')}")
        print(f"  Progress: {status.get('processed_lots')}/{status.get('total_lots')} lots")
        
        if status.get('openai_batch_id'):
            print(f"  OpenAI Batch ID: {status.get('openai_batch_id')}")
    else:
        print(f"  Error checking status: {status_response.text}")
        
else:
    print(f"✗ Failed to create batch: {response.status_code}")
    print(f"  Error: {response.text}")

print("\n=== Test Complete ===")
print("Monitor the Background Worker logs to see if vision results are extracted correctly.")
print("The fix should extract actual text from body.output[0].content[0].text")
print("NOT from body.text which only contains format info.")