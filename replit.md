# Generation Service

## Overview

The Generation Service is an AI-powered microservice that generates multilingual car damage assessments and descriptions from vehicle images. It leverages OpenAI's Vision API (o4-mini model) to analyze car photos and automatically detect damage, wear, and condition issues. The service supports both synchronous processing for single lots and asynchronous batch processing for multiple lots, with automatic translation capabilities to generate descriptions in multiple languages.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Framework
- **Flask-based REST API** with modular blueprint architecture
- **PostgreSQL Database Integration** with SQLAlchemy ORM for persistent storage
- **Background Worker Service** for automated job monitoring and webhook delivery
- **Polling API System** for real-time job status checking and result retrieval
- **ProxyFix middleware** for proper header handling in production environments
- **Centralized configuration management** through environment variables
- **Structured logging** with configurable levels and handlers

### Processing Modes
- **Synchronous Mode**: Real-time processing for single lot requests (≤20 images, ≤300s response time)
- **Batch Mode**: Asynchronous processing for multiple lots using OpenAI Batch API (≤50,000 lots, ≤24h processing time)
- **Polling Mode**: REST API endpoints for job status checking and result retrieval
- **Webhook Mode**: Automatic result delivery via HTTP callbacks with retry mechanisms
- **Automatic mode selection** based on request size and complexity

### Security Architecture
- **HMAC-SHA256 signature validation** for request authentication using shared secrets
- **Constant-time signature comparison** to prevent timing attacks
- **Webhook signature validation** for secure callback communication
- **Request size and rate limiting** to prevent abuse

### Image Processing Pipeline
- **Multi-stage image validation**: URL format checking, accessibility verification, content-type validation
- **Size and timeout controls**: Configurable limits for image downloads and processing
- **Fallback mechanisms**: HEAD requests with GET fallbacks for robust image validation
- **Threshold-based processing**: Minimum viable image count requirements

### AI Integration
- **OpenAI Responses API** integration using o4-mini reasoning model with medium effort setting
- **Vision analysis** with configurable system prompts for automotive damage assessment
- **Translation capabilities** using GPT-4.1-mini for multilingual output
- **Retry mechanisms** with exponential backoff for API reliability

### Error Handling and Resilience
- **Comprehensive retry logic** with configurable attempts and backoff strategies
- **Circuit breaker patterns** for external service failures
- **Graceful degradation** when services are unavailable
- **Detailed error categorization** for retryable vs non-retryable failures

### Database Architecture
- **PostgreSQL-based persistence** with comprehensive schema design
- **BatchJob table**: Main job tracking with status, OpenAI batch IDs, and configuration
- **BatchLot table**: Individual lot processing with image URLs, results, and translations
- **BatchResult table**: Structured storage of vision and translation results
- **WebhookDelivery table**: Webhook delivery tracking with retry mechanisms and status monitoring

### Webhook System
- **Background worker service** for automated webhook delivery
- **Asynchronous result delivery** via HTTP webhooks with comprehensive retry policies
- **Exponential backoff strategy** with configurable retry limits and timeouts
- **Signed webhook payloads** for verification and security using HMAC-SHA256
- **Delivery status tracking** with detailed error logging and failure analysis
- **Job status monitoring** for batch processing lifecycle management

## External Dependencies

### OpenAI Platform
- **Responses API**: Primary integration for o4-mini reasoning model
- **Vision API**: Car image analysis and damage detection
- **Translation API**: Multilingual description generation using GPT-4.1-mini
- **Batch API**: Large-scale asynchronous processing capabilities

### Infrastructure Services
- **HTTP Client Libraries**: Requests library for external API communication
- **Image Processing**: URL-based image validation and accessibility checking
- **Webhook Infrastructure**: HTTP callback system for asynchronous result delivery

### Configuration Dependencies
- **Environment Variables**: OPENAI_API_KEY, SHARED_KEY, processing limits, timeout configurations
- **System Prompts**: Configurable AI behavior for automotive damage assessment
- **Rate Limiting**: Configurable batch limits and processing thresholds

