#!/usr/bin/env python3
"""
Проверяет настроенный SHARED_KEY и генерирует тестовую подпись
"""
import os
import hmac
import hashlib

def check_server_shared_key():
    """Проверяет настройки SHARED_KEY на сервере"""
    shared_key = os.environ.get('SHARED_KEY')
    
    if not shared_key:
        print("❌ SHARED_KEY не установлен в переменных окружения")
        return None
    
    print("✅ SHARED_KEY установлен")
    print(f"📏 Длина ключа: {len(shared_key)} символов")
    
    # Маскируем ключ для безопасности
    if len(shared_key) > 8:
        masked_key = shared_key[:4] + "..." + shared_key[-4:]
    else:
        masked_key = shared_key[:2] + "..."
    
    print(f"🔒 Маскированный ключ: {masked_key}")
    
    # Генерируем тестовую подпись для пустого payload
    test_signature = hmac.new(
        shared_key.encode(),
        "".encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"🔐 Тестовая подпись для GET запроса: {test_signature}")
    
    return shared_key

def generate_signature_for_client(shared_key, payload=""):
    """Генерирует подпись для клиента"""
    if not shared_key:
        return None
        
    return hmac.new(
        shared_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

if __name__ == "__main__":
    print("🔍 Проверка настроек сервера")
    print("=" * 40)
    
    key = check_server_shared_key()
    
    if key:
        print("\n📋 Для клиентов:")
        print("- Используйте тот же SHARED_KEY, что установлен на сервере")
        print("- Для GET запросов используйте пустой payload ('')")
        print("- Для POST запросов используйте JSON строку как payload")
        
        print(f"\n🌐 Пример curl для проверки статуса:")
        signature = generate_signature_for_client(key, "")
        print(f"curl -H 'X-Signature: {signature}' http://localhost:5000/api/v1/batch-status/JOB_ID")
    else:
        print("\n❌ Необходимо установить SHARED_KEY в переменные окружения")