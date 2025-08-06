#!/usr/bin/env python3
"""
Инструмент для генерации HMAC-SHA256 подписей для API запросов
"""
import os
import sys
import json
import hmac
import hashlib
import requests

def generate_signature(payload: str, shared_key: str) -> str:
    """Генерирует HMAC-SHA256 подпись для payload"""
    return hmac.new(
        shared_key.encode(),
        payload.encode() if isinstance(payload, str) else payload,
        hashlib.sha256
    ).hexdigest()

def test_signature_auth(endpoint: str, payload_data: dict = None):
    """Тестирует аутентификацию с подписью"""
    shared_key = os.environ.get("SHARED_KEY")
    if not shared_key:
        print("❌ SHARED_KEY не найден в переменных окружения")
        return False
    
    # Подготавливаем payload
    if payload_data:
        payload = json.dumps(payload_data, separators=(',', ':'))
    else:
        payload = ""
    
    # Генерируем подпись
    signature = generate_signature(payload, shared_key)
    
    # Отправляем запрос
    headers = {
        'Content-Type': 'application/json',
        'X-Signature': signature
    }
    
    print(f"🔑 Генерируем подпись для: {endpoint}")
    print(f"📝 Payload: {payload}")
    print(f"🔐 Подпись: {signature}")
    print(f"📤 Отправляем запрос...")
    
    try:
        if payload_data:
            response = requests.post(f"http://localhost:5000{endpoint}", 
                                   data=payload, headers=headers)
        else:
            response = requests.get(f"http://localhost:5000{endpoint}", 
                                  headers=headers)
        
        print(f"📥 Ответ: {response.status_code}")
        if response.text:
            try:
                formatted = json.dumps(response.json(), indent=2, ensure_ascii=False)
                print(f"💬 Содержимое:\n{formatted}")
            except:
                print(f"💬 Содержимое: {response.text}")
        
        return response.status_code < 400
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False

def main():
    print("🔐 Тестирование HMAC аутентификации")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python signature_helper.py <endpoint> [payload.json]")
        print("Примеры:")
        print("  python signature_helper.py /api/v1/batch-status/365a09ce-5416-49b5-8471-d6aad042761c")
        print("  python signature_helper.py /api/generate")
        return
    
    endpoint = sys.argv[1]
    payload_data = None
    
    # Загружаем payload из файла или используем тестовые данные
    if len(sys.argv) > 2:
        try:
            with open(sys.argv[2], 'r') as f:
                payload_data = json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки payload: {e}")
            return
    
    # Тестируем аутентификацию
    success = test_signature_auth(endpoint, payload_data)
    
    if success:
        print("\n✅ Аутентификация успешна!")
    else:
        print("\n❌ Ошибка аутентификации")
    
    print("\n📋 Пример команды curl:")
    shared_key = os.environ.get("SHARED_KEY", "YOUR_SHARED_KEY")
    if payload_data:
        payload_str = json.dumps(payload_data, separators=(',', ':'))
        signature = generate_signature(payload_str, shared_key)
        print(f'curl -X POST "http://localhost:5000{endpoint}" \\')
        print(f'  -H "Content-Type: application/json" \\')
        print(f'  -H "X-Signature: {signature}" \\')
        print(f"  -d '{payload_str}'")
    else:
        signature = generate_signature("", shared_key)
        print(f'curl -X GET "http://localhost:5000{endpoint}" \\')
        print(f'  -H "X-Signature: {signature}"')

if __name__ == "__main__":
    main()