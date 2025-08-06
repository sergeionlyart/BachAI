# API Usage with Webhooks - Technical Documentation

## Table of Contents
- [Quick Start](#quick-start)
- [Webhook Configuration](#webhook-configuration)
- [Payload Format](#payload-format)
- [Security & Authentication](#security--authentication)
- [Error Handling & Retries](#error-handling--retries)
- [Integration Examples](#integration-examples)
- [Monitoring & Debugging](#monitoring--debugging)
- [Best Practices](#best-practices)
- [FAQ](#faq)

---

## Quick Start

### 1. Create a Job with Webhook

```bash
curl -X POST https://your-service.com/api/v1/generate-descriptions \
  -H "Content-Type: application/json" \
  -d '{
    "signature": "your_hmac_sha256_signature",
    "version": "1.0.0",
    "languages": ["en", "ru", "es"],
    "webhook_url": "https://your-domain.com/api/webhooks/car-descriptions",
    "lots": [
      {
        "lot_id": "CAR_001",
        "images": [
          "https://example.com/car1_front.jpg",
          "https://example.com/car1_side.jpg",
          "https://example.com/car1_interior.jpg"
        ]
      },
      {
        "lot_id": "CAR_002", 
        "images": [
          "https://example.com/car2_front.jpg",
          "https://example.com/car2_damage.jpg"
        ]
      }
    ]
  }'
```

### 2. Implement Webhook Endpoint

Your webhook endpoint must:
- Accept HTTP POST requests
- Return HTTP 200-299 for successful processing
- Respond within 30 seconds
- Validate the HMAC signature

---

## Webhook Configuration

### Webhook URL Requirements

| Requirement | Details |
|-------------|---------|
| **Protocol** | HTTPS recommended, HTTP allowed for development |
| **Method** | POST only |
| **Timeout** | 30 seconds maximum |
| **Response** | HTTP 200-299 for success |
| **Content-Type** | Must accept `application/json` |

### Request Headers

```http
POST /your/webhook/endpoint HTTP/1.1
Host: your-domain.com
Content-Type: application/json
User-Agent: Generation-Service/1.0
X-Signature: 1a2b3c4d5e6f7890abcdef...
Content-Length: 234
```

---

## Payload Format

### Standard Completion Notification

```json
{
  "job_id": "365a09ce-5416-49b5-8471-d6aad042761c",
  "status": "completed",
  "timestamp": "2025-08-06T11:30:00.000Z",
  "total_lots": 10,
  "completed_lots": 9,
  "failed_lots": 1,
  "processing_time_seconds": 1834,
  "webhook_url": "https://your-domain.com/api/webhooks/car-descriptions",
  "results_available": true,
  "batch_info": {
    "openai_batch_id": "batch_abc123def456",
    "vision_completed": true,
    "translation_completed": true
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier (UUID) |
| `status` | enum | `completed`, `failed`, `partially_completed` |
| `timestamp` | string | ISO 8601 completion timestamp |
| `total_lots` | integer | Total number of car lots in the job |
| `completed_lots` | integer | Successfully processed lots |
| `failed_lots` | integer | Lots that failed processing |
| `processing_time_seconds` | integer | Total processing duration |
| `webhook_url` | string | Your webhook URL (for verification) |
| `results_available` | boolean | Whether results can be fetched |
| `batch_info` | object | OpenAI batch processing details |

### Status Types

- **`completed`**: All lots processed successfully
- **`partially_completed`**: Some lots failed, but results available
- **`failed`**: Job failed completely, no results available

---

## Security & Authentication

### HMAC-SHA256 Signature Validation

Every webhook request includes an `X-Signature` header containing HMAC-SHA256 signature.

#### Signature Generation Algorithm

```python
import hmac
import hashlib

def generate_signature(payload: str, secret_key: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload"""
    return hmac.new(
        secret_key.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
```

#### Validation Implementation

```python
import hmac
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = "your-shared-secret-key"

def verify_webhook_signature(payload: str, signature: str) -> bool:
    """Verify webhook signature using constant-time comparison"""
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@app.route('/api/webhooks/car-descriptions', methods=['POST'])
def handle_webhook():
    # Get raw payload and signature
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Signature')
    
    # Validate signature
    if not signature or not verify_webhook_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 403
    
    # Process webhook
    data = request.get_json()
    process_job_completion(data)
    
    return jsonify({'success': True, 'received_at': datetime.utcnow().isoformat()})

def process_job_completion(data):
    job_id = data['job_id']
    status = data['status']
    
    if data.get('results_available'):
        # Fetch results using polling API
        fetch_job_results(job_id)
    
    # Update your database
    update_job_status(job_id, status, data)
```

---

## Error Handling & Retries

### Retry Strategy

The webhook system implements exponential backoff with the following parameters:

| Attempt | Delay | Cumulative Time |
|---------|-------|-----------------|
| 1 | Immediate | 0 min |
| 2 | 1 minute | 1 min |
| 3 | 2 minutes | 3 min |
| 4 | 4 minutes | 7 min |
| 5 | 8 minutes | 15 min |
| Final | 16 minutes | 31 min |

### Response Code Handling

| Status Code Range | Action | Retry |
|-------------------|--------|-------|
| 200-299 | Success | No |
| 400-499 | Client Error | No |
| 500-599 | Server Error | Yes |
| Timeout (30s) | Timeout Error | Yes |
| Connection Error | Network Error | Yes |

### Error Response Examples

```python
# Client error - no retry
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    try:
        data = request.get_json()
        if not validate_webhook_data(data):
            return jsonify({'error': 'Invalid data format'}), 400
            
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400

# Server error - will retry
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    try:
        process_webhook(request.get_json())
        return jsonify({'success': True}), 200
        
    except DatabaseError as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({'error': 'Temporary database issue'}), 503
```

---

## Integration Examples

### Flask + SQLAlchemy Integration

```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hmac, hashlib, requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/db'
db = SQLAlchemy(app)

class JobStatus(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(20), nullable=False)
    total_lots = db.Column(db.Integer)
    completed_lots = db.Column(db.Integer)
    failed_lots = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime)
    results_fetched = db.Column(db.Boolean, default=False)

@app.route('/webhooks/car-descriptions', methods=['POST'])
def car_description_webhook():
    # Validate signature
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Signature')
    
    if not verify_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 403
    
    data = request.get_json()
    job_id = data['job_id']
    
    # Update database
    job = JobStatus.query.get(job_id)
    if not job:
        job = JobStatus(id=job_id)
        db.session.add(job)
    
    job.status = data['status']
    job.total_lots = data['total_lots']
    job.completed_lots = data['completed_lots']
    job.failed_lots = data['failed_lots']
    job.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    # Fetch results if available
    if data.get('results_available') and not job.results_fetched:
        fetch_and_store_results.delay(job_id)  # Async task
    
    return jsonify({'success': True})

def fetch_and_store_results(job_id):
    """Background task to fetch and store results"""
    response = requests.get(
        f'https://api.service.com/api/v1/jobs/{job_id}/results',
        headers={'Authorization': 'Bearer your-token'}
    )
    
    if response.status_code == 200:
        results = response.json()
        # Store results in your system
        store_car_descriptions(job_id, results)
        
        # Mark as fetched
        job = JobStatus.query.get(job_id)
        job.results_fetched = True
        db.session.commit()
```

### Express.js + MongoDB Integration

```javascript
const express = require('express');
const crypto = require('crypto');
const mongoose = require('mongoose');
const axios = require('axios');

const app = express();
app.use(express.raw({type: 'application/json'}));

const JobSchema = new mongoose.Schema({
  _id: String,
  status: String,
  totalLots: Number,
  completedLots: Number,
  failedLots: Number,
  completedAt: Date,
  resultsFetched: Boolean
});

const Job = mongoose.model('Job', JobSchema);

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;

function verifySignature(payload, signature) {
  const expectedSignature = crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

app.post('/webhooks/car-descriptions', async (req, res) => {
  const payload = req.body.toString();
  const signature = req.headers['x-signature'];
  
  // Validate signature
  if (!signature || !verifySignature(payload, signature)) {
    return res.status(403).json({error: 'Invalid signature'});
  }
  
  const data = JSON.parse(payload);
  const jobId = data.job_id;
  
  try {
    // Update job status
    await Job.findByIdAndUpdate(jobId, {
      _id: jobId,
      status: data.status,
      totalLots: data.total_lots,
      completedLots: data.completed_lots,
      failedLots: data.failed_lots,
      completedAt: new Date()
    }, { upsert: true });
    
    // Fetch results if available
    if (data.results_available) {
      fetchJobResults(jobId);
    }
    
    res.json({success: true});
    
  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(500).json({error: 'Internal server error'});
  }
});

async function fetchJobResults(jobId) {
  try {
    const response = await axios.get(
      `https://api.service.com/api/v1/jobs/${jobId}/results`,
      { headers: { 'Authorization': 'Bearer your-token' } }
    );
    
    // Store results
    await storeCarDescriptions(jobId, response.data);
    
    // Mark as fetched
    await Job.findByIdAndUpdate(jobId, { resultsFetched: true });
    
  } catch (error) {
    console.error('Failed to fetch results:', error);
  }
}
```

---

## Monitoring & Debugging

### Webhook Monitoring API

Check webhook system health and performance:

```bash
# Get delivery metrics for last 24 hours
curl "https://api.service.com/api/v1/webhook-metrics?hours=24"

# Response:
{
  "success": true,
  "metrics": {
    "period_hours": 24,
    "total_webhooks": 150,
    "delivered": 145,
    "failed": 2,
    "pending": 3,
    "success_rate": 96.67,
    "average_retries": 0.8,
    "average_delivery_time_seconds": 2.3
  }
}
```

```bash
# Get system health status
curl "https://api.service.com/api/v1/webhook-health"

# Response:
{
  "success": true,
  "report": {
    "health_score": 95,
    "health_status": "healthy",
    "alerts": [],
    "metrics_24h": {...},
    "failed_webhooks": []
  }
}
```

```bash
# Get failed delivery details
curl "https://api.service.com/api/v1/webhook-failures?limit=5"

# Response:
{
  "success": true,
  "failed_webhooks": [
    {
      "id": "webhook-123",
      "webhook_url": "https://client.com/webhook",
      "attempt_count": 5,
      "error_message": "Connection timeout",
      "last_attempt": "2025-08-06T10:30:00Z"
    }
  ]
}
```

### Debugging Checklist

1. **Webhook URL Accessibility**
   ```bash
   curl -X POST https://your-domain.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": true}'
   ```

2. **SSL Certificate Validation**
   ```bash
   openssl s_client -connect your-domain.com:443 -servername your-domain.com
   ```

3. **Response Time Testing**
   ```bash
   time curl -X POST https://your-domain.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": true}'
   ```

4. **Signature Validation Testing**
   ```python
   import hmac, hashlib
   
   payload = '{"test": true}'
   secret = "your-secret-key"
   signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
   print(f"Expected signature: {signature}")
   ```

---

## Best Practices

### Performance Optimization

1. **Quick Response Pattern**
   ```python
   @app.route('/webhook', methods=['POST'])
   def webhook_handler():
       data = request.get_json()
       
       # Immediately queue for background processing
       process_webhook_async.delay(data)
       
       # Return success quickly
       return jsonify({'success': True}), 200
   ```

2. **Database Optimization**
   ```python
   # Use database transactions
   with db.session.begin():
       job = Job.query.get(job_id)
       job.status = 'completed'
       # All operations in single transaction
   ```

3. **Connection Pooling**
   ```python
   # Configure connection pools
   app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
       'pool_size': 20,
       'pool_recycle': 3600,
       'pool_pre_ping': True
   }
   ```

### Security Best Practices

1. **Always Verify Signatures**
   ```python
   def secure_webhook_handler(request):
       if not verify_signature(request.data, request.headers.get('X-Signature')):
           raise SecurityError('Invalid signature')
   ```

2. **Rate Limiting**
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(app, key_func=get_remote_address)
   
   @app.route('/webhook', methods=['POST'])
   @limiter.limit("100 per minute")
   def webhook_handler():
       pass
   ```

3. **Input Validation**
   ```python
   from marshmallow import Schema, fields, ValidationError
   
   class WebhookSchema(Schema):
       job_id = fields.UUID(required=True)
       status = fields.Str(validate=validate.OneOf(['completed', 'failed']))
       total_lots = fields.Int(validate=validate.Range(min=1))
   
   def validate_webhook(data):
       schema = WebhookSchema()
       try:
           return schema.load(data)
       except ValidationError as e:
           raise BadRequest(f'Invalid webhook data: {e.messages}')
   ```

### Reliability Patterns

1. **Idempotency**
   ```python
   def process_webhook(data):
       job_id = data['job_id']
       
       # Check if already processed
       if Job.query.filter_by(id=job_id, processed=True).first():
           return {'message': 'Already processed'}
       
       # Process only once
       process_job_completion(data)
       Job.query.filter_by(id=job_id).update({'processed': True})
   ```

2. **Graceful Degradation**
   ```python
   def webhook_handler():
       try:
           process_webhook_immediately()
       except DatabaseError:
           # Fall back to file-based queue
           queue_webhook_to_file(data)
           return jsonify({'status': 'queued'})
   ```

3. **Circuit Breaker Pattern**
   ```python
   from circuit_breaker import CircuitBreaker
   
   @CircuitBreaker(failure_threshold=5, recovery_timeout=30)
   def external_api_call():
       return requests.post('https://external-api.com/process')
   ```

---

## FAQ

### Q: How long should I wait before considering a webhook lost?

**A:** The system retries for up to 31 minutes total. If you haven't received a webhook after 45 minutes, use the polling API to check job status.

### Q: Can I use the same webhook URL for multiple jobs?

**A:** Yes, the webhook URL can be reused. Each webhook payload includes the unique `job_id` to identify which job completed.

### Q: What happens if my webhook endpoint is temporarily down?

**A:** The system will retry up to 5 times with exponential backoff. If all retries fail, you can check the job status using the polling API.

### Q: How do I test webhooks during development?

**A:** Use ngrok or similar tools to create a public tunnel to your local development server:
```bash
ngrok http 3000
# Use the generated HTTPS URL as your webhook_url
```

### Q: Should I verify the webhook signature?

**A:** Absolutely! Always verify the `X-Signature` header to ensure the webhook is legitimate and hasn't been tampered with.

### Q: Can I change the webhook URL after submitting a job?

**A:** No, the webhook URL is set when the job is created and cannot be modified. You'll need to use the polling API if you need to receive updates at a different endpoint.

### Q: What's the maximum payload size for webhooks?

**A:** Webhook payloads are typically under 1KB. The exact size depends on the number of lots and metadata, but it's well within standard HTTP limits.

### Q: How do I handle webhook delivery failures?

**A:** Implement robust error handling and monitoring:
1. Log all webhook receipts and processing results
2. Use the webhook monitoring APIs to track delivery health
3. Implement fallback polling for critical applications
4. Set up alerts for webhook delivery failures

---

## Support

For technical support with webhook integration:

1. Check the [webhook monitoring endpoints](#monitoring--debugging)
2. Review your webhook endpoint logs
3. Verify your HMAC signature implementation
4. Test your endpoint with the provided debugging tools
5. Contact support with specific error details and webhook delivery IDs

**Documentation Version:** 2.0  
**Last Updated:** August 6, 2025  
**API Version:** 1.0.0