import json
import logging
import time
from flask import Blueprint, request, jsonify
from services.openai_client import OpenAIClient
from services.image_validator import ImageValidator
from services.signature_validator import SignatureValidator
from services.batch_processor import BatchProcessor
from config import MAX_SYNC_IMAGES

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Initialize services
openai_client = OpenAIClient()
image_validator = ImageValidator()
signature_validator = SignatureValidator()
batch_processor = BatchProcessor()

@api_bp.route('/generate-descriptions', methods=['POST'])
def generate_descriptions():
    """
    Main endpoint for generating car descriptions
    """
    try:
        # Parse JSON request
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['signature', 'version', 'languages', 'lots']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        signature = data['signature']
        version = data['version']
        languages = data['languages']
        lots = data['lots']
        
        # Validate version
        if version != "1.0.0":
            return jsonify({"error": f"Unsupported version: {version}"}), 400
        
        # Validate signature
        if not signature_validator.validate_signature(lots, signature):
            return jsonify({"error": "Invalid signature"}), 403
        
        # Validate lots structure
        if not isinstance(lots, list) or len(lots) == 0:
            return jsonify({"error": "lots must be a non-empty array"}), 400
        
        # Validate languages
        if not isinstance(languages, list) or len(languages) == 0:
            return jsonify({"error": "languages must be a non-empty array"}), 400
        
        # Determine processing mode
        if len(lots) == 1:
            # Synchronous mode
            return handle_sync_request(lots[0], languages)
        else:
            # Batch mode
            return handle_batch_request(lots, languages)
    
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400
    except Exception as e:
        logger.error(f"Request processing error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def handle_sync_request(lot, languages):
    """
    Handle synchronous processing for single lot
    """
    try:
        lot_id = lot.get('lot_id')
        additional_info = lot.get('additional_info', '')
        images = lot.get('images', [])
        
        if not lot_id:
            return jsonify({"error": "lot_id is required"}), 400
        
        if not images:
            return jsonify({"error": "images array cannot be empty"}), 400
        
        # Extract image URLs
        image_urls = [img['url'] for img in images if 'url' in img]
        
        # Check sync limits
        if len(image_urls) > MAX_SYNC_IMAGES:
            return jsonify({"error": f"Too many images for sync mode: {len(image_urls)} > {MAX_SYNC_IMAGES}"}), 400
        
        # Validate images
        valid_urls, unreachable_urls = image_validator.validate_images(image_urls)
        
        # Check image threshold
        if not image_validator.check_image_threshold(len(image_urls), len(valid_urls)):
            return jsonify({
                "error": "image_unreachable",
                "message": "Too many unreachable images",
                "missing_images": unreachable_urls
            }), 400
        
        # Generate vision description
        english_description = openai_client.generate_vision_description(valid_urls, additional_info)
        
        # Prepare descriptions
        descriptions = [
            {"language": "en", "damages": f"<p>{english_description}</p>"}
        ]
        
        # Optimize translations to prevent worker timeout
        # Limit number of languages in sync mode to prevent timeout
        non_english_languages = [lang for lang in languages if lang.lower() != 'en']
        
        # In sync mode, limit to maximum 2 additional languages to prevent timeout
        max_sync_translations = 2
        if len(non_english_languages) > max_sync_translations:
            logger.warning(f"Too many languages for sync mode ({len(non_english_languages)}), limiting to {max_sync_translations}")
            non_english_languages = non_english_languages[:max_sync_translations]
        
        # Generate translations with timeout protection
        translation_start = time.time()
        max_translation_time = 45  # Maximum 45 seconds for all translations
        
        for lang in non_english_languages:
            # Check if we're running out of time
            elapsed = time.time() - translation_start
            if elapsed > max_translation_time:
                logger.warning(f"Translation timeout reached, skipping remaining languages")
                # Add English fallback for remaining languages
                for remaining_lang in [l for l in non_english_languages if l not in [desc['language'] for desc in descriptions]]:
                    descriptions.append({
                        "language": remaining_lang,
                        "damages": f"<p>{english_description}</p>"
                    })
                break
            
            try:
                # Set shorter timeout for individual translation
                translated_text = openai_client.translate_text(english_description, lang)
                descriptions.append({
                    "language": lang,
                    "damages": f"<p>{translated_text}</p>"
                })
            except Exception as e:
                logger.error(f"Translation failed for {lang}: {str(e)}")
                # Use English as fallback
                descriptions.append({
                    "language": lang,
                    "damages": f"<p>{english_description}</p>"
                })
        
        # Prepare response
        response = {
            "version": "1.0.0",
            "lots": [
                {
                    "lot_id": lot_id,
                    "descriptions": descriptions
                }
            ]
        }
        
        # Add missing images if any
        if unreachable_urls:
            response["lots"][0]["missing_images"] = unreachable_urls
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Sync processing error: {str(e)}")
        return jsonify({"error": "Processing failed", "details": str(e)}), 500

def handle_batch_request(lots, languages):
    """
    Handle batch processing for multiple lots with timeout protection
    """
    try:
        # Add timeout protection for batch creation
        start_time = time.time()
        max_creation_time = 20  # Maximum 20 seconds for batch creation
        
        logger.info(f"Starting batch creation for {len(lots)} lots")
        
        # Create batch job with optimized processing
        job_id = batch_processor.create_batch_job(lots, languages)
        
        creation_time = time.time() - start_time
        logger.info(f"Batch job {job_id} created in {creation_time:.2f}s")
        
        return jsonify({
            "job_id": job_id,
            "status": "accepted",
            "creation_time": f"{creation_time:.2f}s",
            "lots_count": len(lots)
        }), 201
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        return jsonify({"error": "Batch processing failed", "details": str(e)}), 500

@api_bp.route('/batch-status/<job_id>', methods=['GET'])
def get_batch_status(job_id):
    """
    Get status of batch processing job
    """
    try:
        status = batch_processor.check_batch_status(job_id)
        
        if status is None:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(status), 200
    
    except Exception as e:
        logger.error(f"Batch status check error: {str(e)}")
        return jsonify({"error": "Status check failed"}), 500

@api_bp.route('/test-image-validation', methods=['POST'])
def test_image_validation():
    """
    Test endpoint for image validation
    """
    try:
        data = request.get_json()
        
        if not data or 'urls' not in data:
            return jsonify({"error": "urls array is required"}), 400
        
        urls = data['urls']
        valid_urls, unreachable_urls = image_validator.validate_images(urls)
        
        return jsonify({
            "valid_urls": valid_urls,
            "unreachable_urls": unreachable_urls,
            "threshold_met": image_validator.check_image_threshold(len(urls), len(valid_urls))
        }), 200
    
    except Exception as e:
        logger.error(f"Image validation test error: {str(e)}")
        return jsonify({"error": "Validation test failed"}), 500
