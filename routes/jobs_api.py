"""
Simple polling API endpoints for job status and results
Compatible with client polling scripts
"""
import logging
from flask import Blueprint, jsonify
from services.database_manager import DatabaseManager
from database.models import db, BatchJob, BatchLot

logger = logging.getLogger(__name__)

# Create blueprint for simple job endpoints
jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/v1/jobs')

def get_db_manager():
    """Get database manager instance"""
    return DatabaseManager(db.session)

@jobs_bp.route('/<job_id>/status', methods=['GET'])
def get_job_status(job_id: str):
    """
    Get simple job status for polling clients
    
    GET /api/v1/jobs/{job_id}/status
    
    Returns simplified status without authentication
    """
    try:
        db_manager = get_db_manager()
        
        # Get job from database
        job = db_manager.get_batch_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Return simplified job status
        response = {
            "job_id": job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }
        
        # Add error if exists
        if job.error_message:
            response["error"] = job.error_message
            
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@jobs_bp.route('/<job_id>', methods=['GET'])
def get_job_results(job_id: str):
    """
    Get job results for polling clients
    
    GET /api/v1/jobs/{job_id}
    
    Returns full results when job is completed
    """
    try:
        db_manager = get_db_manager()
        
        # Get job from database
        job = db_manager.get_batch_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # If job not completed, return status only
        if job.status != 'completed':
            return jsonify({
                "job_id": job_id,
                "status": job.status,
                "message": f"Job is currently {job.status}",
                "error": job.error_message
            }), 200
        
        # Get all lots for completed job
        lots = db.session.query(BatchLot).filter(
            BatchLot.batch_job_id == job.id
        ).all()
        
        # Build full results
        results = []
        for lot in lots:
            lot_result = {
                "lot_id": lot.lot_id,
                "status": lot.status,
                "vision_result": lot.vision_result,
                "translations": lot.translations or {},
                "error_message": lot.error_message,
                "missing_images": lot.missing_images or []
            }
            results.append(lot_result)
        
        response = {
            "job_id": job_id,
            "status": job.status,
            "results": results,
            "total_lots": job.total_lots,
            "processed_lots": job.processed_lots,
            "failed_lots": job.failed_lots
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting job results {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500