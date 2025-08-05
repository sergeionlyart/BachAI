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
- **OpenAI Chat Completions API** integration using gpt-4o model for vision analysis
- **Vision analysis** with configurable system prompts for automotive damage assessment
- **Translation capabilities** using gpt-4o-mini for multilingual output
- **Retry mechanisms** with exponential backoff for API reliability
- **Timeout configuration** with 60-second limits to prevent WORKER TIMEOUT errors
- **Parallel translation processing** in sync mode to improve performance

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
- **Chat Completions API**: Primary integration for gpt-4o vision model and gpt-4o-mini translation model
- **Vision API**: Car image analysis and damage detection using gpt-4o
- **Translation API**: Multilingual description generation using gpt-4o-mini
- **Batch API**: Large-scale asynchronous processing capabilities using chat completions endpoint

### Infrastructure Services
- **HTTP Client Libraries**: Requests library for external API communication
- **Image Processing**: URL-based image validation and accessibility checking
- **Webhook Infrastructure**: HTTP callback system for asynchronous result delivery

### Configuration Dependencies
- **Environment Variables**: OPENAI_API_KEY, SHARED_KEY, processing limits, timeout configurations
- **System Prompts**: Configurable AI behavior for automotive damage assessment
- **Rate Limiting**: Configurable batch limits and processing thresholds