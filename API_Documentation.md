# Generation Service API Documentation v2.0

## Обзор системы

Generation Service — это production-ready микросервис для автоматической генерации многоязычных описаний повреждений автомобилей на основе анализа изображений с использованием искусственного интеллекта OpenAI.

### 🚀 Ключевые возможности

- **AI Vision Analysis**: Анализ изображений автомобилей с использованием OpenAI o4-mini модели с максимальной точностью
- **Многоязычный перевод**: Автоматический перевод на 100+ языков с использованием GPT-4.1-mini
- **PostgreSQL интеграция**: Полная persistence система для надежного хранения заданий и результатов
- **Background Worker**: Автоматический мониторинг, обработка результатов и доставка webhook уведомлений
- **Polling API**: Система real-time отслеживания статуса заданий и получения результатов
- **Синхронная обработка**: Мгновенные результаты для одного автомобиля (≤300 секунд)
- **Пакетная обработка**: Обработка до 50,000 автомобилей одновременно (≤24 часа)
- **Webhook система**: Автоматические уведомления с retry механизмами и exponential backoff
- **HMAC-SHA256 безопасность**: Валидация подписей для всех запросов

### 🏗️ Архитектура системы

| Компонент | Описание | Технология |
|-----------|----------|-------------|
| **Flask API** | Основное REST API приложение | Flask + Gunicorn |
| **PostgreSQL** | База данных для persistent хранения | PostgreSQL + SQLAlchemy |
| **Background Worker** | Автоматический мониторинг и webhook доставка | Python threading |
| **OpenAI Integration** | Vision анализ и перевод текстов | OpenAI Responses API |
| **Webhook System** | Надежная доставка уведомлений | HTTP callbacks + retry logic |

### 📊 Режимы обработки

| Режим | Условие активации | Макс. изображений | Время ответа | Persistence | Уведомления |
|-------|------------------|-------------------|---------------|-------------|-------------|
| **Синхронный** | 1 автомобиль в запросе | ≤ 20 | ≤ 300 секунд | Временная | Немедленно |
| **Пакетный** | 2+ автомобилей в запросе | Без ограничений | ≤ 24 часа | PostgreSQL | Webhook |
| **Polling** | GET запросы к API | N/A | Мгновенно | PostgreSQL | Real-time |

## 🔐 Аутентификация и безопасность

Все запросы к API должны содержать валидную HMAC-SHA256 подпись в заголовке `X-Signature` или в теле запроса.

### Генерация подписи для requests

```python
import hmac
import hashlib
import json

def generate_signature(data, shared_key):
    """Генерация HMAC-SHA256 подписи для payload"""
    if isinstance(data, dict):
        # Для JSON payload (batch/sync requests)
        normalized = json.dumps(data["lots"], separators=(',', ':'), sort_keys=True)
    else:
        # Для polling requests (string job_id)
        normalized = str(data)
    
    signature = hmac.new(
        shared_key.encode(),
        normalized.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"

# Пример использования для batch request
payload = {"lots": [...]}  # ваши данные
signature = generate_signature(payload, "your-shared-key")

# Для polling requests
job_id = "550e8400-e29b-41d4-a716-446655440000"
polling_signature = generate_signature(job_id, "your-shared-key")
```

### Заголовки безопасности

```http
Content-Type: application/json
X-Signature: sha256=your_hmac_signature_here
User-Agent: YourApp/1.0
```

⚠️ **Важно**: Неверные подписи приводят к HTTP 403 Forbidden ответам.

## 🔄 Синхронный режим

Обработка одного автомобиля с мгновенным получением результатов (время ответа ≤300 секунд).

### Формат запроса

**POST** `/api/v1/generate-descriptions`

```json
{
  "signature": "sha256=hmac_sha256_signature_here",
  "version": "1.0.0",
  "languages": ["en", "ru", "de"],
  "lots": [
    {
      "lot_id": "sync-12345",
      "additional_info": "2021 BMW X5, front collision damage, airbags deployed",
      "images": [
        {"url": "https://example.com/bmw-front.jpg"},
        {"url": "https://example.com/bmw-side.jpg"},
        {"url": "https://example.com/bmw-interior.jpg"}
      ]
    }
  ]
}
```

### Успешный ответ (200 OK)

