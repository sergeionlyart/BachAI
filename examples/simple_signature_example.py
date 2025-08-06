#!/usr/bin/env python3
"""
ПРОСТОЙ ПРИМЕР: Как клиенту получить подпись для API запроса
"""
import hmac
import hashlib
import requests

# ШАГ 1: Ваш секретный ключ (получите от администратора)
SHARED_KEY = "your-shared-key-here"  # Замените на ваш ключ

# ШАГ 2: Функция генерации подписи
def generate_signature(payload, shared_key):
    """Генерирует подпись для запроса"""
    return hmac.new(
        shared_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

# ШАГ 3: Пример GET запроса
def get_job_status(job_id):
    """Получить статус задачи"""
    # Для GET запроса payload пустой
    payload = ""
    
    # Генерируем подпись
    signature = generate_signature(payload, SHARED_KEY)
    
    # Отправляем запрос с подписью
    url = f"http://localhost:5000/api/v1/batch-status/{job_id}"
    headers = {"X-Signature": signature}
    
    response = requests.get(url, headers=headers)
    return response.json()

# ШАГ 4: Пример POST запроса  
def create_job(lots, languages):
    """Создать задачу"""
    import json
    
    # Подготавливаем данные
    data = {
        "lots": lots,
        "languages": languages
    }
    
    # Конвертируем в JSON строку (без пробелов!)
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
    return response.json()

# ДЕМОНСТРАЦИЯ:
if __name__ == "__main__":
    # Тестируем генерацию подписи
    test_payload = ""
    test_signature = generate_signature(test_payload, "demo-key")
    
    print("🔐 ПРИМЕР ГЕНЕРАЦИИ ПОДПИСИ:")
    print(f"Payload: '{test_payload}'")
    print(f"SHARED_KEY: 'demo-key'")
    print(f"Подпись: {test_signature}")
    
    print("\n📋 ЗАГОЛОВКИ ДЛЯ ЗАПРОСА:")
    print(f'X-Signature: {test_signature}')
    
    print("\n🌐 КОМАНДА CURL:")
    print(f'curl -H "X-Signature: {test_signature}" http://localhost:5000/api/v1/batch-status/JOB_ID')