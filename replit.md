# Generation Service

## Overview

The Generation Service is an AI-powered microservice that generates multilingual car damage assessments and descriptions from vehicle images. It leverages OpenAI's Vision API (o4-mini model) to analyze car photos and automatically detect damage, wear, and condition issues. The service supports both synchronous processing for single lots and asynchronous batch processing for multiple lots, with automatic translation capabilities to generate descriptions in multiple languages.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Framework
- **Flask-based REST API** with modular blueprint architecture
- **ProxyFix middleware** for proper header handling in production environments
- **Centralized configuration management** through environment variables
- **Structured logging** with configurable levels and handlers

### Processing Modes
- **Synchronous Mode**: Real-time processing for single lot requests (≤20 images, ≤300s response time)
- **Batch Mode**: Asynchronous processing for multiple lots using OpenAI Batch API (≤50,000 lots, ≤24h processing time)
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

### Webhook System
- **Asynchronous result delivery** via HTTP webhooks
- **Retry mechanisms** with exponential backoff for webhook delivery
- **Signed webhook payloads** for verification and security
- **Job status tracking** for batch processing monitoring

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

### August 5, 2025 - Critical OpenAI API Integration Fixes ✅
- **Complete API Migration**: Successfully migrated from outdated chat.completions to modern OpenAI Responses API exclusively
- **Model Updates**: Now using o4-mini for vision analysis and gpt-4.1-mini for translations via Responses API only
- **Timeout Resolution**: Fixed WORKER TIMEOUT errors by optimizing sync route with translation limits (max 2 languages) and 45s timeout
- **Batch Processing Optimization**: Removed unused translation_requests code, fixed file upload with proper filename parameter
- **Error Handling**: Resolved all LSP diagnostics and improved exception handling with proper timeout tracking
- **Performance Improvements**: Added request timeouts (60s), sequential translation limits, and fallback mechanisms
- **Type Safety**: Fixed multimodal content format issues for stable Responses API integration

### Key Technical Improvements
- **OpenAI Client**: Rewritten to use only Responses API with proper timeout handling and error recovery
- **Batch Processor**: Simplified request format, removed placeholder translation logic, fixed file upload
- **Sync Route**: Added translation limits and timeout protection to prevent worker timeouts
- **Error Handling**: Comprehensive exception handling with duration tracking and graceful fallbacks