```json
{
  "version": "1.0.0",
  "processing_mode": "synchronous",
  "total_lots": 1,
  "processed_at": "2025-08-05T08:30:15Z",
  "lots": [
    {
      "lot_id": "sync-12345",
      "status": "completed",
      "processed_images": 3,
      "descriptions": [
        {
          "language": "en",
          "damages": "<p>Significant front-end collision damage with extensive structural deformation. The vehicle shows impact damage to the front bumper, hood, and headlight assemblies. Airbag deployment indicates high-impact collision. Engine compartment integrity may be compromised.</p>"
        },
        {
          "language": "ru",
          "damages": "<p>Значительные повреждения передней части от столкновения с обширной структурной деформацией. Автомобиль показывает повреждения переднего бампера, капота и блоков фар. Срабатывание подушек безопасности указывает на сильное столкновение.</p>"
        },
        {
          "language": "de",
          "damages": "<p>Erhebliche Frontschäden durch Kollision mit ausgedehnter struktureller Verformung. Das Fahrzeug zeigt Aufprallschäden an der vorderen Stoßstange, der Motorhaube und den Scheinwerfereinheiten.</p>"
        }
      ],
      "missing_images": []
    }
  ]
}
```

## 📦 Пакетный режим

Асинхронная обработка множественных автомобилей (2-50,000) с PostgreSQL persistence и webhook уведомлениями.

### Создание пакетного задания

**POST** `/api/v1/generate-descriptions`

```json
{
  "signature": "sha256=hmac_sha256_signature_here",
  "version": "1.0.0",
  "languages": ["en", "fr", "de"],
  "lots": [
    {
      "lot_id": "batch-001",
      "webhook": "https://your-app.com/webhooks/generation-complete",
      "additional_info": "2019 Mercedes C-Class, minor rear damage",
      "images": [
        {"url": "https://example.com/merc-rear.jpg"},
        {"url": "https://example.com/merc-bumper.jpg"}
      ]
    },
    {
      "lot_id": "batch-002",
      "webhook": "https://your-app.com/webhooks/generation-complete",
      "additional_info": "2020 Audi A4, hail damage assessment",
      "images": [
        {"url": "https://example.com/audi-roof.jpg"},
        {"url": "https://example.com/audi-hood.jpg"},
        {"url": "https://example.com/audi-side.jpg"}
      ]
    }
  ]
}
```

### Ответ принятия задания (201 Created)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "created_at": "2025-08-05T07:30:00Z",
  "total_lots": 2,
  "languages": ["en", "fr", "de"],
  "estimated_completion": "2025-08-05T08:30:00Z",
  "processing_mode": "batch",
  "webhook_configured": true
}
```

### 📊 Жизненный цикл пакетного задания

| Статус | Описание | Длительность | Действия пользователя |
|--------|----------|--------------|----------------------|
| **pending** | Задание создано, ожидает обработки | 1-5 минут | Мониторинг через polling |
| **processing** | OpenAI выполняет vision анализ | 30 минут - 12 часов | Мониторинг прогресса |
| **translating** | Перевод результатов на другие языки | 5-30 минут | Ожидание завершения |
| **completed** | Все результаты готовы | - | Получение через polling/webhook |
| **failed** | Ошибка обработки | - | Анализ error_message, retry |
| **cancelled** | Отменено пользователем | - | Создание нового задания |

## 🔍 Polling API - Система отслеживания

Real-time мониторинг статуса заданий и получение результатов через PostgreSQL.

### Проверка статуса задания

**GET** `/api/v1/batch-status/{job_id}`

**Headers:**
```http
Content-Type: application/json
X-Signature: sha256=hmac_signature_for_job_id
```

**Успешный ответ (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-08-05T07:30:00Z",
  "updated_at": "2025-08-05T07:45:00Z",
  "progress": {
    "total_lots": 100,
    "processed_lots": 67,
    "failed_lots": 3,
    "completion_percentage": 67.0,
    "estimated_completion": "2025-08-05T08:15:00Z"
  },
  "languages": ["en", "ru", "de"],
  "processing_details": {
    "openai_vision_batch_id": "batch_67890abc",
    "openai_translation_batch_id": "batch_12345def",
    "current_stage": "vision_analysis"
  },
  "error_message": null,
  "webhook_configured": true
}
```

### Получение результатов

**GET** `/api/v1/batch-results/{job_id}`