## Recent Updates

### August 6, 2025 - Complete Webhook Documentation & Testing ✅
- **Technical Documentation Created**: Comprehensive WEBHOOK_API_USAGE.md with detailed API integration guide
- **User-Friendly Guide**: Interactive web interface at `/webhook-guide` with visual examples and code snippets
- **Webhook Testing Completed**: Successfully tested webhook delivery system with local test endpoints
- **Monitoring APIs Operational**: Health checks, metrics tracking, and failure monitoring all functioning
- **Multiple Language Examples**: Python Flask, Node.js Express integration examples with authentication
- **Production Security**: HMAC-SHA256 signature validation, SSRF protection, retry mechanisms all verified
- **Complete Documentation Suite**: WEBHOOK_API_USAGE.md, CLIENT_WEBHOOK_GUIDE.md, interactive web guide at /webhook-guide

### August 6, 2025 - Complete Batch Results Recovery & System Fixes ✅
- **CRITICAL FIX**: Resolved vision results not saving to database - all 20 lots of job 365a09ce-5416-49b5-8471-d6aad042761c successfully recovered with full OpenAI-generated descriptions (2000+ characters each)
- **LSP Code Fixes**: Fixed 17 LSP diagnostic errors in batch_monitor.py preventing proper SQLAlchemy model updates
- **OpenAI Responses API Parser**: Fixed parsing of Responses API format - correctly extracts text from `output[].content[].text` structure instead of treating output as string
- **Recovery Tools**: Created `tools/recover_batch_results.py` script for manual result recovery from OpenAI batch API
- **Database Updates**: Proper setattr() usage for SQLAlchemy Column assignments, fixed PostgreSQL type compatibility
- **Production Validation**: Confirmed full end-to-end processing - vision analysis results properly saved and retrievable via API
- **Client Results Available**: Job 365a09ce-5416-49b5-8471-d6aad042761c now returns complete automotive damage assessments instead of placeholder text

### August 6, 2025 - Complete Authentication System Setup & Polling API Resolution ✅
- **HMAC Authentication System**: Successfully configured complete HMAC-SHA256 signature validation with SHARED_KEY environment variable
- **Client Authentication Tools**: Created comprehensive client authentication guides, signature generators, and working examples
- **Verified Authentication**: Confirmed working curl requests with proper HMAC signatures for job status polling
- **Multiple API Options**: Both authenticated endpoints (`/api/v1/batch-status/{job_id}`) and non-authenticated (`/api/v1/jobs/{job_id}/status`) available
- **Complete Documentation**: Full client integration guides with Python examples and signature generation algorithms
- **Job Status Resolution**: Job 365a09ce-5416-49b5-8471-d6aad042761c confirmed completed with proper status endpoints
- **Production Ready**: SHARED_KEY properly configured, signature validation working, client tools provided

### August 5, 2025 - Enhanced Synchronous Translation System ✅
- **Flexible Translation Processing**: Added configurable threshold for warning about large language lists during synchronous requests
- **Improved Client Experience**: Revised synchronous translation handling to process all requested languages with English fallbacks when exceeding time limits
- **Enhanced API Responses**: Added optional "warnings" and "pending_languages" fields to inform clients about delays and fallback translations
- **Updated Documentation**: API documentation now describes support for arbitrary language counts and new response fields
- **Backward Compatibility**: All existing clients continue to work without changes while gaining access to enhanced features

### August 5, 2025 - Complete API Documentation v2.0 & Web Interface Updates ✅
- **API Documentation Rewrite**: Completely rewritten API_Documentation.md with comprehensive v2.0 specifications
- **Production-Ready Documentation**: Full coverage of PostgreSQL integration, Background Worker, and Polling API
- **Enhanced Web Interface**: Updated homepage and API documentation templates to showcase all new capabilities
- **Complete Code Examples**: Added Python and JavaScript/Node.js client SDKs with full integration examples
- **Production Deployment Guide**: Docker, nginx, monitoring, and troubleshooting sections for enterprise deployment
- **Comprehensive Polling API**: Full documentation of all job tracking, result retrieval, and management endpoints

