import logging
from flask import Blueprint, request, jsonify
from services.database_manager import DatabaseManager
from database.models import db
from utils.auth import verify_signature

logger = logging.getLogger(__name__)

# Create blueprint for polling API endpoints
polling_bp = Blueprint('polling', __name__, url_prefix='/api/v1')

def get_db_manager():
    """Get database manager instance"""
    return DatabaseManager(db.session)

@polling_bp.route('/batch-status/<job_id>', methods=['GET'])
def get_batch_status(job_id: str):
    """
    Get batch job status for polling
    
    GET /api/v1/batch-status/{job_id}
    """
    try:
        # Verify signature
        if not verify_signature(request):
            return jsonify({"error": "Invalid signature"}), 401
        
        db_manager = get_db_manager()
        
        # Get job from database
        job = db_manager.get_batch_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Return job status
        response = {
            "job_id": job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "progress": {
                "total_lots": job.total_lots,
                "processed_lots": job.processed_lots,
                "failed_lots": job.failed_lots,
                "completion_percentage": round((job.processed_lots / job.total_lots * 100) if job.total_lots > 0 else 0, 2)
            },
            "languages": job.languages,
            "error_message": job.error_message
        }
        
        # Add OpenAI batch information if available
        if job.openai_vision_batch_id:
            response["openai_vision_batch_id"] = job.openai_vision_batch_id
        if job.openai_translation_batch_id:
            response["openai_translation_batch_id"] = job.openai_translation_batch_id
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting batch status {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@polling_bp.route('/batch-results/<job_id>', methods=['GET'])
def get_batch_results(job_id: str):
    """
    Get batch job results for polling
    
    GET /api/v1/batch-results/{job_id}
    """
    try:
        # Verify signature
        if not verify_signature(request):
            return jsonify({"error": "Invalid signature"}), 401
        
        db_manager = get_db_manager()
        
        # Get job from database
        job = db_manager.get_batch_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Check if job is completed
        if job.status != 'completed':
            return jsonify({
                "error": "Job not completed",
                "status": job.status,
                "message": f"Job is currently {job.status}. Results will be available when status is 'completed'."
            }), 202  # Accepted but not ready
        
        # Get results from database
        results = db_manager.get_batch_results(job_id)
        if not results:
            return jsonify({"error": "Results not found"}), 404
        
        # Return complete results
        response = {
            "job_id": job_id,
            "status": job.status,
            "completed_at": job.updated_at.isoformat(),
            "results": results
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting batch results {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@polling_bp.route('/batch-results/<job_id>/download', methods=['GET'])
def download_batch_results(job_id: str):
    """
    Download batch job results as JSON file
    
    GET /api/v1/batch-results/{job_id}/download
    """
    try:
        # Verify signature
        if not verify_signature(request):
            return jsonify({"error": "Invalid signature"}), 401
        
        db_manager = get_db_manager()
        
        # Get job from database
        job = db_manager.get_batch_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Check if job is completed
        if job.status != 'completed':
            return jsonify({
                "error": "Job not completed",
                "status": job.status
            }), 202
        
        # Get results from database
        results = db_manager.get_batch_results(job_id)
        if not results:
            return jsonify({"error": "Results not found"}), 404
        
        # Create downloadable response
        from flask import Response
        import json
        
        response_data = {
            "job_id": job_id,
            "status": job.status,
            "completed_at": job.updated_at.isoformat(),
            "generated_at": job.created_at.isoformat(),
            "total_lots": job.total_lots,
            "processed_lots": job.processed_lots,
            "failed_lots": job.failed_lots,
            "languages": job.languages,
            "results": results
        }
        
        json_string = json.dumps(response_data, indent=2, ensure_ascii=False)
        
        response = Response(
            json_string,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=batch_results_{job_id}.json',
                'Content-Length': str(len(json_string.encode('utf-8')))
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading batch results {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@polling_bp.route('/batch-jobs', methods=['GET'])
def list_batch_jobs():
    """
    List batch jobs with filtering
    
    GET /api/v1/batch-jobs?status=pending&limit=10&offset=0
    """
    try:
        # Verify signature
        if not verify_signature(request):
            return jsonify({"error": "Invalid signature"}), 401
        
        # Get query parameters
        status_filter = request.args.get('status')
        limit = min(int(request.args.get('limit', 10)), 100)  # Max 100
        offset = int(request.args.get('offset', 0))
        
        db_manager = get_db_manager()
        
        # Get jobs from database (this would need to be implemented in DatabaseManager)
        jobs = db_manager.get_batch_jobs_list(
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        # Format response
        jobs_data = []
        for job in jobs:
            job_data = job.to_dict()
            job_data['progress'] = {
                "total_lots": job.total_lots,
                "processed_lots": job.processed_lots,
                "failed_lots": job.failed_lots,
                "completion_percentage": round((job.processed_lots / job.total_lots * 100) if job.total_lots > 0 else 0, 2)
            }
            jobs_data.append(job_data)
        
        response = {
            "jobs": jobs_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(jobs)  # This would need to be implemented as a separate count query
            }
        }
        
        return jsonify(response), 200
        
    except ValueError as e:
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error listing batch jobs: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@polling_bp.route('/batch-jobs/<job_id>/cancel', methods=['POST'])
def cancel_batch_job(job_id: str):
    """
    Cancel a pending or processing batch job
    
    POST /api/v1/batch-jobs/{job_id}/cancel
    """
    try:
        # Verify signature
        if not verify_signature(request):
            return jsonify({"error": "Invalid signature"}), 401
        
        db_manager = get_db_manager()
        
        # Get job from database
        job = db_manager.get_batch_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Check if job can be cancelled
        if job.status not in ['pending', 'processing', 'translating']:
            return jsonify({
                "error": "Job cannot be cancelled",
                "status": job.status,
                "message": f"Only pending, processing, or translating jobs can be cancelled. Current status: {job.status}"
            }), 400
        
        # Cancel the job
        success = db_manager.update_batch_job_status(job_id, 'cancelled', 'Job cancelled by user request')
        
        if not success:
            return jsonify({"error": "Failed to cancel job"}), 500
        
        # TODO: Also cancel OpenAI batch jobs if they exist
        # This would require implementing OpenAI batch cancellation
        
        return jsonify({
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job successfully cancelled"
        }), 200
        
    except Exception as e:
        logger.error(f"Error cancelling batch job {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500