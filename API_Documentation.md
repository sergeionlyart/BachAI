# Generation Service API Documentation

## Обзор

Generation Service API представляет собой производственно-готовый микросервис для ИИ-анализа повреждений автомобилей и генерации многоязычных описаний с использованием OpenAI Vision и Translation моделей.

### Ключевые возможности

- **Vision анализ** с использованием OpenAI o4-mini модели с максимальной точностью
- **Многоязычный перевод** с использованием GPT-4.1-mini для до 100+ языков
- **Синхронная обработка** для одного автомобиля (≤300 сек) с мгновенными результатами  
- **Пакетная обработка** до 50,000 автомобилей одновременно (≤24 часа)
- **PostgreSQL интеграция** для надежного хранения и отслеживания заданий
- **Background Worker** для автоматического мониторинга и обработки
- **Polling API** для проверки статуса и получения результатов в реальном времени
- **Webhook система** с автоматическими повторами и экспоненциальной задержкой
- **HMAC-SHA256 валидация** для безопасности всех запросов

### Архитектура обработки

| Режим обработки | Условие запуска | Макс. изображений/машина | Время ответа | Persistence |
|----------------|-----------------|-------------------------|--------------|-------------|
| **Синхронный** | 1 машина в запросе | ≤ 20 | ≤ 300 секунд | Временная |
| **Пакетный** | 2+ машины в запросе | Без ограничений | ≤ 24 часа | PostgreSQL |
| **Polling** | GET запросы к результатам | N/A | Мгновенно | PostgreSQL |
| **Webhook** | Автоматические уведомления | N/A | Мгновенно | PostgreSQL |

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
  "status": "accepted",
  "created_at": "2025-08-05T07:30:00Z",
  "total_lots": 2,
  "languages": ["en", "de"],
  "estimated_completion": "2025-08-05T08:30:00Z"
}
```

### Статусы пакетной обработки

| Статус | Описание | Действия пользователя |
|--------|----------|----------------------|
| **pending** | Задание создано, ожидает обработки | Ожидать или использовать polling |
| **processing** | OpenAI обрабатывает vision анализ | Использовать polling для мониторинга |
| **translating** | Выполняется перевод на другие языки | Использовать polling для мониторинга |
| **completed** | Все обработано, результаты готовы | Получить результаты через polling или webhook |
| **failed** | Ошибка в обработке | Проверить error_message, повторить запрос |
| **cancelled** | Задание отменено пользователем | Создать новое задание при необходимости |

## Polling API - Отслеживание заданий

Polling API позволяет в реальном времени отслеживать статус и получать результаты пакетных заданий.

### Проверка статуса задания

**GET** `/api/v1/batch-status/{job_id}`

**Headers:**
```
Content-Type: application/json
X-Signature: sha256=your_hmac_signature
```

**Успешный ответ (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-08-05T07:30:00Z",
  "updated_at": "2025-08-05T07:35:00Z",
  "progress": {
    "total_lots": 100,
    "processed_lots": 45,
    "failed_lots": 2,
    "completion_percentage": 45.0
  },
  "languages": ["en", "ru", "de"],
  "error_message": null,
  "openai_vision_batch_id": "batch_67890abc",
  "openai_translation_batch_id": "batch_12345def"
}
```

### Получение результатов

**GET** `/api/v1/batch-results/{job_id}`

**Ответ для завершенного задания (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2025-08-05T08:15:00Z",
  "results": {
    "version": "1.0.0",
    "total_lots": 2,
    "processed_lots": 2,
    "failed_lots": 0,
    "lots": [
      {
        "lot_id": "batch-001",
        "status": "completed",
        "descriptions": [
          {
            "language": "en",
            "damages": "<p>Significant front-end collision damage...</p>"
          },
          {
            "language": "de",
            "damages": "<p>Erhebliche Frontschäden durch Kollision...</p>"
          }
        ],
        "missing_images": []
      }
    ]
  }
}
```

**Ответ для незавершенного задания (202):**
```json
{
  "error": "Job not completed",
  "status": "processing",
  "message": "Job is currently processing. Results will be available when status is 'completed'."
}
```

### Скачивание результатов

**GET** `/api/v1/batch-results/{job_id}/download`

Возвращает файл `batch_results_{job_id}.json` для скачивания с полными результатами.

### Список заданий

**GET** `/api/v1/batch-jobs?status=processing&limit=10&offset=0`

**Query параметры:**
- `status` (optional): Фильтр по статусу (`pending`, `processing`, `completed`, `failed`, `cancelled`)
- `limit` (optional): Количество записей (max 100, default 10)
- `offset` (optional): Смещение для пагинации (default 0)

**Ответ (200):**
```json
{
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "processing",
      "created_at": "2025-08-05T07:30:00Z",
      "updated_at": "2025-08-05T07:35:00Z",
      "total_lots": 50,
      "processed_lots": 25,
      "languages": ["en", "fr"],
      "progress": {
        "total_lots": 50,
        "processed_lots": 25,
        "failed_lots": 1,
        "completion_percentage": 50.0
      }
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 1
  }
}
```

### Отмена задания

**POST** `/api/v1/batch-jobs/{job_id}/cancel`

**Headers:**
```
Content-Type: application/json
X-Signature: sha256=your_hmac_signature
```

**Успешный ответ (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Job successfully cancelled"
}
```

