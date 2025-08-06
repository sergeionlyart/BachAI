#!/usr/bin/env python3
"""
Script to recover lost batch connections by scanning OpenAI batches and matching metadata
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

# Database and OpenAI setup
DATABASE_URL = os.environ.get('DATABASE_URL')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

def recover_lost_batch_connections():
    """Find and recover lost batch connections"""
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # Find jobs without OpenAI batch IDs but with processing/translating status
        cur.execute("""
            SELECT id, status, created_at, updated_at
            FROM batch_jobs 
            WHERE openai_batch_id IS NULL 
              AND status IN ('processing', 'translating', 'failed')
              AND created_at >= '2025-08-05'  -- Focus on recent jobs
            ORDER BY created_at DESC
        """)
        orphaned_jobs = cur.fetchall()
        
        logger.info(f"Found {len(orphaned_jobs)} orphaned jobs")
        
        if not orphaned_jobs:
            logger.info("No orphaned jobs found!")
            return
        
        # Get list of recent OpenAI batches
        try:
            batches_response = client.batches.list(limit=20)  # Recent batches
            openai_batches = batches_response.data
            logger.info(f"Found {len(openai_batches)} recent OpenAI batches")
        except Exception as e:
            logger.error(f"Failed to list OpenAI batches: {e}")
            return
        
        # Match batches by metadata and timing
        recoveries = []
        
        for job in orphaned_jobs:
            job_id = job['id']
            job_created = job['created_at']
            
            logger.info(f"Searching match for job {job_id} (created: {job_created})")
            
            # Find matching OpenAI batch by metadata
            best_match = None
            
            for batch in openai_batches:
                # Check if metadata contains this job ID
                metadata = batch.metadata or {}
                description = metadata.get('description', '')
                
                if job_id in description:
                    logger.info(f"  FOUND MATCH: {batch.id} - {description}")
                    best_match = batch
                    break
                    
                # Also check by timing (within 10 minutes of job creation)
                batch_created = datetime.fromtimestamp(batch.created_at)
                if abs((job_created.replace(tzinfo=None) - batch_created).total_seconds()) < 600:  # 10 minutes
                    if batch.status in ['completed', 'in_progress']:
                        logger.info(f"  POSSIBLE MATCH by timing: {batch.id} - {batch_created}")
                        if not best_match:  # Only use timing match if no metadata match
                            best_match = batch
            
            if best_match:
                recoveries.append({
                    'job_id': job_id,
                    'batch_id': best_match.id,
                    'batch_status': best_match.status,
                    'match_type': 'metadata' if job_id in (best_match.metadata or {}).get('description', '') else 'timing'
                })
        
        logger.info(f"Found {len(recoveries)} potential recoveries")
        
        # Apply recoveries
        for recovery in recoveries:
            job_id = recovery['job_id']
            batch_id = recovery['batch_id'] 
            batch_status = recovery['batch_status']
            match_type = recovery['match_type']
            
            logger.info(f"Recovering {job_id} -> {batch_id} ({batch_status}) via {match_type}")
            
            # Update database
            cur.execute("""
                UPDATE batch_jobs 
                SET 
                    openai_batch_id = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (batch_id, job_id))
            
            # If batch is completed, background worker should pick it up automatically
            
        conn.commit()
        logger.info(f"Successfully recovered {len(recoveries)} batch connections")
        
        # Verify results
        cur.execute("""
            SELECT id, openai_batch_id, status
            FROM batch_jobs 
            WHERE id = ANY(%s)
        """, ([r['job_id'] for r in recoveries],))
        
        results = cur.fetchall()
        print("\n=== Recovery Results ===")
        for result in results:
            print(f"Job {result['id']}: batch_id={result['openai_batch_id']}, status={result['status']}")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Recovery failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    recover_lost_batch_connections()