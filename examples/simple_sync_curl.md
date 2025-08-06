# Простой curl пример для синхронного анализа

## Быстрый запрос (готовая подпись)

```bash
curl -X POST "https://bach-ai-info3819.replit.app/api/v1/generate-descriptions" \
  -H "Content-Type: application/json" \
  -H "User-Agent: CurlExample/1.0" \
  -d '{
    "signature": "sha256=7c5c3ffc9d0b8e2a1234567890abcdef1234567890abcdef1234567890abcdef",
    "version": "1.0.0",
    "languages": ["en", "ru"],
    "lots": [
      {
        "lot_id": "demo-sync-12345",
        "additional_info": "2020 BMW X3, minor front damage, parking incident",
        "images": [
          {"url": "https://images.unsplash.com/photo-1549399811-9b0c893bd7c1?w=800"},
          {"url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"}
        ]
      }
    ]
  }' \
  --max-time 300
```

**⚠️ Важно:** Подпись выше НЕ валидна! Для рабочего запроса используйте генератор подписи.

## Генерация правильной подписи

### Шаг 1: Подготовьте данные
```json
{
  "lot_id": "demo-sync-12345",
  "additional_info": "2020 BMW X3, minor front damage, parking incident", 
  "images": [
    {"url": "https://images.unsplash.com/photo-1549399811-9b0c893bd7c1?w=800"},
    {"url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"}
  ]
}
```

### Шаг 2: Сгенерируйте подпись
```python
import hmac
import hashlib
import json

# Ваши данные
lots_data = [{
    "lot_id": "demo-sync-12345",
    "additional_info": "2020 BMW X3, minor front damage, parking incident",
    "images": [
        {"url": "https://images.unsplash.com/photo-1549399811-9b0c893bd7c1?w=800"},
        {"url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"}
    ]
}]

# Ключ для разработки
shared_key = "dev-secret-key-for-testing-2024"

# Нормализация для подписи
normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)

# Генерация подписи
signature = hmac.new(
    shared_key.encode(),
    normalized.encode(),
    hashlib.sha256
).hexdigest()

print(f"sha256={signature}")
```

### Шаг 3: Используйте в curl
```bash
# Замените YOUR_SIGNATURE_HERE на результат из шага 2
curl -X POST "https://bach-ai-info3819.replit.app/api/v1/generate-descriptions" \
  -H "Content-Type: application/json" \
  -H "User-Agent: CurlExample/1.0" \
  -d '{
    "signature": "sha256=YOUR_SIGNATURE_HERE",
    "version": "1.0.0", 
    "languages": ["en", "ru"],
    "lots": [
      {
        "lot_id": "demo-sync-12345",
        "additional_info": "2020 BMW X3, minor front damage, parking incident",
        "images": [
          {"url": "https://images.unsplash.com/photo-1549399811-9b0c893bd7c1?w=800"},
          {"url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"}
        ]
      }
    ]
  }'
```

## Ожидаемый ответ (200 OK)

```json
{
  "version": "1.0.0",
  "processing_mode": "synchronous",
  "total_lots": 1,
  "processed_at": "2025-08-06T07:30:15Z",
  "lots": [
    {
      "lot_id": "demo-sync-12345",
      "status": "completed",
      "processed_images": 2,
      "descriptions": [
        {
          "language": "en",
          "damages": "Detailed professional automotive damage assessment..."
        },
        {
          "language": "ru", 
          "damages": "Детальная оценка повреждений автомобиля..."
        }
      ],
      "missing_images": []
    }
  ],
  "warnings": [],
  "pending_languages": []
}
```

## Автоматический скрипт

Для удобства используйте готовый скрипт:
```bash
./examples/sync_curl_example.sh
```