**Ошибка отмены (400):**
```json
{
  "error": "Job cannot be cancelled",
  "status": "completed",
  "message": "Only pending, processing, or translating jobs can be cancelled. Current status: completed"
}
```

## Webhook система

Production-ready webhook система с автоматическими повторами и надежной доставкой.

### Автоматические уведомления

Webhook уведомления отправляются автоматически при завершении пакетной обработки через background worker сервис.

### Формат webhook payload

**POST** `{your_webhook_url}`

**Headers:**
```
Content-Type: application/json
X-Signature: sha256=hmac_signature_for_payload_verification
User-Agent: Generation-Service/1.0
```

**Payload:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2025-08-05T08:15:00Z",
  "lots": [
    {
      "lot_id": "batch-001",
      "status": "completed",
      "descriptions": [
        {
          "language": "en",
          "damages": "<p>Detailed damage assessment with specific details about collision impact, structural damage, and repair recommendations...</p>"
        },
        {
          "language": "de", 
          "damages": "<p>Detaillierte Schadensbewertung mit spezifischen Details über Kollisionsauswirkungen, strukturelle Schäden und Reparaturempfehlungen...</p>"
        }
      ],
      "missing_images": []
    },
    {
      "lot_id": "batch-002",
      "status": "completed", 
      "descriptions": [
        {
          "language": "en",
          "damages": "<p>Minor cosmetic damage on rear bumper...</p>"
        },
        {
          "language": "de",
          "damages": "<p>Geringfügige kosmetische Schäden am hinteren Stoßfänger...</p>"
        }
      ],
      "missing_images": ["https://example.com/unreachable-image.jpg"]
    }
  ]
}
```

### Верификация webhook

Все webhook payload подписываются HMAC-SHA256 для верификации:

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload_json, received_signature, shared_key):
    expected_signature = hmac.new(
        shared_key.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={expected_signature}" == received_signature
```

### Политика повторов

**Background Worker** автоматически обрабатывает failed webhook доставки:

| Попытка | Задержка | Статус |
|---------|----------|--------|
| 1 | Немедленно | Initial attempt |
| 2 | 30 секунд | Exponential backoff |
| 3 | 60 секунд | 2^1 * 30s |
| 4 | 120 секунд | 2^2 * 30s |
| 5 | 240 секунд | 2^3 * 30s |
| 6+ | **Failed** | Максимум 5 попыток |

**Успешная доставка:** HTTP статус коды 200, 201, или 202  
**Failed доставка:** Все остальные статус коды, таймауты, или network errors

### Мониторинг webhook доставки

Все webhook доставки отслеживаются в PostgreSQL с полной историей попыток:

```sql
SELECT 
  webhook_url,
  status,
  attempt_count,
  last_attempt_at,
  delivered_at,
  error_message
FROM webhook_deliveries 
WHERE batch_job_id = 'your-job-id';
```

## Примеры кода

### Python примеры

#### Синхронная обработка одного автомобиля

