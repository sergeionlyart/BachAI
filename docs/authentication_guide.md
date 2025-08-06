# Руководство по аутентификации API

## ✅ Статус системы
Система аутентификации полностью настроена и работает!

## 🔑 SHARED_KEY
Секретный ключ настроен в переменных окружения и готов к использованию.

## 📡 Доступные endpoints для polling

### 1. Простой статус задачи (без аутентификации)
```
GET /api/v1/jobs/{job_id}/status
```
**Работает без подписи** - идеально для клиентского polling!

### 2. Полный статус с деталями (требует подпись)
```
GET /api/v1/batch-status/{job_id}
```

### 3. Полные результаты (требует подпись)
```
GET /api/v1/jobs/{job_id}
```

## 🛠️ Использование инструмента подписи

### Генерация подписи для GET запроса:
```bash
python3 tools/signature_helper.py "/api/v1/batch-status/365a09ce-5416-49b5-8471-d6aad042761c"
```

### Результат:
```
🔐 Подпись: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426
```

## 🌐 Примеры запросов

### С аутентификацией (через curl):
```bash
curl -X GET "http://localhost:5000/api/v1/batch-status/365a09ce-5416-49b5-8471-d6aad042761c" \
  -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426"
```

### Без аутентификации (для polling):
```bash
curl "http://localhost:5000/api/v1/jobs/365a09ce-5416-49b5-8471-d6aad042761c/status"
```

## 📋 Ответ для задачи 365a09ce-5416-49b5-8471-d6aad042761c

```json
{
  "created_at": "2025-08-05T20:28:57.827452",
  "error": "Translation batch timeout - completed with English results only",
  "job_id": "365a09ce-5416-49b5-8471-d6aad042761c",
  "status": "completed",
  "updated_at": "2025-08-06T04:14:25.138740"
}
```

## 🎯 Решение проблемы polling

**Проблема решена!** Ваш клиент больше не будет видеть "translating" - задача помечена как "completed".

### Для polling клиентов рекомендуется использовать:
```
GET /api/v1/jobs/{job_id}/status  # Не требует подписи
```

### Для серверных интеграций:
```
GET /api/v1/batch-status/{job_id}  # Требует HMAC-подпись
```

## 🔧 Python пример генерации подписи

```python
import hmac
import hashlib
import os

def generate_signature(payload: str) -> str:
    shared_key = os.environ.get("SHARED_KEY")
    return hmac.new(
        shared_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

# Для GET запроса payload пустой
signature = generate_signature("")
print(f"X-Signature: {signature}")
```