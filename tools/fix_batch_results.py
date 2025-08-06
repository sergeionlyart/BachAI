#!/usr/bin/env python3
"""
Fix batch results that were incorrectly saved with format structure instead of actual text.
This script re-downloads and re-processes OpenAI batch results.
"""

import os
import sys
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.openai_client import OpenAIClient
from models.batch_models import BatchJob, BatchLot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_batch_results(job_id: str):
    """Fix batch results for a specific job"""
    
    # Initialize database
    database_url = os.environ.get('DATABASE_URL')
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Initialize OpenAI client
    openai_client = OpenAIClient()
    
    try:
        # Get job from database
        job = session.query(BatchJob).filter(
            BatchJob.id == job_id
        ).first()
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        logger.info(f"Processing job {job_id} with OpenAI batch ID: {job.openai_batch_id}")
        
        # Get batch status from OpenAI
        batch_status = openai_client.get_batch_status(job.openai_batch_id)
        
        if batch_status['status'] != 'completed':
            logger.error(f"Batch is not completed. Status: {batch_status['status']}")
            return False
        
        if not batch_status.get('output_file_id'):
            logger.error("No output file ID in batch status")
            return False
        
        # Download results from OpenAI
        logger.info(f"Downloading results from file {batch_status['output_file_id']}")
        results_content = openai_client.download_batch_results(batch_status['output_file_id'])
        
        # Parse results
        results = []
        for line in results_content.strip().split('\n'):
            if line.strip():
                results.append(json.loads(line))
        
        logger.info(f"Parsed {len(results)} results from OpenAI")
        
        # Get all lots for this job
        lots = session.query(BatchLot).filter(
            BatchLot.batch_job_id == job.id
        ).all()
        
        lot_map = {lot.lot_id: lot for lot in lots}
        logger.info(f"Found {len(lots)} lots in database")
        
        # Process each result
        fixed_count = 0
        for result in results:
            custom_id = result.get('custom_id', '')
            
            if not custom_id.startswith('vision:'):
                continue
            
            # Parse lot_id from custom_id
            parts = custom_id.split(':')
            if len(parts) == 2:
                lot_id = parts[1]
            elif len(parts) >= 3:
                lot_id = parts[2]
            else:
                logger.warning(f"Invalid custom_id format: {custom_id}")
                continue
            
            if lot_id not in lot_map:
                logger.warning(f"Lot {lot_id} not found in database")
                continue
            
            lot = lot_map[lot_id]
            
            # Extract the actual text from the correct location
            response_data = result.get('response', {})
            body = response_data.get('body', {})
            
            # The actual text is in: body.output[0].content[0].text
            vision_text = ''
            output = body.get('output', [])
            
            if output and isinstance(output, list) and len(output) > 0:
                first_output = output[0]
                if isinstance(first_output, dict):
                    content = first_output.get('content', [])
                    if content and isinstance(content, list) and len(content) > 0:
                        first_content = content[0]
                        if isinstance(first_content, dict):
                            vision_text = first_content.get('text', '')
            
            if vision_text:
                # Check if this lot needs fixing
                current_result = lot.vision_result
                if current_result and isinstance(current_result, str):
                    # Check if it contains the incorrect format structure
                    if "'format'" in current_result or "{'type': 'text'}" in current_result:
                        logger.info(f"Fixing lot {lot_id}: replacing format structure with actual text ({len(vision_text)} chars)")
                        lot.vision_result = vision_text
                        lot.updated_at = datetime.utcnow()
                        fixed_count += 1
                    else:
                        logger.info(f"Lot {lot_id} already has valid text, skipping")
                else:
                    logger.info(f"Setting vision result for lot {lot_id}: {len(vision_text)} chars")
                    lot.vision_result = vision_text
                    lot.status = 'completed' if lot.status != 'failed' else lot.status
                    lot.updated_at = datetime.utcnow()
                    fixed_count += 1
            else:
                logger.error(f"Could not extract text for lot {lot_id}")
        
        # Commit changes
        session.commit()
        logger.info(f"Fixed {fixed_count} lots for job {job_id}")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error fixing batch results: {str(e)}")
        return False
    finally:
        session.close()

def main():
    """Main function to fix all affected jobs"""
    
    # Job ID from the user's request
    job_id = "64734dab-3961-4014-8b2b-196302b5d047"
    
    logger.info(f"Fixing batch results for job {job_id}")
    
    if fix_batch_results(job_id):
        logger.info("Successfully fixed batch results!")
        
        # Verify the fix
        database_url = os.environ.get('DATABASE_URL')
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        lots = session.query(BatchLot).filter(
            BatchLot.batch_job_id == job_id
        ).limit(3).all()
        
        print("\n=== Verification ===")
        for lot in lots:
            result = lot.vision_result
            if result:
                print(f"\nLot {lot.lot_id}:")
                print(f"  Result length: {len(result)} chars")
                print(f"  Preview: {result[:150]}...")
            else:
                print(f"\nLot {lot.lot_id}: No result")
        
        session.close()
    else:
        logger.error("Failed to fix batch results")

if __name__ == "__main__":
    main()