```python
import requests
import hmac
import hashlib
import json
import time

class GenerationServiceClient:
    def __init__(self, base_url, shared_key):
        self.base_url = base_url
        self.shared_key = shared_key
    
    def generate_signature(self, lots):
        normalized = json.dumps(lots, separators=(',', ':'), sort_keys=True)
        return hmac.new(self.shared_key.encode(), normalized.encode(), hashlib.sha256).hexdigest()
    
    def sync_generate(self, lot_id, additional_info, image_urls, languages=["en"]):
        """Синхронная обработка одного автомобиля"""
        lots = [{
            "lot_id": lot_id,
            "additional_info": additional_info,
            "images": [{"url": url} for url in image_urls]
        }]
        
        payload = {
            "signature": self.generate_signature(lots),
            "version": "1.0.0",
            "languages": languages,
            "lots": lots
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/generate-descriptions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 минут для синхронного режима
        )
        
        return response.json(), response.status_code

# Использование
client = GenerationServiceClient("http://localhost:5000", "your-shared-key")

result, status = client.sync_generate(
    lot_id="test-001",
    additional_info="2019 Toyota Camry, front collision damage",
    image_urls=["https://example.com/car1.jpg", "https://example.com/car2.jpg"],
    languages=["en", "ru", "fr"]
)

print(f"Status: {status}")
print(f"Result: {json.dumps(result, indent=2)}")
```

#### Пакетная обработка с polling

```python
def batch_generate_with_polling(self, cars_data, languages=["en"], webhook_url=None):
    """Пакетная обработка с polling для получения результатов"""
    
    # Подготовка lots для пакетной обработки
    lots = []
    for car in cars_data:
        lot = {
            "lot_id": car["lot_id"],
            "additional_info": car["additional_info"],
            "images": [{"url": url} for url in car["image_urls"]]
        }
        if webhook_url:
            lot["webhook"] = webhook_url
        lots.append(lot)
    
    # Отправка пакетного запроса
    payload = {
        "signature": self.generate_signature(lots),
        "version": "1.0.0",
        "languages": languages,
        "lots": lots
    }
    
    response = requests.post(
        f"{self.base_url}/api/v1/generate-descriptions",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 201:
        return None, f"Failed to create batch job: {response.text}"
    
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"Batch job created: {job_id}")
    
    # Polling для отслеживания прогресса
    return self.poll_for_results(job_id)

def poll_for_results(self, job_id, poll_interval=30, max_wait_time=3600):
    """Polling результатов пакетного задания"""
    start_time = time.time()
    
    # Создаем signature для polling запросов
    polling_signature = hmac.new(
        self.shared_key.encode(),
        job_id.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Signature": f"sha256={polling_signature}"
    }
    
    while time.time() - start_time < max_wait_time:
        # Проверяем статус
        status_response = requests.get(
            f"{self.base_url}/api/v1/batch-status/{job_id}",
            headers=headers
        )
        
        if status_response.status_code != 200:
            return None, f"Failed to get status: {status_response.text}"
        
        status_data = status_response.json()
        print(f"Job {job_id} status: {status_data['status']} - "
              f"{status_data['progress']['completion_percentage']:.1f}% complete")
        
        if status_data["status"] == "completed":
            # Получаем результаты
            results_response = requests.get(
                f"{self.base_url}/api/v1/batch-results/{job_id}",
                headers=headers
            )
            
            if results_response.status_code == 200:
                return results_response.json(), None
            else:
                return None, f"Failed to get results: {results_response.text}"
        
        elif status_data["status"] == "failed":
            return None, f"Job failed: {status_data.get('error_message', 'Unknown error')}"
        
        elif status_data["status"] == "cancelled":
            return None, "Job was cancelled"
        
        # Ждем перед следующей проверкой
        time.sleep(poll_interval)
    
    return None, f"Timeout after {max_wait_time} seconds"

# Использование пакетной обработки
cars_data = [
    {
        "lot_id": "batch-001",
        "additional_info": "BMW X5 damage assessment",
        "image_urls": ["https://example.com/bmw1.jpg", "https://example.com/bmw2.jpg"]
    },
    {
        "lot_id": "batch-002", 
        "additional_info": "Mercedes C-Class inspection",
        "image_urls": ["https://example.com/merc1.jpg"]
    }
]

results, error = client.batch_generate_with_polling(
    cars_data=cars_data,
    languages=["en", "de", "fr"],
    webhook_url="https://your-app.com/webhook"
)

if error:
    print(f"Error: {error}")
else:
    print(f"Results: {json.dumps(results, indent=2)}")
```

#### Отмена пакетного задания