**Ответ для завершенного задания (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2025-08-05T08:15:00Z",
  "processing_summary": {
    "total_lots": 2,
    "processed_lots": 2,
    "failed_lots": 0,
    "total_images_processed": 5,
    "total_processing_time": "45 minutes"
  },
  "results": {
    "version": "1.0.0",
    "lots": [
      {
        "lot_id": "batch-001",
        "status": "completed",
        "processed_at": "2025-08-05T08:10:00Z",
        "processed_images": 2,
        "descriptions": [
          {
            "language": "en",
            "damages": "<p>Minor rear-end collision damage. The rear bumper shows impact deformation with paint scratches and minor denting. No structural damage visible. Recommended repairs include bumper replacement and paint touch-up.</p>"
          },
          {
            "language": "fr", 
            "damages": "<p>Dommages mineurs de collision arrière. Le pare-chocs arrière présente une déformation d'impact avec des rayures de peinture et des bosses mineures.</p>"
          },
          {
            "language": "de",
            "damages": "<p>Geringfügige Heckaufprallschäden. Die hintere Stoßstange zeigt Aufprallverformungen mit Lackkratzern und kleineren Dellen.</p>"
          }
        ],
        "missing_images": []
      },
      {
        "lot_id": "batch-002",
        "status": "completed",
        "processed_at": "2025-08-05T08:12:00Z", 
        "processed_images": 3,
        "descriptions": [
          {
            "language": "en",
            "damages": "<p>Extensive hail damage assessment. Multiple small to medium-sized dents across the roof, hood, and side panels. Paint integrity maintained. Paintless dent repair recommended for most damage areas.</p>"
          },
          {
            "language": "fr",
            "damages": "<p>Évaluation complète des dommages de grêle. Multiples bosses de petite à moyenne taille sur le toit, le capot et les panneaux latéraux.</p>"
          },
          {
            "language": "de", 
            "damages": "<p>Umfassende Hagelschadenbewertung. Mehrere kleine bis mittelgroße Dellen auf dem Dach, der Motorhaube und den Seitenpaneelen.</p>"
          }
        ],
        "missing_images": ["https://example.com/audi-trunk.jpg"]
      }
    ]
  }
}
```

**Ответ для незавершенного задания (202 Accepted):**
```json
{
  "error": "Job not completed",
  "status": "processing", 
  "progress": {
    "completion_percentage": 45.0,
    "estimated_completion": "2025-08-05T08:30:00Z"
  },
  "message": "Job is currently processing. Results will be available when status is 'completed'."
}
```

### Скачивание результатов

**GET** `/api/v1/batch-results/{job_id}/download`

Возвращает JSON файл `batch_results_{job_id}.json` для скачивания.

**Headers ответа:**
```http
Content-Type: application/json
Content-Disposition: attachment; filename="batch_results_550e8400-e29b-41d4-a716-446655440000.json"
```

### Список заданий с фильтрацией

**GET** `/api/v1/batch-jobs?status=processing&limit=20&offset=0`

**Query параметры:**
- `status` (optional): `pending`, `processing`, `translating`, `completed`, `failed`, `cancelled`
- `limit` (optional): Количество записей (max 100, default 10)
- `offset` (optional): Смещение для пагинации (default 0)
- `created_after` (optional): ISO timestamp для фильтра по дате
- `created_before` (optional): ISO timestamp для фильтра по дате

**Ответ (200 OK):**
```json
{
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "processing",
      "created_at": "2025-08-05T07:30:00Z",
      "updated_at": "2025-08-05T07:45:00Z",
      "total_lots": 50,
      "processed_lots": 32,
      "failed_lots": 1,
      "languages": ["en", "fr"],
      "progress": {
        "completion_percentage": 64.0,
        "estimated_completion": "2025-08-05T08:20:00Z"
      },
      "webhook_configured": true
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 1,
    "has_more": false
  }
}
```

### Отмена задания

**POST** `/api/v1/batch-jobs/{job_id}/cancel`

**Успешная отмена (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "cancelled_at": "2025-08-05T08:00:00Z",
  "message": "Job successfully cancelled"
}
```

**Ошибка отмены (400 Bad Request):**
```json
{
  "error": "Job cannot be cancelled",
  "status": "completed",
  "message": "Only pending, processing, or translating jobs can be cancelled. Current status: completed"
}
```

## 🔔 Webhook система

Production-ready система автоматических уведомлений с Background Worker для надежной доставки.

### Автоматическая доставка

Background Worker автоматически отслеживает завершенные задания и доставляет webhook уведомления с retry механизмами.

### Формат webhook payload

**POST** `{your_webhook_url}`

