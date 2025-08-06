# Пошаговое руководство для клиентов

## 🎯 Главное правило
**Каждый запрос = своя подпись!** Никогда не используйте одну подпись для разных запросов.

## 🔧 Шаги для клиента:

### Шаг 1: Получите SHARED_KEY
У вас должен быть тот же секретный ключ, что и на сервере.

### Шаг 2: Для каждого запроса генерируйте подпись
```python
import hmac
import hashlib

def generate_signature(payload: str, shared_key: str) -> str:
    return hmac.new(
        shared_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```

### Шаг 3: Отправляйте с заголовком X-Signature
```python
headers = {"X-Signature": signature}
requests.get(url, headers=headers)
```

## 📋 Примеры подписей для разных запросов:

### GET запрос (пустой payload):
```
Payload: ""
Подпись: f243e50f793cb97f46092f9d08328cf9c0a31d2eb77a785a8e629d11390a4841
```

### POST запрос с данными:
```
Payload: {"lots":[{"lot_id":"test123"}]}
Подпись: c22572dcdec79b8ecf7e3596c6f47bc23388de5355d7eb75cd9c607ad42d5b48
```

## 💡 Простой способ: Используйте endpoints БЕЗ аутентификации

Для polling клиентов рекомендуется:
```
GET /api/v1/jobs/{job_id}/status  ✅ Без подписи!
```

Вместо:
```
GET /api/v1/batch-status/{job_id}  ❌ Требует подпись
```

## ⚠️ Частые ошибки:

1. **Использование одной подпись для всех запросов** - НЕПРАВИЛЬНО!
2. **Неправильный payload** - учитывайте точный JSON формат
3. **Неправильный SHARED_KEY** - должен совпадать с сервером

## ✅ Готовый клиент:
Используйте `examples/simple_client.py` - там все правильно настроено!