import os

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# HMAC Security
SHARED_KEY = os.getenv("SHARED_KEY", "default-shared-key-change-in-production")

# Vision System Prompt
VISION_SYSTEM_PROMPT = os.getenv(
    "VISION_SYSTEM_PROMPT", 
    """You are an expert automotive damage assessor. Analyze the provided car images and generate a detailed description of any visible damage, condition issues, or notable features. Focus on:
- Exterior damage (dents, scratches, rust, paint issues)
- Interior condition (wear, tears, stains)
- Mechanical visible issues
- Overall condition assessment
- Market-relevant details for potential buyers

Provide your response in clear, professional language suitable for a vehicle listing. Be specific about locations and severity of any damage found."""
)

# Processing Limits
MAX_LINE_BYTES = 1_048_576  # 1 MB
MAX_FILE_BYTES = 200_000_000  # 200 MB
MAX_LINES = 50_000
MAX_SYNC_IMAGES = 20
MAX_IMAGE_SIZE = 10_000_000  # 10 MB

# Translation configuration
SYNC_TRANSLATION_WARNING_THRESHOLD = int(
    os.getenv("SYNC_TRANSLATION_WARNING_THRESHOLD", "5")
)

# Batch API Limits
ACTIVE_BATCH_LIMIT_KEY = int(os.getenv("ACTIVE_BATCH_LIMIT_KEY", "2"))
ACTIVE_BATCH_LIMIT_GLB = int(os.getenv("ACTIVE_BATCH_LIMIT_GLB", "10"))

# Retry Configuration
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "5"))
BASE_DELAY_SEC = int(os.getenv("BASE_DELAY_SEC", "2"))

# Image Validation Timeouts
IMAGE_HEAD_TIMEOUT = int(os.getenv("IMAGE_HEAD_TIMEOUT", "3"))
IMAGE_GET_TIMEOUT = int(os.getenv("IMAGE_GET_TIMEOUT", "5"))
IMAGE_GET_MAX_SIZE = int(os.getenv("IMAGE_GET_MAX_SIZE", "32768"))  # 32 KB for fallback GET

# Webhook Configuration
WEBHOOK_RETRY_ATTEMPTS = int(os.getenv("WEBHOOK_RETRY_ATTEMPTS", "5"))
WEBHOOK_BASE_DELAY = int(os.getenv("WEBHOOK_BASE_DELAY", "1"))