```python
def cancel_batch_job(self, job_id):
    """Отмена пакетного задания"""
    cancel_signature = hmac.new(
        self.shared_key.encode(),
        job_id.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Signature": f"sha256={cancel_signature}"
    }
    
    response = requests.post(
        f"{self.base_url}/api/v1/batch-jobs/{job_id}/cancel",
        headers=headers
    )
    
    return response.json(), response.status_code

# Отмена задания
result, status = client.cancel_batch_job("550e8400-e29b-41d4-a716-446655440000")
print(f"Cancel result: {result}")
```

### cURL примеры

#### Синхронная обработка

```bash
# Генерация подписи (используйте этот скрипт)
echo '[{"lot_id":"curl-test-001","additional_info":"Testing via cURL","images":[{"url":"https://example.com/test-car.jpg"}]}]' | \
openssl dgst -sha256 -hmac "your-shared-key"

# Синхронный запрос
curl -X POST http://localhost:5000/api/v1/generate-descriptions \
  -H "Content-Type: application/json" \
  -d '{
    "signature": "calculated_hmac_signature_here",
    "version": "1.0.0",
    "languages": ["en", "fr", "de"],
    "lots": [{
      "lot_id": "curl-test-001",
      "additional_info": "2020 BMW X3, minor rear damage",
      "images": [
        {"url": "https://example.com/test-car1.jpg"},
        {"url": "https://example.com/test-car2.jpg"}
      ]
    }]
  }'
```

#### Пакетная обработка

```bash
# Пакетный запрос
curl -X POST http://localhost:5000/api/v1/generate-descriptions \
  -H "Content-Type: application/json" \
  -d '{
    "signature": "calculated_hmac_signature_here",
    "version": "1.0.0",
    "languages": ["en", "ru"],
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
        "additional_info": "Mercedes inspection",
        "images": [{"url": "https://example.com/merc1.jpg"}]
      }
    ]
  }'
```

#### Polling статуса и результатов

```bash
# Проверка статуса задания
JOB_ID="550e8400-e29b-41d4-a716-446655440000"
SIGNATURE=$(echo -n "$JOB_ID" | openssl dgst -sha256 -hmac "your-shared-key" | sed 's/^.* //')

curl -X GET "http://localhost:5000/api/v1/batch-status/$JOB_ID" \
  -H "Content-Type: application/json" \
  -H "X-Signature: sha256=$SIGNATURE"

# Получение результатов
curl -X GET "http://localhost:5000/api/v1/batch-results/$JOB_ID" \
  -H "Content-Type: application/json" \
  -H "X-Signature: sha256=$SIGNATURE"

# Скачивание результатов как файл
curl -X GET "http://localhost:5000/api/v1/batch-results/$JOB_ID/download" \
  -H "X-Signature: sha256=$SIGNATURE" \
  -o "batch_results_$JOB_ID.json"

# Список всех заданий
curl -X GET "http://localhost:5000/api/v1/batch-jobs?status=processing&limit=20" \
  -H "X-Signature: sha256=$SIGNATURE"

# Отмена задания
curl -X POST "http://localhost:5000/api/v1/batch-jobs/$JOB_ID/cancel" \
  -H "Content-Type: application/json" \
  -H "X-Signature: sha256=$SIGNATURE"
```

## Ограничения и лимиты

### Лимиты обработки

| Тип лимита | Синхронный режим | Пакетный режим | Polling режим |
|------------|------------------|----------------|---------------|
| Макс. изображений на машину | 20 | Без ограничений | N/A |
| Макс. машин на запрос | 1 | 50,000 | N/A |
| Макс. размер изображения | 10 MB | 10 MB | N/A |
| Макс. размер пакетного файла | N/A | 200 MB | N/A |
| Тайм-аут ответа | 300 секунд | 24 часа | 30 секунд |
| Макс. языков перевода | 2 (sync) | Без ограничений | N/A |
| Частота polling запросов | N/A | N/A | Рекомендуется 30+ секунд |

### HTTP коды статусов

| Код статуса | Описание | Endpoints | Частые причины |
|------------|----------|-----------|----------------|
| **200** | OK - Успешно | Все GET endpoints | Данные получены успешно |
| **201** | Created - Пакетная задача создана | `/generate-descriptions` | Batch job создан и запущен |
| **202** | Accepted - Не готово | `/batch-results/{id}` | Задание еще обрабатывается |
| **400** | Bad Request | Все endpoints | Неверный JSON, отсутствующие поля, превышен лимит |
| **401** | Unauthorized | Polling endpoints | Неверная подпись в заголовке X-Signature |
| **403** | Forbidden | `/generate-descriptions` | Неверная HMAC подпись в payload |
| **404** | Not Found | Все endpoints с {job_id} | ID пакетной задачи не найден |
| **500** | Internal Server Error | Все endpoints | Ошибка OpenAI API, ошибка базы данных |

