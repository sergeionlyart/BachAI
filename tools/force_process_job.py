#!/usr/bin/env python3
"""
Force process a specific batch job manually
"""

import os
import sys
import logging
sys.path.insert(0, '/home/runner/workspace')
from app import app
from services.batch_monitor import BatchMonitor
from services.database_manager import DatabaseManager
from database.models import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_process_job(job_id):
    """Force process a specific job"""
    
    with app.app_context():
        try:
            # Initialize services
            db_manager = DatabaseManager(db.session)
            batch_monitor = BatchMonitor()
            
            # Get the job
            job = db_manager.get_batch_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            logger.info(f"Processing job {job_id} with status {job.status}")
            logger.info(f"OpenAI batch: {job.openai_batch_id}")
            
            # Force check this specific job
            if job.openai_batch_id and job.status in ['processing', 'failed']:
                logger.info(f"Checking OpenAI batch {job.openai_batch_id}")
                batch_monitor._check_vision_batch(job)
                logger.info(f"Vision batch check completed for {job_id}")
                return True
            elif job.openai_translation_batch_id and job.status in ['translating', 'failed']:
                logger.info(f"Checking translation batch {job.openai_translation_batch_id}")
                batch_monitor._check_translation_batch(job)
                logger.info(f"Translation batch check completed for {job_id}")
                return True
            else:
                logger.warning(f"Job {job_id} not in processable state: status={job.status}, batch_id={job.openai_batch_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python force_process_job.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    success = force_process_job(job_id)
    sys.exit(0 if success else 1)