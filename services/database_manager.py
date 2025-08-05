import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_
from database.models import BatchJob, BatchLot, BatchResult, WebhookDelivery

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_session):
        self.session = db_session
    
    def create_batch_job(self, job_data: Dict[str, Any]) -> str:
        """
        Create new batch job in database
        """
        try:
            batch_job = BatchJob(
                status=job_data.get('status', 'pending'),
                openai_batch_id=job_data.get('openai_batch_id'),
                openai_vision_batch_id=job_data.get('openai_vision_batch_id'),
                languages=job_data['languages'],
                webhook_url=job_data.get('webhook_url'),
                total_lots=len(job_data.get('lots', []))
            )
            
            # Set ID if provided
            if 'job_id' in job_data:
                batch_job.id = job_data['job_id']
            
            # Create batch lots
            for lot_data in job_data.get('lots', []):
                batch_lot = BatchLot(
                    batch_job_id=batch_job.id,
                    lot_id=lot_data['lot_id'],
                    additional_info=lot_data.get('additional_info'),
                    image_urls=lot_data.get('image_urls', []),
                    status=lot_data.get('status', 'pending')
                )
                batch_job.lots.append(batch_lot)
            
            self.session.add(batch_job)
            self.session.commit()
            
            logger.info(f"Created batch job {batch_job.id} with {len(batch_job.lots)} lots")
            return str(batch_job.id)
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error creating batch job: {str(e)}")
            raise e
    
    def get_batch_job(self, job_id: str):
        """
        Get batch job by ID
        """
        try:
            return self.session.query(BatchJob).filter(BatchJob.id == job_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting batch job {job_id}: {str(e)}")
            return None
    
    def update_batch_job_status(self, job_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        Update batch job status
        """
        try:
            batch_job = self.get_batch_job(job_id)
            if not batch_job:
                return False
            
            batch_job.status = status
            batch_job.updated_at = datetime.utcnow()
            if error_message:
                batch_job.error_message = error_message
            
            self.session.commit()
            logger.info(f"Updated batch job {job_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error updating batch job {job_id}: {str(e)}")
            return False
    
    def update_batch_job_openai_id(self, job_id: str, openai_batch_id: str, batch_type: str = 'vision') -> bool:
        """
        Update OpenAI batch ID for job
        """
        try:
            batch_job = self.get_batch_job(job_id)
            if not batch_job:
                return False
            
            if batch_type == 'vision':
                batch_job.openai_vision_batch_id = openai_batch_id
            elif batch_type == 'translation':
                batch_job.openai_translation_batch_id = openai_batch_id
            
            batch_job.updated_at = datetime.utcnow()
            self.session.commit()
            
            logger.info(f"Updated batch job {job_id} {batch_type} batch ID to {openai_batch_id}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error updating OpenAI batch ID: {str(e)}")
            return False
    
    def get_active_batch_jobs(self):
        """
        Get all active batch jobs that need monitoring
        Also includes failed jobs that might have completed OpenAI batches
        """
        try:
            return self.session.query(BatchJob).filter(
                BatchJob.status.in_(['pending', 'processing', 'failed'])
            ).filter(
                (BatchJob.openai_vision_batch_id.isnot(None)) | 
                (BatchJob.openai_translation_batch_id.isnot(None))
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting active batch jobs: {str(e)}")
            return []
    
    def save_batch_results(self, job_id: str, results_data: Dict[str, Any]) -> bool:
        """
        Save completed batch results
        """
        try:
            batch_job = self.get_batch_job(job_id)
            if not batch_job:
                return False
            
            # Create batch result record
            batch_result = BatchResult(
                batch_job_id=batch_job.id,
                result_data=results_data,
                file_size=len(str(results_data).encode('utf-8'))
            )
            
            # Update lot results
            lots_data = results_data.get('lots', [])
            for lot_result in lots_data:
                lot = self.session.query(BatchLot).filter(
                    and_(
                        BatchLot.batch_job_id == batch_job.id,
                        BatchLot.lot_id == lot_result['lot_id']
                    )
                ).first()
                
                if lot:
                    lot.status = 'completed'
                    lot.vision_result = lot_result.get('vision_result')
                    lot.translations = lot_result.get('translations', {})
                    lot.updated_at = datetime.utcnow()
            
            # Update job progress
            batch_job.processed_lots = len([l for l in lots_data if l.get('status') == 'completed'])
            batch_job.failed_lots = len([l for l in lots_data if l.get('status') == 'failed'])
            batch_job.status = 'completed'
            batch_job.updated_at = datetime.utcnow()
            
            self.session.add(batch_result)
            self.session.commit()
            
            logger.info(f"Saved results for batch job {job_id}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error saving batch results: {str(e)}")
            return False
    
    def get_batch_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch results by job ID
        """
        try:
            batch_result = self.session.query(BatchResult).filter(
                BatchResult.batch_job_id == job_id
            ).first()
            
            return batch_result.result_data if batch_result else None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting batch results {job_id}: {str(e)}")
            return None
    
    def get_batch_jobs_list(self, status_filter=None, limit=10, offset=0):
        """
        Get list of batch jobs with filtering
        """
        try:
            query = self.session.query(BatchJob)
            
            if status_filter:
                query = query.filter(BatchJob.status == status_filter)
            
            jobs = query.order_by(BatchJob.created_at.desc()).offset(offset).limit(limit).all()
            return jobs
        except SQLAlchemyError as e:
            logger.error(f"Database error getting batch jobs list: {str(e)}")
            return []
    

    def mark_webhook_delivered(self, webhook_id: str) -> bool:
        """
        Mark webhook as successfully delivered
        """
        try:
            webhook = self.session.query(WebhookDelivery).filter(
                WebhookDelivery.id == webhook_id
            ).first()
            
            if webhook:
                webhook.status = 'delivered'
                webhook.delivered_at = datetime.utcnow()
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error marking webhook delivered: {str(e)}")
            return False
    
    def mark_webhook_failed(self, webhook_id: str, error_message: str) -> bool:
        """
        Mark webhook as permanently failed
        """
        try:
            webhook = self.session.query(WebhookDelivery).filter(
                WebhookDelivery.id == webhook_id
            ).first()
            
            if webhook:
                webhook.status = 'failed'
                webhook.error_message = error_message
                webhook.last_attempt_at = datetime.utcnow()
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error marking webhook failed: {str(e)}")
            return False
    
    def update_webhook_attempt(self, webhook_id: str, attempt_count: int, next_attempt_at: datetime, error_message: str) -> bool:
        """
        Update webhook attempt information
        """
        try:
            webhook = self.session.query(WebhookDelivery).filter(
                WebhookDelivery.id == webhook_id
            ).first()
            
            if webhook:
                webhook.attempt_count = attempt_count
                webhook.next_attempt_at = next_attempt_at
                webhook.last_attempt_at = datetime.utcnow()
                webhook.error_message = error_message
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error updating webhook attempt: {str(e)}")
            return False
    
    def create_webhook_delivery(self, job_id: str, webhook_url: str, payload: Dict[str, Any], signature: str) -> str:
        """
        Create webhook delivery record
        """
        try:
            webhook_delivery = WebhookDelivery(
                batch_job_id=job_id,
                webhook_url=webhook_url,
                payload=payload,
                signature=signature,
                next_attempt_at=datetime.utcnow()
            )
            
            self.session.add(webhook_delivery)
            self.session.commit()
            
            logger.info(f"Created webhook delivery {webhook_delivery.id} for job {job_id}")
            return str(webhook_delivery.id)
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error creating webhook delivery: {str(e)}")
            raise e
    
    def get_pending_webhook_deliveries(self, ready_only: bool = False) -> List[WebhookDelivery]:
        """
        Get webhook deliveries that need to be attempted.

        Args:
            ready_only: If True, only return deliveries that are ready to be
                retried (next_attempt_at is in the past or not set). When False,
                return all pending or failed deliveries regardless of schedule.
        """
        try:
            query = self.session.query(WebhookDelivery).filter(
                and_(
                    WebhookDelivery.status.in_(['pending', 'failed']),
                    WebhookDelivery.attempt_count < 5
                )
            )

            if ready_only:
                query = query.filter(
                    or_(
                        WebhookDelivery.next_attempt_at.is_(None),
                        WebhookDelivery.next_attempt_at <= datetime.utcnow()
                    )
                )

            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting pending webhooks: {str(e)}")
            return []
    
    def update_webhook_delivery(self, delivery_id: str, status: str, response_status: int = None, 
                               response_body: str = None, error_message: str = None) -> bool:
        """
        Update webhook delivery status
        """
        try:
            delivery = self.session.query(WebhookDelivery).filter(
                WebhookDelivery.id == delivery_id
            ).first()
            
            if not delivery:
                return False
            
            delivery.status = status
            delivery.attempt_count += 1
            delivery.last_attempt_at = datetime.utcnow()
            
            if status == 'delivered':
                delivery.delivered_at = datetime.utcnow()
            elif status == 'failed' and delivery.attempt_count < 5:
                # Schedule next retry with exponential backoff
                delay_seconds = 2 ** delivery.attempt_count
                delivery.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
            
            if response_status:
                delivery.response_status = response_status
            if response_body:
                delivery.response_body = response_body[:1000]  # Limit size
            if error_message:
                delivery.error_message = error_message
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error updating webhook delivery: {str(e)}")
            return False
    
    def cleanup_old_jobs(self, days: int = 7) -> int:
        """
        Clean up old completed jobs
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_jobs = self.session.query(BatchJob).filter(
                and_(
                    BatchJob.status.in_(['completed', 'failed']),
                    BatchJob.updated_at < cutoff_date
                )
            ).all()
            
            count = 0
            for job in old_jobs:
                self.session.delete(job)
                count += 1
            
            self.session.commit()
            logger.info(f"Cleaned up {count} old batch jobs")
            return count
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error during cleanup: {str(e)}")
            return 0