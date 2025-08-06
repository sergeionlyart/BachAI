# 🚗 Generation Service - Руководство для клиентов

## Обзор

Generation Service предоставляет два режима обработки автомобильных изображений:

- **Синхронный режим** - мгновенные результаты для 1 автомобиля
- **Асинхронный режим** - обработка множества автомобилей через систему Polling

## 🔐 Аутентификация

Все запросы требуют HMAC-SHA256 подпись для безопасности.

### Генерация подписи

```python
import hmac
import hashlib
import json

def generate_signature(lots_data, shared_key):
    """Генерация HMAC-SHA256 подписи"""
    normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)
    signature = hmac.new(
        shared_key.encode(),
        normalized.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature  # БЕЗ префикса "sha256="
```

⚠️ **Важно:** Система ожидает подпись БЕЗ префикса `sha256=`

---

## 📱 Синхронный режим

**Когда использовать:**
- 1 автомобиль
- Нужен мгновенный результат (≤300 секунд)
- До 20 изображений на автомобиль

### Структура запроса

```http
POST /api/v1/generate-descriptions
Content-Type: application/json
```

```json
{
  "signature": "d95badb38ba7e8dd74a47e5d0199da73e88f5e249ffaf87f46dde90e3ab7e743",
  "version": "1.0.0",
  "languages": ["en", "ru", "de"],
  "lots": [
    {
      "lot_id": "car-12345",
      "additional_info": "2021 BMW X5, front damage",
      "images": [
        {"url": "https://example.com/front.jpg"},
        {"url": "https://example.com/side.jpg"}
      ]
    }
  ]
}
```

### Пример ответа

```json
{
  "version": "1.0.0",
  "lots": [
    {
      "lot_id": "car-12345",
      "descriptions": [
        {
          "language": "en",
          "damages": "<p>Front bumper shows significant impact damage...</p>"
        },
        {
          "language": "ru", 
          "damages": "<p>Передний бампер имеет значительные повреждения...</p>"
        },
        {
          "language": "de",
          "damages": "<p>Die vordere Stoßstange zeigt erhebliche Aufprallschäden...</p>"
        }
      ]
    }
  ],
  "warnings": ["processing 3 languages may increase response time"]
}
```

### Полный пример кода (Python)

```python
import requests
import hmac
import hashlib
import json

class GenerationServiceClient:
    def __init__(self, base_url, shared_key):
        self.base_url = base_url
        self.shared_key = shared_key
    
    def generate_signature(self, lots_data):
        normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)
        return hmac.new(
            self.shared_key.encode(),
            normalized.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def sync_generate(self, lot_id, images, additional_info="", languages=["en"]):
        """Синхронная генерация описаний"""
        lots = [{
            "lot_id": lot_id,
            "additional_info": additional_info,
            "images": [{"url": url} for url in images]
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
            timeout=300
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

# Использование
client = GenerationServiceClient(
    base_url="https://your-service.replit.app",
    shared_key="your-shared-key"
)

result = client.sync_generate(
    lot_id="demo-car-123",
    images=[
        "https://example.com/front.jpg",
        "https://example.com/side.jpg"
    ],
    additional_info="2019 Tesla Model 3, minor scratches",
    languages=["en", "ru", "es"]
)

print(f"Описания получены: {len(result['lots'][0]['descriptions'])} языков")
```

---

## 🔄 Асинхронный режим (Polling)

**Когда использовать:**
- 2+ автомобилей
- Большие объемы данных
- Не критично время ответа

### Шаг 1: Создание задания

```http
POST /api/v1/generate-descriptions
```

```json
{
  "signature": "your_signature_here",
  "version": "1.0.0", 
  "languages": ["en", "ru"],
  "lots": [
    {
      "lot_id": "car-001",
      "additional_info": "2020 Toyota Camry",
      "images": [{"url": "https://example.com/car1.jpg"}]
    },
    {
      "lot_id": "car-002", 
      "additional_info": "2021 Honda Civic",
      "images": [{"url": "https://example.com/car2.jpg"}]
    }
  ]
}
```

**Ответ:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "creation_time": "1.23s",
  "lots_count": 2
}
```

### Шаг 2: Проверка статуса (Polling)

```http
GET /api/v1/batch-status/{job_id}
```

**Ответ (в процессе):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-08-06T08:30:00Z",
  "updated_at": "2025-08-06T08:32:15Z", 
  "progress": {
    "total_lots": 2,
    "processed_lots": 1,
    "failed_lots": 0,
    "completion_percentage": 50.0
  },
  "languages": ["en", "ru"]
}
```

### Шаг 3: Получение результатов

```http
GET /api/v1/batch-results/{job_id}
```

**Ответ (завершено):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2025-08-06T08:35:42Z",
  "results": {
    "lots": [
      {
        "lot_id": "car-001",
        "descriptions": [
          {
            "language": "en",
            "damages": "<p>Vehicle appears in good condition...</p>"
          },
          {
            "language": "ru", 
            "damages": "<p>Автомобиль в хорошем состоянии...</p>"
          }
        ]
      },
      {
        "lot_id": "car-002",
        "descriptions": [
          {
            "language": "en",
            "damages": "<p>Minor cosmetic damage visible...</p>"
          },
          {
            "language": "ru",
            "damages": "<p>Видны незначительные косметические повреждения...</p>"
          }
        ]
      }
    ]
  }
}
```

### Полный пример Polling клиента (Python)

```python
import time
import requests
from typing import Dict, List, Optional