**Headers:**
```http
Content-Type: application/json
X-Signature: sha256=hmac_signature_for_payload_verification
User-Agent: Generation-Service/2.0
X-Delivery-Attempt: 1
X-Job-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Payload:**
```json
{
  "event": "batch_job_completed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2025-08-05T08:15:00Z",
  "processing_summary": {
    "total_lots": 2,
    "processed_lots": 2,
    "failed_lots": 0,
    "total_processing_time": "45 minutes"
  },
  "lots": [
    {
      "lot_id": "batch-001",
      "status": "completed",
      "processed_images": 2,
      "descriptions": [
        {
          "language": "en",
          "damages": "<p>Comprehensive damage assessment with detailed analysis of structural integrity, cosmetic damage, and repair recommendations based on AI vision analysis...</p>"
        },
        {
          "language": "fr",
          "damages": "<p>Évaluation complète des dommages avec analyse détaillée de l'intégrité structurelle, des dommages cosmétiques...</p>"
        }
      ],
      "missing_images": []
    }
  ]
}
```

### Верификация webhook подписи

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload_json, received_signature, shared_key):
    """Верификация HMAC подписи webhook payload"""
    expected_signature = hmac.new(
        shared_key.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={expected_signature}" == received_signature

# Пример использования
def handle_webhook(request):
    payload_json = request.body.decode('utf-8')
    received_signature = request.headers.get('X-Signature')
    
    if verify_webhook_signature(payload_json, received_signature, "your-shared-key"):
        payload = json.loads(payload_json)
        # Обработка webhook данных
        return {"status": "success"}, 200
    else:
        return {"error": "Invalid signature"}, 403
```

### Политика повторов Background Worker

| Попытка | Задержка | Timeout | Статус |
|---------|----------|---------|--------|
| 1 | Немедленно | 30s | Initial delivery |
| 2 | 30 секунд | 30s | First retry |
| 3 | 60 секунд | 30s | Second retry (2^1 * 30s) |
| 4 | 120 секунд | 30s | Third retry (2^2 * 30s) |
| 5 | 240 секунд | 30s | Fourth retry (2^3 * 30s) |
| 6+ | **Failed** | - | Maximum attempts reached |

**Критерии успешной доставки:**
- HTTP статус коды: 200, 201, 202
- Ответ получен в течение 30 секунд
- Нет network errors

**Критерии неудачной доставки:**
- Все остальные HTTP статус коды (4xx, 5xx)
- Timeout (>30 секунд)
- Network errors (DNS, connection refused)

### Мониторинг webhook доставки

Все webhook доставки отслеживаются в PostgreSQL с полной историей:

```sql
-- Просмотр статуса доставки
SELECT 
  id,
  batch_job_id,
  webhook_url,
  status,
  attempt_count,
  created_at,
  last_attempt_at,
  delivered_at,
  error_message
FROM webhook_deliveries 
WHERE batch_job_id = '550e8400-e29b-41d4-a716-446655440000';

-- Статистика webhook доставок
SELECT 
  status,
  COUNT(*) as count,
  AVG(attempt_count) as avg_attempts
FROM webhook_deliveries 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY status;
```

## 💻 Примеры интеграции

### Python Client SDK

