#!/usr/bin/env python3
"""
Standalone script to fix batch results.
"""

import os
import json
import logging
from datetime import datetime
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

def fix_batch_results(job_id: str):
    """Fix batch results for a specific job"""
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # Get job from database
        cur.execute("SELECT * FROM batch_jobs WHERE id = %s", (job_id,))
        job = cur.fetchone()
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        openai_batch_id = job['openai_batch_id']
        logger.info(f"Processing job {job_id} with OpenAI batch ID: {openai_batch_id}")
        
        # Get batch status from OpenAI
        batch = client.batches.retrieve(openai_batch_id)
        
        if batch.status != 'completed':
            logger.error(f"Batch is not completed. Status: {batch.status}")
            return False
        
        if not batch.output_file_id:
            logger.error("No output file ID in batch status")
            return False
        
        # Download results from OpenAI
        logger.info(f"Downloading results from file {batch.output_file_id}")
        file_response = client.files.content(batch.output_file_id)
        results_content = file_response.read().decode('utf-8')
        
        # Parse results
        results = []
        for line in results_content.strip().split('\n'):
            if line.strip():
                results.append(json.loads(line))
        
        logger.info(f"Parsed {len(results)} results from OpenAI")
        
        # Get all lots for this job
        cur.execute("SELECT * FROM batch_lots WHERE batch_job_id = %s", (job_id,))
        lots = cur.fetchall()
        
        lot_map = {lot['lot_id']: lot for lot in lots}
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
                current_result = lot['vision_result']
                if current_result and isinstance(current_result, str):
                    # Check if it contains the incorrect format structure
                    if "'format'" in current_result or "{'type': 'text'}" in current_result:
                        logger.info(f"Fixing lot {lot_id}: replacing format structure with actual text ({len(vision_text)} chars)")
                        cur.execute(
                            "UPDATE batch_lots SET vision_result = %s, updated_at = %s WHERE id = %s",
                            (vision_text, datetime.utcnow(), lot['id'])
                        )
                        fixed_count += 1
                    else:
                        logger.info(f"Lot {lot_id} already has valid text, skipping")
                else:
                    logger.info(f"Setting vision result for lot {lot_id}: {len(vision_text)} chars")
                    cur.execute(
                        "UPDATE batch_lots SET vision_result = %s, status = 'completed', updated_at = %s WHERE id = %s",
                        (vision_text, datetime.utcnow(), lot['id'])
                    )
                    fixed_count += 1
            else:
                logger.error(f"Could not extract text for lot {lot_id}")
        
        # Commit changes
        conn.commit()
        logger.info(f"Fixed {fixed_count} lots for job {job_id}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error fixing batch results: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cur.close()
        conn.close()

def main():
    """Main function to fix all affected jobs"""
    
    # Job ID from the user's request
    job_id = "64734dab-3961-4014-8b2b-196302b5d047"
    
    logger.info(f"Fixing batch results for job {job_id}")
    
    if fix_batch_results(job_id):
        logger.info("Successfully fixed batch results!")
        
        # Verify the fix
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT lot_id, vision_result FROM batch_lots WHERE batch_job_id = %s LIMIT 3",
            (job_id,)
        )
        lots = cur.fetchall()
        
        print("\n=== Verification ===")
        for lot in lots:
            result = lot['vision_result']
            if result:
                print(f"\nLot {lot['lot_id']}:")
                print(f"  Result length: {len(result)} chars")
                print(f"  Preview: {result[:150]}...")
            else:
                print(f"\nLot {lot['lot_id']}: No result")
        
        cur.close()
        conn.close()
    else:
        logger.error("Failed to fix batch results")

if __name__ == "__main__":
    main()
