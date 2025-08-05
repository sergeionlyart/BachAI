import uuid
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

# Initialize db - will be set by app
db = SQLAlchemy()

class BatchJob(db.Model):
    __tablename__ = 'batch_jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # OpenAI integration
    openai_batch_id = Column(String(100), nullable=True, index=True)
    openai_vision_batch_id = Column(String(100), nullable=True)
    openai_translation_batch_id = Column(String(100), nullable=True)
    
    # Configuration
    languages = Column(JSON, nullable=False)
    webhook_url = Column(String(500), nullable=True)
    
    # Progress tracking
    total_lots = Column(Integer, nullable=False, default=0)
    processed_lots = Column(Integer, nullable=False, default=0)
    failed_lots = Column(Integer, nullable=False, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Relationships
    lots = relationship("BatchLot", back_populates="batch_job", cascade="all, delete-orphan")
    results = relationship("BatchResult", back_populates="batch_job", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': str(self.id),
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'languages': self.languages,
            'webhook_url': self.webhook_url,
            'total_lots': self.total_lots,
            'processed_lots': self.processed_lots,
            'failed_lots': self.failed_lots,
            'error_message': self.error_message,
            'openai_batch_id': self.openai_batch_id
        }

class BatchLot(db.Model):
    __tablename__ = 'batch_lots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_job_id = Column(UUID(as_uuid=True), ForeignKey('batch_jobs.id'), nullable=False)
    
    # Lot information
    lot_id = Column(String(100), nullable=False, index=True)
    additional_info = Column(Text, nullable=True)
    image_urls = Column(JSON, nullable=False)
    
    # Processing status
    status = Column(String(20), nullable=False, default='pending')
    
    # Results
    vision_result = Column(Text, nullable=True)
    translations = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    missing_images = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    batch_job = relationship("BatchJob", back_populates="lots")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'lot_id': self.lot_id,
            'status': self.status,
            'additional_info': self.additional_info,
            'image_urls': self.image_urls,
            'vision_result': self.vision_result,
            'translations': self.translations,
            'error_message': self.error_message,
            'missing_images': self.missing_images,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class BatchResult(db.Model):
    __tablename__ = 'batch_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_job_id = Column(UUID(as_uuid=True), ForeignKey('batch_jobs.id'), nullable=False, index=True)
    
    # Complete result in API format
    result_data = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # Relationships
    batch_job = relationship("BatchJob", back_populates="results")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'batch_job_id': str(self.batch_job_id),
            'result_data': self.result_data,
            'created_at': self.created_at.isoformat(),
            'file_size': self.file_size
        }

class WebhookDelivery(db.Model):
    __tablename__ = 'webhook_deliveries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_job_id = Column(UUID(as_uuid=True), ForeignKey('batch_jobs.id'), nullable=False)
    
    # Delivery details
    webhook_url = Column(String(500), nullable=False)
    payload = Column(JSON, nullable=False)
    signature = Column(String(64), nullable=False)
    
    # Status tracking
    status = Column(String(20), nullable=False, default='pending')
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    next_attempt_at = Column(DateTime, nullable=True)
    
    # Response details
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'batch_job_id': str(self.batch_job_id),
            'webhook_url': self.webhook_url,
            'status': self.status,
            'attempt_count': self.attempt_count,
            'last_attempt_at': self.last_attempt_at.isoformat() if self.last_attempt_at is not None else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at is not None else None,
            'error_message': self.error_message
        }