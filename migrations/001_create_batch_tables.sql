-- Migration: Create batch processing tables
-- Version: 001
-- Date: 2025-08-05
-- Description: Create tables for persistent batch job tracking and results storage

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Batch jobs table
CREATE TABLE batch_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- OpenAI integration
    openai_batch_id VARCHAR(100),
    openai_vision_batch_id VARCHAR(100),
    openai_translation_batch_id VARCHAR(100),
    
    -- Configuration
    languages JSON NOT NULL,
    webhook_url VARCHAR(500),
    
    -- Progress tracking
    total_lots INTEGER NOT NULL DEFAULT 0,
    processed_lots INTEGER NOT NULL DEFAULT 0,
    failed_lots INTEGER NOT NULL DEFAULT 0,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0
);

-- Batch lots table
CREATE TABLE batch_lots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_job_id UUID NOT NULL REFERENCES batch_jobs(id) ON DELETE CASCADE,
    
    -- Lot information
    lot_id VARCHAR(100) NOT NULL,
    additional_info TEXT,
    image_urls JSON NOT NULL,
    
    -- Processing status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Results
    vision_result TEXT,
    translations JSON,
    
    -- Error handling
    error_message TEXT,
    missing_images JSON,
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- Batch results table
CREATE TABLE batch_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_job_id UUID NOT NULL REFERENCES batch_jobs(id) ON DELETE CASCADE,
    
    -- Complete result in API format
    result_data JSON NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    file_size INTEGER
);

-- Webhook deliveries table
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_job_id UUID NOT NULL REFERENCES batch_jobs(id) ON DELETE CASCADE,
    
    -- Delivery details
    webhook_url VARCHAR(500) NOT NULL,
    payload JSON NOT NULL,
    signature VARCHAR(64) NOT NULL,
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMP WITHOUT TIME ZONE,
    next_attempt_at TIMESTAMP WITHOUT TIME ZONE,
    
    -- Response details
    response_status INTEGER,
    response_body TEXT,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMP WITHOUT TIME ZONE
);

-- Indexes for performance
CREATE INDEX idx_batch_jobs_status ON batch_jobs(status);
CREATE INDEX idx_batch_jobs_openai_batch_id ON batch_jobs(openai_batch_id);
CREATE INDEX idx_batch_jobs_created_at ON batch_jobs(created_at);

CREATE INDEX idx_batch_lots_batch_job_id ON batch_lots(batch_job_id);
CREATE INDEX idx_batch_lots_lot_id ON batch_lots(lot_id);
CREATE INDEX idx_batch_lots_status ON batch_lots(status);

CREATE INDEX idx_batch_results_batch_job_id ON batch_results(batch_job_id);

CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX idx_webhook_deliveries_next_attempt ON webhook_deliveries(next_attempt_at);
CREATE INDEX idx_webhook_deliveries_batch_job_id ON webhook_deliveries(batch_job_id);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_batch_jobs_updated_at 
    BEFORE UPDATE ON batch_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_batch_lots_updated_at 
    BEFORE UPDATE ON batch_lots 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE batch_jobs IS 'Persistent storage for batch processing jobs';
COMMENT ON TABLE batch_lots IS 'Individual car lots within batch jobs';
COMMENT ON TABLE batch_results IS 'Final results for completed batch jobs';
COMMENT ON TABLE webhook_deliveries IS 'Webhook delivery tracking with retry logic';