#!/usr/bin/env python3
"""
Демонстрация как клиент должен генерировать подписи для каждого запроса
"""
import os
import json
import hmac
import hashlib
import requests

# Ваш секретный ключ (должен быть тот же, что на сервере)
SHARED_KEY = "your-shared-key-here"  # В реальности берется из переменных окружения

def generate_signature(payload: str, shared_key: str) -> str:
    """Генерирует HMAC-SHA256 подпись для payload"""
    return hmac.new(
        shared_key.encode(),
        payload.encode() if isinstance(payload, str) else payload,
        hashlib.sha256
    ).hexdigest()

def make_authenticated_request(endpoint: str, method: str = "GET", data: dict = None):
    """Делает аутентифицированный запрос к API"""
    
    # Подготавливаем payload
    if data:
        payload = json.dumps(data, separators=(',', ':'))
        headers = {'Content-Type': 'application/json'}
    else:
        payload = ""
        headers = {}
    
    # Генерируем подпись для ЭТОГО КОНКРЕТНОГО запроса
    signature = generate_signature(payload, SHARED_KEY)
    headers['X-Signature'] = signature
    
    print(f"🚀 Запрос: {method} {endpoint}")
    print(f"📝 Payload: {payload}")
    print(f"🔐 Подпись: {signature}")
    
    # Отправляем запрос
    url = f"http://localhost:5000{endpoint}"
    if method == "GET":
        response = requests.get(url, headers=headers)
    else:
        response = requests.post(url, data=payload, headers=headers)
    
    print(f"📥 Ответ: {response.status_code}")
    return response

# Примеры разных запросов с разными подписями:

print("=" * 50)
print("ПРИМЕР 1: GET запрос (пустой payload)")
print("=" * 50)
response1 = make_authenticated_request("/api/v1/batch-status/365a09ce-5416-49b5-8471-d6aad042761c")

print("\n" + "=" * 50)
print("ПРИМЕР 2: POST запрос с данными")
print("=" * 50)
test_data = {
    "lots": [
        {"lot_id": "test123", "images": ["http://example.com/car.jpg"]}
    ],
    "languages": ["en", "ru"]
}
response2 = make_authenticated_request("/api/v1/generate", "POST", test_data)

print("\n" + "=" * 50)
print("ПРИМЕР 3: Другой GET запрос")
print("=" * 50)
response3 = make_authenticated_request("/api/v1/jobs/365a09ce-5416-49b5-8471-d6aad042761c")

print("\n🎯 ВАЖНО:")
print("Каждый запрос имеет СВОЮ уникальную подпись!")
print("Нельзя использовать одну подпись для всех запросов!")