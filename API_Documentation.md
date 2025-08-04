# Generation Service API Documentation

## Обзор

Generation Service API предоставляет ИИ-анализ повреждений автомобилей и генерацию многоязычных описаний с использованием OpenAI Vision и Translation моделей.

### Ключевые возможности

- Vision анализ с использованием OpenAI o4-mini модели
- Перевод на несколько языков с использованием GPT-4.1-mini  
- Синхронная обработка для одного автомобиля (≤300 сек)
- Пакетная обработка до 50,000 автомобилей (≤24 часа)
- Webhook уведомления для асинхронных результатов
- HMAC-SHA256 валидация подписи

### Режимы обработки

| Режим обработки | Условие запуска | Макс. изображений/машина | Время ответа |
|----------------|-----------------|-------------------------|--------------|
| Синхронный     | 1 машина в запросе | ≤ 20 | ≤ 300 секунд |
| Пакетный       | 2+ машины в запросе | Без ограничений | ≤ 24 часа |

## Аутентификация

Все запросы должны включать валидную HMAC-SHA256 подпись для безопасности.

### Генерация подписи

```python
import hmac
import hashlib
import json

def generate_signature(lots, shared_key):
    normalized = json.dumps(lots, separators=(',', ':'), sort_keys=True)
    return hmac.new(shared_key.encode(), normalized.encode(), hashlib.sha256).hexdigest()
```

⚠️ **Внимание:** Недействительные подписи приводят к HTTP 403 Forbidden ответам.

## Синхронный режим

Для обработки одного автомобиля с немедленным ответом (≤300 секунд).

### Формат запроса

**POST** `/api/v1/generate-descriptions`

```json
{
  "signature": "hmac_sha256_signature_here",
  "version": "1.0.0",
  "languages": ["en", "ru", "fr"],
  "lots": [
    {
      "lot_id": "11-12345",
      "additional_info": "2019 Toyota Camry, front collision damage",
      "images": [
        {"url": "https://example.com/car1.jpg"},
        {"url": "https://example.com/car2.jpg"}
      ]
    }
  ]
}
```

### Успешный ответ (200 OK)

```json
{
  "version": "1.0.0",
  "lots": [
    {
      "lot_id": "11-12345",
      "descriptions": [
        {
          "language": "en",
          "damages": "<p>Front-end collision damage visible...</p>"
        },
        {
          "language": "ru", 
          "damages": "<p>Повреждения от лобового столкновения...</p>"
        }
      ],
      "missing_images": ["https://example.com/unreachable.jpg"]
    }
  ]
}
```

## Пакетный режим

Для обработки множественных автомобилей (2-50,000) с webhook уведомлениями.

### Формат запроса

**POST** `/api/v1/generate-descriptions`

```json
{
  "signature": "hmac_sha256_signature_here",
  "version": "1.0.0", 
  "languages": ["en", "de"],
  "lots": [
    {
      "webhook": "https://your-app.com/webhook",
      "lot_id": "batch-001",
      "additional_info": "BMW X5 damage assessment",
      "images": [{"url": "https://example.com/bmw1.jpg"}]
    },
    {
      "webhook": "https://your-app.com/webhook",
      "lot_id": "batch-002", 
      "additional_info": "Mercedes C-Class inspection",
      "images": [{"url": "https://example.com/merc1.jpg"}]
    }
  ]
}
```

### Ответ принятия (201)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted"
}
```

### Проверка статуса пакета

**GET** `/api/v1/batch-status/{job_id}`

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-01-06T10:30:00Z"
}
```

## Формат webhook

Webhook уведомления отправляются при завершении пакетной обработки.

### Payload webhook

**POST** `{your_webhook_url}`

```json
{
  "signature": "hmac_sha256_signature_here",
  "version": "1.0.0",
  "lots": [
    {
      "lot_id": "batch-001",
      "descriptions": [
        {
          "language": "en",
          "damages": "<p>Detailed damage assessment...</p>"
        },
        {
          "language": "de", 
          "damages": "<p>Detaillierte Schadensbewertung...</p>"
        }
      ],
      "missing_images": []
    }
  ]
}
```

ℹ️ **Политика повторов:** Webhook повторяются до 5 раз с экспоненциальной задержкой (1s → 16s).

## Примеры кода

### Python пример

```python
import requests
import hmac
import hashlib
import json

def generate_signature(lots, shared_key):
    normalized = json.dumps(lots, separators=(',', ':'), sort_keys=True)
    return hmac.new(shared_key.encode(), normalized.encode(), hashlib.sha256).hexdigest()

# Одна машина (синхронный режим)
lots = [{
    "lot_id": "test-001",
    "additional_info": "Test car damage assessment",
    "images": [{"url": "https://example.com/car.jpg"}]
}]

payload = {
    "signature": generate_signature(lots, "your-shared-key"),
    "version": "1.0.0",
    "languages": ["en", "es"],
    "lots": lots
}

response = requests.post(
    "http://localhost:5000/api/v1/generate-descriptions",
    json=payload,
    headers={"Content-Type": "application/json"}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### cURL пример

```bash
curl -X POST http://localhost:5000/api/v1/generate-descriptions \
  -H "Content-Type: application/json" \
  -d '{
    "signature": "your_hmac_signature_here",
    "version": "1.0.0",
    "languages": ["en", "fr"],
    "lots": [{
      "lot_id": "curl-test-001",
      "additional_info": "Testing via cURL",
      "images": [{"url": "https://example.com/test-car.jpg"}]
    }]
  }'
```

## Ограничения и лимиты

### Лимиты обработки

| Тип лимита | Синхронный режим | Пакетный режим |
|------------|------------------|----------------|
| Макс. изображений на машину | 20 | Без ограничений |
| Макс. машин на запрос | 1 | 50,000 |
| Макс. размер изображения | 10 MB | 10 MB |
| Макс. размер пакетного файла | N/A | 200 MB |
| Тайм-аут ответа | 300 секунд | 24 часа |

### HTTP коды статусов

| Код статуса | Описание | Частые причины |
|------------|----------|----------------|
| **200** | OK - Синхронная обработка завершена | Одна машина обработана успешно |
| **201** | Accepted - Пакетная задача создана | Несколько машин отправлены на пакетную обработку |
| **400** | Bad Request | Неверный JSON, отсутствующие поля, превышен лимит |
| **403** | Forbidden | Неверная HMAC подпись |
| **404** | Not Found | ID пакетной задачи не найден |
| **500** | Internal Server Error | Ошибка OpenAI API, ошибка обработки |

## Дополнительные endpoints

### Проверка здоровья сервиса

**GET** `/health`

```json
{
  "status": "healthy",
  "timestamp": "2025-01-06T10:30:00Z"
}
```

### Валидация изображений

**POST** `/api/v1/validate-images`

```json
{
  "images": [
    {"url": "https://example.com/car1.jpg"},
    {"url": "https://example.com/car2.jpg"}
  ]
}
```

Ответ:
```json
{
  "valid_images": ["https://example.com/car1.jpg"],
  "invalid_images": ["https://example.com/car2.jpg"],
  "validation_percentage": 50.0
}
```

---

© 2025 Generation Service - AI-Powered Car Description API