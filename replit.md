# Generation Service

## Overview
The Generation Service is an AI-powered microservice designed to generate multilingual car damage assessments and descriptions from vehicle images. It utilizes OpenAI's Vision API to analyze car photos, detecting damage, wear, and condition issues. The service supports both synchronous processing for single requests and asynchronous batch processing for multiple lots, with integrated automatic translation capabilities. The business vision is to provide a comprehensive, automated solution for vehicle assessment, enhancing efficiency and accuracy in the automotive industry.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The Generation Service is built as a Flask-based REST API with a modular blueprint architecture. It uses a PostgreSQL database with SQLAlchemy ORM for persistent storage and incorporates a background worker service for job monitoring and webhook delivery. A polling API system allows for real-time job status checks and result retrieval.

Key architectural decisions include:
- **Processing Modes**: Supports synchronous (real-time for single lots with ≤20 images), batch (asynchronous for multiple lots via OpenAI Batch API, up to 50,000 lots), polling, and webhook modes. Automatic mode selection is based on request size.
- **Security**: Implements HMAC-SHA256 signature validation for request authentication, with constant-time comparison to prevent timing attacks. Includes request size and rate limiting.
- **Image Processing**: Features a multi-stage image validation pipeline (URL format, accessibility, content-type), with configurable size and timeout controls, and fallback mechanisms.
- **AI Integration**: Integrates with OpenAI's o4-mini model for vision analysis and GPT-4.1-mini for multilingual translations. Utilizes configurable system prompts for automotive damage assessment and includes robust retry mechanisms with exponential backoff.
- **Error Handling and Resilience**: Incorporates comprehensive retry logic, circuit breaker patterns for external service failures, and graceful degradation.
- **Database Architecture**: Employs a PostgreSQL database with a schema designed for tracking batch jobs, individual lots, vision/translation results, and webhook deliveries.
- **Webhook System**: Features an asynchronous webhook delivery system with configurable retry policies, exponential backoff, and signed payloads for security.

## External Dependencies
- **OpenAI Platform**:
    - Responses API (primary integration for o4-mini reasoning model)
    - Vision API (car image analysis and damage detection)
    - Translation API (multilingual description generation using GPT-4.1-mini)
    - Batch API (large-scale asynchronous processing)
- **Infrastructure Services**:
    - Requests library (for external API communication)
    - URL-based image validation and accessibility checking
    - HTTP callback system (for asynchronous result delivery)
- **Configuration Dependencies**:
    - Environment Variables (e.g., `OPENAI_API_KEY`, `SHARED_KEY`)
    - System Prompts (for AI behavior configuration)