### August 5, 2025 - Complete PostgreSQL Integration & Background Worker System ✅
- **PostgreSQL Database Architecture**: Successfully migrated from in-memory storage to full PostgreSQL-based persistence system
- **Background Worker Service**: Implemented complete background monitoring and webhook delivery system with automatic job tracking
- **Polling API System**: Added comprehensive REST API for job status checking and results retrieval
- **Webhook Delivery System**: Implemented robust webhook delivery with retry mechanisms, exponential backoff, and failure tracking
- **Database Models**: Created complete schema with BatchJob, BatchLot, BatchResult, and WebhookDelivery tables for full persistence
- **Batch Monitoring**: Added automatic OpenAI batch status monitoring with result downloading and processing
- **Production Architecture**: Integrated all components into main Flask application with proper service startup and lifecycle management

### August 5, 2025 - Complete Vision Results Processing System Fixed ✅
- **CRITICAL FIX #1**: Resolved `'list' object has no attribute 'get'` error in vision results processing pipeline
- **CRITICAL FIX #2**: Fixed custom_id parsing to support both `vision:lot_id` and `vision:job_id:lot_id` formats from OpenAI batches
- **CRITICAL FIX #3**: Fixed OpenAI Responses API response parsing - correctly extracts text from `{'format': {'type': 'text'}}` structure
- **CRITICAL FIX #4**: Fixed translation batch creation to read vision results from database instead of parsing raw responses
- **Failed Job Recovery**: Enhanced background monitoring to automatically detect and restore failed jobs when OpenAI batch completes successfully
- **Vision Processing Pipeline**: Complete end-to-end vision result processing with proper PostgreSQL persistence (20/20 lots processed)
- **Translation Pipeline**: Fully operational translation batch creation system with proper error handling and status management
- **OpenAI Integration**: Confirmed compatibility with OpenAI Responses API format and batch processing workflow
- **Database Consistency**: Resolved all data type mismatches between dict objects and PostgreSQL TEXT fields
- **Status Management**: Fixed job status transitions from failed → processing → translating with proper error message clearing
- **Production Ready**: Complete monitoring system successfully processes real client requests end-to-end with full error recovery

### August 5, 2025 - Critical OpenAI API Integration & Performance Fixes ✅
- **Complete API Migration**: Successfully migrated from outdated chat.completions to modern OpenAI Responses API exclusively
- **Model Updates**: Now using o4-mini for vision analysis and gpt-4.1-mini for translations via Responses API only
- **WORKER TIMEOUT RESOLUTION**: **CRITICAL FIX** - Completely resolved WORKER TIMEOUT errors by optimizing batch creation (3 lots: 1.41s, 20 lots: 0.99s)
- **Batch Processing Optimization**: Removed expensive image validation from batch creation, added timeout protection (15s limit), optimized file creation
- **Sync Route Optimization**: Added translation limits (max 2 languages) and 45s timeout protection
- **Error Handling**: Resolved all LSP diagnostics, improved exception handling with proper timeout tracking and graceful fallbacks
- **Performance Improvements**: Added request timeouts (60s), sequential translation limits, and comprehensive fallback mechanisms
- **Type Safety**: Fixed multimodal content format issues for stable Responses API integration

### Key Technical Improvements
- **PostgreSQL Integration**: Complete database-based persistence system replacing in-memory storage for production reliability
- **Background Services**: Automated job monitoring, result processing, and webhook delivery with configurable retry policies
- **API Endpoints**: Full REST API for job creation, status polling, and result retrieval with proper error handling
- **OpenAI Client**: Rewritten to use only Responses API with proper timeout handling, start_time initialization fixes
- **Batch Processor**: **MAJOR OPTIMIZATION** - Fast batch creation without HTTP image validation, 15s timeout protection, efficient batch submission
- **Sync Route**: Translation limits and timeout protection to prevent worker timeouts
- **Error Handling**: Comprehensive exception handling with duration tracking, creation time monitoring, graceful degradation