class AsyncGenerationClient:
    def __init__(self, base_url: str, shared_key: str):
        self.base_url = base_url
        self.shared_key = shared_key
    
    def generate_signature(self, lots_data: List[Dict]) -> str:
        normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)
        return hmac.new(
            self.shared_key.encode(),
            normalized.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def create_batch_job(self, cars_data: List[Dict], languages: List[str] = ["en"]) -> str:
        """Создание пакетного задания"""
        payload = {
            "signature": self.generate_signature(cars_data),
            "version": "1.0.0",
            "languages": languages,
            "lots": cars_data
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/generate-descriptions",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            return response.json()["job_id"]
        else:
            raise Exception(f"Failed to create job: {response.text}")
    
    def get_job_status(self, job_id: str) -> Dict:
        """Проверка статуса задания"""
        response = requests.get(f"{self.base_url}/api/v1/batch-status/{job_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get status: {response.text}")
    
    def get_results(self, job_id: str) -> Optional[Dict]:
        """Получение результатов (только для завершенных заданий)"""
        response = requests.get(f"{self.base_url}/api/v1/batch-results/{job_id}")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 202:
            return None  # Еще не готово
        else:
            raise Exception(f"Failed to get results: {response.text}")
    
    def wait_for_completion(self, job_id: str, max_wait_time: int = 3600, 
                          poll_interval: int = 30) -> Dict:
        """Ожидание завершения с polling"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.get_job_status(job_id)
            
            print(f"Статус: {status['status']} - {status['progress']['completion_percentage']:.1f}%")
            
            if status["status"] == "completed":
                return self.get_results(job_id)
            elif status["status"] in ["failed", "cancelled"]:
                raise Exception(f"Job {status['status']}: {status.get('error_message', 'Unknown error')}")
            
            time.sleep(poll_interval)
        
        raise Exception(f"Job timeout after {max_wait_time} seconds")

# Использование
client = AsyncGenerationClient(
    base_url="https://your-service.replit.app",
    shared_key="your-shared-key"
)

# Создание задания
cars = [
    {
        "lot_id": "fleet-car-001",
        "additional_info": "2020 BMW X3, company fleet vehicle",
        "images": [{"url": "https://example.com/bmw1.jpg"}]
    },
    {
        "lot_id": "fleet-car-002", 
        "additional_info": "2019 Audi A4, lease return",
        "images": [{"url": "https://example.com/audi1.jpg"}]
    }
]

job_id = client.create_batch_job(cars, languages=["en", "ru", "de"])
print(f"Задание создано: {job_id}")

# Ожидание результатов с автоматическим polling
results = client.wait_for_completion(job_id, max_wait_time=1800, poll_interval=15)
print(f"Обработано {len(results['results']['lots'])} автомобилей")
```

---

## 🛠️ Дополнительные API endpoints

### Скачивание результатов

```http
GET /api/v1/batch-results/{job_id}/download
```

Возвращает JSON файл с результатами для скачивания.

### Список заданий

```http
GET /api/v1/batch-jobs?status=completed&limit=10&offset=0
```

### Отмена задания

```http
POST /api/v1/batch-jobs/{job_id}/cancel
```

---

## 📋 Статусы заданий

| Статус | Описание |
|--------|----------|
| `pending` | Задание принято, ожидает обработки |
| `processing` | Анализ изображений в процессе |
| `translating` | Генерация переводов |
| `completed` | Готово, результаты доступны |
| `failed` | Ошибка обработки |
| `cancelled` | Отменено пользователем |

---

## 🌍 Поддержка языков

Система поддерживает **100+ языков** без ограничений по количеству:

**Популярные коды языков:**
- `en` - English
- `ru` - Русский  
- `de` - Deutsch
- `fr` - Français
- `es` - Español
- `it` - Italiano
- `pt` - Português
- `zh` - 中文
- `ja` - 日本語
- `ko` - 한국어

**Ограничения по времени:**
- **Синхронный режим**: 45 секунд на все переводы, при превышении - английский fallback
- **Асинхронный режим**: без ограничений

---

## ⚡ Рекомендации по производительности

### Синхронный режим
- ≤5 языков для оптимальной производительности
- ≤20 изображений на автомобиль
- Используйте для критичных по времени запросов

### Асинхронный режим  
- Для больших объемов данных (2+ автомобилей)
- Любое количество языков
- Настройте polling интервал 15-30 секунд

### Обработка ошибок
```python
try:
    result = client.sync_generate(lot_id, images, languages=["en", "ru"])
except Exception as e:
    if "timeout" in str(e).lower():
        # Повторить с меньшим количеством языков
        result = client.sync_generate(lot_id, images, languages=["en"])
    else:
        # Обработка других ошибок
        print(f"Ошибка: {e}")
```

---

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте подпись** - самая частая причина ошибок 403
2. **Убедитесь в корректности URL изображений** - система проверяет доступность
3. **Используйте timeout'ы** - особенно для синхронного режима
4. **Логируйте job_id** - для отслеживания асинхронных заданий

**Примеры curl команд для тестирования:**

```bash
# Синхронный запрос
curl -X POST "https://your-service.replit.app/api/v1/generate-descriptions" \
  -H "Content-Type: application/json" \
  -d '{"signature":"your_signature","version":"1.0.0","languages":["en"],"lots":[...]}' \
  --max-time 300

# Проверка статуса
curl "https://your-service.replit.app/api/v1/batch-status/your-job-id"

# Получение результатов  
curl "https://your-service.replit.app/api/v1/batch-results/your-job-id"
```

Система готова к production использованию с полной поддержкой мониторинга, логирования и отказоустойчивости.