```python
import requests
import hmac
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple

class GenerationServiceClient:
    def __init__(self, base_url: str, shared_key: str):
        self.base_url = base_url.rstrip('/')
        self.shared_key = shared_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'GenerationServiceClient/1.0'
        })
    
    def _generate_signature(self, data) -> str:
        """Генерация HMAC-SHA256 подписи"""
        if isinstance(data, dict):
            # Для JSON payload
            normalized = json.dumps(data["lots"], separators=(',', ':'), sort_keys=True)
        else:
            # Для polling requests
            normalized = str(data)
        
        signature = hmac.new(
            self.shared_key.encode(),
            normalized.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def sync_generate(self,
                     lot_id: str,
                     additional_info: str,
                     image_urls: List[str],
                     languages: List[str] = ["en"]) -> Tuple[Dict, int]:
        """Синхронная обработка одного автомобиля"""
        
        lots = [{
            "lot_id": lot_id,
            "additional_info": additional_info,
            "images": [{"url": url} for url in image_urls]
        }]
        
        payload = {
            "signature": self._generate_signature({"lots": lots}),
            "version": "1.0.0",
            "languages": languages,
            "lots": lots
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/generate-descriptions",
            json=payload,
            timeout=300  # 5 минут для синхронного режима
        )
        
        return response.json(), response.status_code
    
    def batch_generate(self,
                      cars_data: List[Dict],
                      languages: List[str] = ["en"],
                      webhook_url: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Создание пакетного задания"""
        
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
        
        payload = {
            "signature": self._generate_signature({"lots": lots}),
            "version": "1.0.0",
            "languages": languages,
            "lots": lots
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/generate-descriptions",
            json=payload
        )
        
        if response.status_code == 201:
            job_data = response.json()
            return job_data["job_id"], None
        else:
            return None, f"Failed to create batch job: {response.text}"
    
    def get_job_status(self, job_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Получение статуса задания"""
        signature = self._generate_signature(job_id)
        headers = {"X-Signature": signature}
        
        response = self.session.get(
            f"{self.base_url}/api/v1/batch-status/{job_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Failed to get job status: {response.text}"
    
    def get_job_results(self, job_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Получение результатов задания"""
        signature = self._generate_signature(job_id)
        headers = {"X-Signature": signature}
        
        response = self.session.get(
            f"{self.base_url}/api/v1/batch-results/{job_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json(), None
        elif response.status_code == 202:
            return None, "Job not completed yet"
        else:
            return None, f"Failed to get results: {response.text}"
    
    def download_results(self, job_id: str, filename: Optional[str] = None) -> Tuple[bool, str]:
        """Скачивание результатов в файл"""
        signature = self._generate_signature(job_id)
        headers = {"X-Signature": signature}
        
        response = self.session.get(
            f"{self.base_url}/api/v1/batch-results/{job_id}/download",
            headers=headers
        )
        
        if response.status_code == 200:
            if not filename:
                filename = f"batch_results_{job_id}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(response.json(), f, indent=2, ensure_ascii=False)
            
            return True, f"Results saved to {filename}"
        else:
            return False, f"Failed to download results: {response.text}"
    
    def cancel_job(self, job_id: str) -> Tuple[bool, str]:
        """Отмена задания"""
        signature = self._generate_signature(job_id)
        headers = {"X-Signature": signature}
        
        response = self.session.post(
            f"{self.base_url}/api/v1/batch-jobs/{job_id}/cancel",
            headers=headers
        )
        
        if response.status_code == 200:
            return True, "Job cancelled successfully"
        else:
            return False, f"Failed to cancel job: {response.text}"
    
    def poll_for_completion(self,
                          job_id: str,
                          poll_interval: int = 30,
                          max_wait_time: int = 3600,
                          progress_callback: Optional[callable] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Polling до завершения задания с progress callback"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_data, error = self.get_job_status(job_id)
            
            if error:
                return None, error
            
            # Вызов callback функции для progress updates
            if progress_callback:
                progress_callback(status_data)
            
            if status_data["status"] == "completed":
                return self.get_job_results(job_id)
            elif status_data["status"] in ["failed", "cancelled"]:
                return None, f"Job {status_data['status']}: {status_data.get('error_message', 'Unknown error')}"
            
            time.sleep(poll_interval)
        
        return None, f"Timeout after {max_wait_time} seconds"

# Примеры использования
def main():
    client = GenerationServiceClient("http://localhost:5000", "your-shared-key")
    
    # Синхронная обработка
    print("=== Синхронная обработка ===")
    result, status = client.sync_generate(
        lot_id="sync-test-001",
        additional_info="2019 Toyota Camry, front collision damage",
        image_urls=[
            "https://example.com/car1.jpg",
            "https://example.com/car2.jpg"
        ],
        languages=["en", "ru"]
    )
    
    print(f"Status: {status}")
    if status == 200:
        print(f"Descriptions generated for lot: {result['lots'][0]['lot_id']}")
        for desc in result['lots'][0]['descriptions']:
            print(f"Language: {desc['language']}")
            print(f"Description: {desc['damages'][:100]}...")
    
    # Пакетная обработка с polling
    print("\n=== Пакетная обработка ===")
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
    
    job_id, error = client.batch_generate(
        cars_data=cars_data,
        languages=["en", "de", "fr"],
        webhook_url="https://your-app.com/webhooks/generation-complete"
    )
    
    if job_id:
        print(f"Batch job created: {job_id}")
        
        # Progress callback функция
        def progress_callback(status_data):
            progress = status_data['progress']
            print(f"Progress: {progress['completion_percentage']:.1f}% "
                  f"({progress['processed_lots']}/{progress['total_lots']} lots)")
        
        # Polling для результатов
        results, error = client.poll_for_completion(
            job_id=job_id,
            poll_interval=30,
            progress_callback=progress_callback
        )
        
        if results:
            print("Batch processing completed!")
            print(f"Processed {results['processing_summary']['processed_lots']} lots")
            
            # Скачивание результатов
            success, message = client.download_results(job_id)
            print(f"Download: {message}")
        else:
            print(f"Error: {error}")
    else:
        print(f"Error creating batch job: {error}")

if __name__ == "__main__":
    main()
```

### Node.js/JavaScript интеграция

