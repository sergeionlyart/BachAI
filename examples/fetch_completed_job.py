#!/usr/bin/env python3
"""
Простой скрипт для получения результатов завершенной задачи
"""
import requests
import json
import hmac
import hashlib

# Конфигурация
BASE_URL = "https://bach-ai-info3819.replit.app"
SHARED_KEY = "dev-secret-key-for-testing-2024"

def generate_signature(payload=""):
    """Генерирует подпись для GET запроса"""
    return hmac.new(
        SHARED_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

def fetch_job_results(job_id):
    """Получает полные результаты задачи"""
    signature = generate_signature()  # Пустой payload для GET
    headers = {"X-Signature": signature}
    
    url = f"{BASE_URL}/api/v1/jobs/{job_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None

def main():
    # Замените на ваш job_id из ответа completed задачи
    job_id = "365a09ce-5416-49b5-8471-d6aad042761c"
    
    print(f"Получение результатов для задачи: {job_id}")
    
    results = fetch_job_results(job_id)
    
    if results:
        print(f"\nСтатус: {results['status']}")
        print(f"Обработано лотов: {results['processed_lots']}")
        print(f"Неудачных лотов: {results['failed_lots']}")
        
        print("\nРезультаты:")
        for i, lot in enumerate(results['results'][:5]):  # Показываем первые 5
            print(f"{i+1}. Лот {lot['lot_id']}: {lot['vision_result']}")
        
        if len(results['results']) > 5:
            print(f"... и еще {len(results['results']) - 5} лотов")

if __name__ == "__main__":
    main()