### Rate Limiting

| Тип запроса | Лимит | Период | Действие при превышении |
|-------------|-------|--------|-------------------------|
| Синхронные запросы | 100 | 1 час | HTTP 429 - слишком много запросов |
| Пакетные запросы | 20 | 1 час | HTTP 429 - слишком много запросов |
| Polling запросы | 1000 | 1 час | HTTP 429 - слишком много запросов |

## Дополнительные endpoints

### Проверка здоровья сервиса

**GET** `/health`

```json
{
  "status": "healthy",
  "service": "generation-service",
  "timestamp": "2025-08-05T07:30:00Z",
  "version": "1.0.0",
  "database": "connected",
  "background_worker": "running"
}
```

### Тестирование валидации изображений

**POST** `/api/v1/test-image-validation`

```json
{
  "urls": [
    "https://example.com/car1.jpg",
    "https://example.com/car2.jpg",
    "https://invalid-url.com/missing.jpg"
  ]
}
```

**Ответ:**
```json
{
  "valid_urls": ["https://example.com/car1.jpg"],
  "unreachable_urls": ["https://example.com/car2.jpg", "https://invalid-url.com/missing.jpg"],
  "threshold_met": false
}
```

## Мониторинг и отладка

### Логирование

Сервис ведет структурированные логи для всех операций:
- **INFO**: Успешные операции, создание заданий, завершение обработки
- **WARNING**: Недоступные изображения, проблемы с webhook доставкой
- **ERROR**: Ошибки OpenAI API, проблемы с базой данных, failed задания

### Метрики (для мониторинга)

```python
# Ключевые метрики для отслеживания
- generation_requests_total{mode="sync|batch"}
- generation_duration_seconds{mode="sync|batch"}
- openai_api_errors_total{api="vision|translation"}
- webhook_deliveries_total{status="success|failed"}
- batch_jobs_total{status="pending|processing|completed|failed"}
- database_operations_total{operation="create|read|update"}
```

### Troubleshooting

#### Частые проблемы

1. **403 Forbidden** - Проверьте генерацию HMAC подписи
2. **Недоступные изображения** - Убедитесь что URLs доступны публично
3. **Webhook не доставляется** - Проверьте endpoint и firewall правила
4. **Долгая обработка** - OpenAI batch API может занимать до 24 часов

#### Отладочные endpoints

```bash
# Проверка подключения к базе данных
curl http://localhost:5000/health

# Тестирование доступности изображений
curl -X POST http://localhost:5000/api/v1/test-image-validation \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://your-image-url.jpg"]}'
```

## Production Deployment

### Требования к окружению

```bash
# Обязательные переменные окружения
export DATABASE_URL="postgresql://user:password@host:5432/database"
export OPENAI_API_KEY="sk-your-openai-api-key"
export SHARED_KEY="your-secret-hmac-key-minimum-32-chars"

# Опциональные переменные
export SESSION_SECRET="your-session-secret-key"
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

### Архитектура системы

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Flask App      │    │   PostgreSQL    │
│   (nginx/HAProxy│◄───┤   (Gunicorn)     │◄───┤   Database      │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Background Worker│    │   OpenAI API    │
                       │   (Threading)    │◄───┤   (Batch API)   │
                       │                  │    │                 │
                       └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Webhook URLs   │
                       │   (Client Apps)  │
                       │                  │
                       └──────────────────┘
```

### Рекомендации для production

1. **Database**: Используйте PostgreSQL с connection pooling
2. **Scaling**: Запускайте несколько worker процессов с Gunicorn
3. **Monitoring**: Настройте логирование и метрики мониторинга
4. **Security**: Используйте HTTPS и надежные HMAC ключи
5. **Backup**: Регулярно создавайте backup базы данных с результатами

---

© 2025 Generation Service - Production-Ready AI Car Description API  
**Версия документации:** 2.0 | **Дата обновления:** 5 августа 2025  
**Поддержка:** Полная интеграция PostgreSQL, Background Worker, Polling API