```javascript
const crypto = require('crypto');
const fetch = require('node-fetch');

class GenerationServiceClient {
    constructor(baseUrl, sharedKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.sharedKey = sharedKey;
    }

    generateSignature(data) {
        const normalized = typeof data === 'object' 
            ? JSON.stringify(data.lots, Object.keys(data.lots).sort())
            : String(data);
        
        const signature = crypto
            .createHmac('sha256', this.sharedKey)
            .update(normalized)
            .digest('hex');
        
        return `sha256=${signature}`;
    }

    async syncGenerate(lotId, additionalInfo, imageUrls, languages = ['en']) {
        const lots = [{
            lot_id: lotId,
            additional_info: additionalInfo,
            images: imageUrls.map(url => ({url}))
        }];

        const payload = {
            signature: this.generateSignature({lots}),
            version: '1.0.0',
            languages,
            lots
        };

        const response = await fetch(`${this.baseUrl}/api/v1/generate-descriptions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'GenerationServiceClient-JS/1.0'
            },
            body: JSON.stringify(payload),
            timeout: 300000 // 5 minutes
        });

        return {
            data: await response.json(),
            status: response.status
        };
    }

    async batchGenerate(carsData, languages = ['en'], webhookUrl = null) {
        const lots = carsData.map(car => {
            const lot = {
                lot_id: car.lotId,
                additional_info: car.additionalInfo,
                images: car.imageUrls.map(url => ({url}))
            };
            if (webhookUrl) {
                lot.webhook = webhookUrl;
            }
            return lot;
        });

        const payload = {
            signature: this.generateSignature({lots}),
            version: '1.0.0',
            languages,
            lots
        };

        const response = await fetch(`${this.baseUrl}/api/v1/generate-descriptions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'GenerationServiceClient-JS/1.0'
            },
            body: JSON.stringify(payload)
        });

        if (response.status === 201) {
            const data = await response.json();
            return {jobId: data.job_id, error: null};
        } else {
            return {jobId: null, error: await response.text()};
        }
    }

    async getJobStatus(jobId) {
        const signature = this.generateSignature(jobId);
        
        const response = await fetch(`${this.baseUrl}/api/v1/batch-status/${jobId}`, {
            headers: {
                'Content-Type': 'application/json',
                'X-Signature': signature
            }
        });

        if (response.ok) {
            return {data: await response.json(), error: null};
        } else {
            return {data: null, error: await response.text()};
        }
    }

    async pollForCompletion(jobId, pollInterval = 30000, maxWaitTime = 3600000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitTime) {
            const {data: statusData, error} = await this.getJobStatus(jobId);
            
            if (error) {
                return {data: null, error};
            }

            console.log(`Job ${jobId} status: ${statusData.status} - ${statusData.progress.completion_percentage}% complete`);

            if (statusData.status === 'completed') {
                return await this.getJobResults(jobId);
            } else if (['failed', 'cancelled'].includes(statusData.status)) {
                return {data: null, error: `Job ${statusData.status}: ${statusData.error_message || 'Unknown error'}`};
            }

            await new Promise(resolve => setTimeout(resolve, pollInterval));
        }

        return {data: null, error: `Timeout after ${maxWaitTime}ms`};
    }
}

// Пример использования
async function main() {
    const client = new GenerationServiceClient('http://localhost:5000', 'your-shared-key');
    
    // Синхронная обработка
    console.log('=== Синхронная обработка ===');
    const syncResult = await client.syncGenerate(
        'js-sync-001',
        '2020 Honda Civic, side collision damage',
        ['https://example.com/honda1.jpg', 'https://example.com/honda2.jpg'],
        ['en', 'fr']
    );
    
    if (syncResult.status === 200) {
        console.log('Sync processing completed!');
        console.log(`Generated descriptions for ${syncResult.data.lots[0].lot_id}`);
    }
    
    // Пакетная обработка
    console.log('\n=== Пакетная обработка ===');
    const carsData = [
        {
            lotId: 'js-batch-001',
            additionalInfo: 'Ford F-150 assessment',
            imageUrls: ['https://example.com/ford1.jpg']
        }
    ];
    
    const {jobId, error} = await client.batchGenerate(
        carsData,
        ['en', 'es'],
        'https://your-app.com/webhooks/complete'
    );
    
    if (jobId) {
        console.log(`Batch job created: ${jobId}`);
        
        const {data: results, error: pollError} = await client.pollForCompletion(jobId);
        
        if (results) {
            console.log('Batch processing completed!');
            console.log(`Processed ${results.processing_summary.processed_lots} lots`);
        } else {
            console.error(`Polling error: ${pollError}`);
        }
    } else {
        console.error(`Batch creation error: ${error}`);
    }
}

main().catch(console.error);
```

## ⚙️ Production Development 

### Системные требования

- **Runtime**: Python 3.8+
- **Database**: PostgreSQL 12+
- **Memory**: 2GB+ RAM для production
- **Storage**: 10GB+ для логов и временных файлов
- **Network**: HTTPS endpoints для webhook доставки

### Environment переменные

```bash
# Обязательные
export DATABASE_URL="postgresql://user:password@host:5432/generation_service"
export OPENAI_API_KEY="sk-your-openai-api-key-here"
export SHARED_KEY="your-secret-hmac-key-minimum-32-characters-long"

# Опциональные
export SESSION_SECRET="your-flask-session-secret-key"
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
export MAX_BATCH_SIZE="50000"  # Максимальный размер batch
export WEBHOOK_TIMEOUT="30"  # Timeout для webhook доставки в секундах
export WEBHOOK_MAX_RETRIES="5"  # Максимальное количество retry попыток
export WORKER_POLL_INTERVAL="30"  # Интервал опроса Background Worker в секундах

# OpenAI настройки
export OPENAI_MODEL_VISION="o1-mini"  # Модель для vision анализа
export OPENAI_MODEL_TRANSLATION="gpt-4.1-mini"  # Модель для перевода
export OPENAI_MAX_TOKENS="4000"  # Максимальное количество токенов
export OPENAI_TEMPERATURE="0.1"  # Temperature для генерации
```

### Docker deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Копирование приложения
COPY . .

# Создание non-root пользователя
RUN useradd -m -u 1000 genservice && chown -R genservice:genservice /app
USER genservice

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Команда запуска
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "300", "main:app"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://genservice:password@db:5432/generation_service
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      SHARED_KEY: ${SHARED_KEY}
      LOG_LEVEL: INFO
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: generation_service
      POSTGRES_USER: genservice
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

### nginx.conf для Load Balancing

```nginx
upstream generation_service {
    server app:5000;
    # Дополнительные серверы для масштабирования
    # server app2:5000;
    # server app3:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # API endpoints
    location /api/ {
        proxy_pass http://generation_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts для long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Body size для больших batch requests
        client_max_body_size 100M;
    }
    
    # Web interface
    location / {
        proxy_pass http://generation_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Мониторинг и логирование

```python
# monitoring.py - Пример мониторинга системы
import psutil
import logging
from datetime import datetime, timedelta
from database.models import BatchJob, WebhookDelivery
from app import db

def system_health_check():
    """Проверка здоровья системы"""
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        "database": check_database_health(),
        "background_worker": check_worker_health(),
        "openai": check_openai_health()
    }
    
    return health_data

def check_database_health():
    """Проверка состояния базы данных"""
    try:
        # Проверка соединения
        db.session.execute('SELECT 1')
        
        # Статистика заданий за последние 24 часа
        last_24h = datetime.utcnow() - timedelta(hours=24)
        jobs_count = BatchJob.query.filter(BatchJob.created_at >= last_24h).count()
        
        # Статистика webhook доставок
        webhook_stats = db.session.query(
            WebhookDelivery.status,
            db.func.count(WebhookDelivery.id)
        ).filter(
            WebhookDelivery.created_at >= last_24h
        ).group_by(WebhookDelivery.status).all()
        
        return {
            "status": "healthy",
            "jobs_24h": jobs_count,
            "webhook_deliveries": dict(webhook_stats)
        }
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

def check_worker_health():
    """Проверка Background Worker"""
    # Проверка наличия активных worker процессов
    # Проверка последней активности worker
    return {"status": "healthy", "last_activity": "2025-08-05T08:30:00Z"}

def check_openai_health():
    """Проверка доступности OpenAI API"""
    # Тестовый запрос к OpenAI API
    return {"status": "healthy", "response_time_ms": 150}
```

## 📊 Ограничения и коды ошибок

### Ограничения системы

| Параметр | Синхронный режим | Пакетный режим | Polling API |
|----------|------------------|----------------|-------------|
| Максимальное количество изображений на автомобиль | 20 | Без ограничений | N/A |
| Максимальное количество автомобилей на запрос | 1 | 50,000 | N/A |
| Максимальный размер изображения | 10 MB | 10 MB | N/A |
| Максимальный размер batch файла | N/A | 200 MB | N/A |
| Максимальное время ответа | 300 секунд | 24 часа | 5 секунд |
| Максимальное количество языков | 10 | 10 | N/A |
| Rate limiting | 100 req/min | 10 req/min | 1000 req/min |

### HTTP коды ошибок

| Код | Название | Описание | Частые причины |
|-----|----------|----------|----------------|
| **200** | OK | Синхронная обработка успешно завершена | Single car processed successfully |
| **201** | Created | Пакетное задание создано и принято | Batch job successfully queued |
| **202** | Accepted | Задание в процессе обработки | Job still processing, results not ready |
| **400** | Bad Request | Некорректный запрос | Invalid JSON, missing required fields, limits exceeded |
| **401** | Unauthorized | Отсутствует аутентификация | Missing X-Signature header |
| **403** | Forbidden | Неверная подпись | Invalid HMAC signature, wrong shared key |
| **404** | Not Found | Ресурс не найден | Job ID not found, endpoint doesn't exist |
| **409** | Conflict | Конфликт состояния | Job already cancelled, duplicate lot_id |
| **413** | Payload Too Large | Слишком большой запрос | Batch size exceeds limits, images too large |
| **422** | Unprocessable Entity | Некорректные данные | Invalid image URLs, unsupported language codes |
| **429** | Too Many Requests | Превышен rate limit | Too many requests per minute |
| **500** | Internal Server Error | Внутренняя ошибка сервера | OpenAI API failure, database connection error |
| **502** | Bad Gateway | Ошибка внешнего сервиса | OpenAI API unavailable |
| **503** | Service Unavailable | Сервис временно недоступен | Database maintenance, high load |
| **504** | Gateway Timeout | Таймаут внешнего сервиса | OpenAI API timeout |

### Примеры ошибок

```json
// 400 Bad Request - Invalid JSON
{
  "error": "Invalid request format",
  "message": "Request body must be valid JSON",
  "code": "INVALID_JSON"
}

// 403 Forbidden - Invalid signature
{
  "error": "Authentication failed",
  "message": "Invalid HMAC signature",
  "code": "INVALID_SIGNATURE"
}

// 413 Payload Too Large - Batch size exceeded
{
  "error": "Request too large",
  "message": "Batch size exceeds maximum limit of 50,000 lots",
  "code": "BATCH_SIZE_EXCEEDED",
  "details": {
    "provided_lots": 75000,
    "max_allowed": 50000
  }
}

// 422 Unprocessable Entity - Invalid image URL
{
  "error": "Validation failed",
  "message": "Invalid image URLs detected",
  "code": "INVALID_IMAGE_URLS",
  "details": {
    "invalid_urls": [
      "https://invalid-domain.com/image.jpg",
      "ftp://example.com/car.jpg"
    ]
  }
}

// 500 Internal Server Error - OpenAI API failure
{
  "error": "External service error",
  "message": "OpenAI API request failed",
  "code": "OPENAI_API_ERROR",
  "details": {
    "openai_error": "Model overloaded",
    "retry_after": 60
  }
}
```

## 🔧 Troubleshooting

### Частые проблемы и решения

#### 1. Проблемы с подписью HMAC

**Проблема**: HTTP 403 Forbidden
**Решение**:
```python
# Убедитесь в корректной нормализации JSON
import json
lots_normalized = json.dumps(lots, separators=(',', ':'), sort_keys=True)

# Проверьте shared_key
shared_key = "exactly-the-same-key-on-both-sides"

# Для polling requests используйте job_id как строку
signature = hmac.new(shared_key.encode(), job_id.encode(), hashlib.sha256).hexdigest()
```

#### 2. Таймауты при синхронной обработке

**Проблема**: HTTP 504 Gateway Timeout
**Решение**:
- Уменьшите количество изображений (≤10 рекомендуется)
- Оптимизируйте размер изображений (≤5MB)
- Используйте пакетный режим для больших заданий

#### 3. Проблемы с webhook доставкой

**Проблема**: Webhook не доставляются
**Решение**:
```python
# Проверьте webhook endpoint
def webhook_handler(request):
    # Возвращайте HTTP 200/201/202 для успешной доставки
    return {"status": "received"}, 200

# Проверьте доступность URL
curl -X POST https://your-app.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'
```

#### 4. Превышение лимитов

**Проблема**: HTTP 413 Payload Too Large
**Решение**:
- Разделите большие batch на несколько меньших
- Оптимизируйте размер изображений
- Используйте compression для изображений

### Логи и диагностика

```bash
# Проверка логов приложения
tail -f logs/generation_service.log

# Проверка статуса Background Worker
grep "Background worker" logs/generation_service.log

# Проверка webhook доставок
grep "webhook_delivery" logs/generation_service.log

# Мониторинг базы данных
psql $DATABASE_URL -c "
SELECT 
  status, 
  COUNT(*) as count,
  AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_seconds
FROM batch_jobs 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY status;
"
```

---

## 📞 Поддержка и обратная связь

**Generation Service API v2.0** - Production-ready микросервис для AI-powered генерации описаний автомобилей

- **Документация**: Актуальная версия всегда доступна в веб-интерфейсе
- **GitHub**: Исходный код и issues
- **Статус системы**: Мониторинг через `/health` endpoint
- **Архитектура**: PostgreSQL + Background Worker + Polling API + Webhook система

**Основные улучшения v2.0:**
- ✅ Полная PostgreSQL интеграция для production deployment
- ✅ Background Worker система для надежной webhook доставки
- ✅ Comprehensive Polling API для real-time мониторинга
- ✅ Автоматические retry механизмы с exponential backoff
- ✅ Production-ready архитектура с Load Balancing поддержкой

---

*Документация обновлена: 5 августа 2025 года*