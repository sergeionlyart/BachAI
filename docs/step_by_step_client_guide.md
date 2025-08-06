# 🔐 Пошаговое руководство: Как клиенту получить подпись

## Шаг 1: Получите секретный ключ (SHARED_KEY)

Вам нужен тот же секретный ключ, который настроен на сервере.
```python
SHARED_KEY = "your-secret-key"  # Получите от администратора сервера
```

## Шаг 2: Установите зависимости

```bash
pip install requests
```

## Шаг 3: Создайте функцию генерации подписи

```python
import hmac
import hashlib

def generate_signature(payload: str, shared_key: str) -> str:
    """
    Генерирует HMAC-SHA256 подпись для запроса
    
    Args:
        payload: Данные запроса (для GET - пустая строка, для POST - JSON)
        shared_key: Секретный ключ
    
    Returns:
        str: HEX-строка подписи
    """
    return hmac.new(
        shared_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```

## Шаг 4: Примеры использования

### 🔍 GET запрос (проверка статуса)

```python
import requests

# Данные для запроса
job_id = "365a09ce-5416-49b5-8471-d6aad042761c"
endpoint = f"/api/v1/batch-status/{job_id}"
payload = ""  # GET запросы имеют пустой payload

# Генерируем подпись
signature = generate_signature(payload, SHARED_KEY)

# Отправляем запрос
headers = {"X-Signature": signature}
response = requests.get(f"http://localhost:5000{endpoint}", headers=headers)

print("Статус:", response.status_code)
print("Ответ:", response.json())
```

### 📤 POST запрос (создание задачи)

```python
import json

# Данные для запроса
data = {
    "lots": [
        {
            "lot_id": "test-123",
            "images": ["http://example.com/car.jpg"]
        }
    ],
    "languages": ["en", "ru"]
}

# Конвертируем в JSON (важно: без пробелов!)
payload = json.dumps(data, separators=(',', ':'))

# Генерируем подпись
signature = generate_signature(payload, SHARED_KEY)

# Отправляем запрос
headers = {
    "Content-Type": "application/json",
    "X-Signature": signature
}

response = requests.post(
    "http://localhost:5000/api/v1/generate",
    data=payload,  # Отправляем как строку
    headers=headers
)
```

## Шаг 5: Готовый класс клиента

```python
class CarDescriptionClient:
    def __init__(self, base_url: str, shared_key: str):
        self.base_url = base_url
        self.shared_key = shared_key
    
    def _sign_request(self, payload: str) -> str:
        """Генерирует подпись для запроса"""
        return hmac.new(
            self.shared_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def get_job_status(self, job_id: str):
        """Получить статус задачи"""
        endpoint = f"/api/v1/batch-status/{job_id}"
        signature = self._sign_request("")
        headers = {"X-Signature": signature}
        
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
        return response.json()
    
    def create_job(self, lots: list, languages: list):
        """Создать задачу генерации описаний"""
        data = {"lots": lots, "languages": languages}
        payload = json.dumps(data, separators=(',', ':'))
        
        signature = self._sign_request(payload)
        headers = {
            "Content-Type": "application/json",
            "X-Signature": signature
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/generate",
            data=payload,
            headers=headers
        )
        return response.json()

# Использование:
client = CarDescriptionClient("http://localhost:5000", "your-secret-key")

# Создать задачу
lots = [{"lot_id": "car-123", "images": ["http://example.com/car.jpg"]}]
job = client.create_job(lots, ["en", "ru"])

# Проверить статус
status = client.get_job_status(job["job_id"])
```

## 🎯 Важные моменты:

1. **Каждый запрос = новая подпись**
2. **Точный JSON формат** (без пробелов): `{"key":"value"}`
3. **Правильный Content-Type** для POST запросов
4. **Одинаковый SHARED_KEY** на клиенте и сервере

## 🚀 Простой способ: Без аутентификации

Для простого polling используйте endpoint без аутентификации:

```python
# Никаких подписей не нужно!
response = requests.get(f"http://localhost:5000/api/v1/jobs/{job_id}/status")
status = response.json()
```

## 🔧 Тестирование подписей

Используйте готовый инструмент для проверки:

```bash
python3 tools/signature_helper.py "/api/v1/batch-status/your-job-id"
```