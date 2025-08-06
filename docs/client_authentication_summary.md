# 🚀 Аутентификация для клиентов - Полное руководство

## ❓ Вопрос: Как клиенту получить подпись?

### 🎯 Ответ: Клиент ГЕНЕРИРУЕТ подпись, не получает ее!

## 🔧 Алгоритм для клиента:

### 1️⃣ Имейте секретный ключ
```
SHARED_KEY = "your-secret-key"  # Тот же, что на сервере
```

### 2️⃣ Генерируйте подпись для каждого запроса
```python
import hmac, hashlib

def generate_signature(payload, shared_key):
    return hmac.new(
        shared_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```

### 3️⃣ Отправляйте с заголовком
```python
headers = {"X-Signature": signature}
```

## 📋 Примеры:

### GET запрос:
```python
payload = ""  # Пустой для GET
signature = generate_signature("", SHARED_KEY)
# Результат: "f243e50f793cb97f46092f9d08328cf9c0a31d2eb77a785a8e629d11390a4841"
```

### POST запрос:
```python
payload = '{"lots":[{"lot_id":"test"}]}'
signature = generate_signature(payload, SHARED_KEY)
# Результат: другая подпись для другого payload
```

## ⚠️ Важно:
- **Каждый запрос = новая подпись**
- **Точный JSON формат** для POST
- **Одинаковый SHARED_KEY** на клиенте и сервере

## 🎯 Готовые решения:

### Простой способ (без подписей):
```python
# Для polling - аутентификация НЕ нужна
response = requests.get(f"/api/v1/jobs/{job_id}/status")
```

### С подписями:
```python
# Используйте examples/simple_signature_example.py
```

## 🔑 Тестирование:
```bash
# Инструмент для тестирования подписей:
python3 tools/signature_helper.py "/api/v1/batch-status/JOB_ID"
```

---

**Главный принцип:** Клиент не получает подпись, а рассчитывает ее сам по алгоритму HMAC-SHA256!