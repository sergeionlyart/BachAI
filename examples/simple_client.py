#!/usr/bin/env python3
"""
Простой пример клиента с правильной генерацией подписей
"""
import os
import hmac
import hashlib
import requests
import json

class ApiClient:
    def __init__(self, base_url: str, shared_key: str):
        self.base_url = base_url
        self.shared_key = shared_key
    
    def _generate_signature(self, payload: str) -> str:
        """Генерирует подпись для запроса"""
        return hmac.new(
            self.shared_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def get_job_status(self, job_id: str):
        """Получает статус задачи (с аутентификацией)"""
        endpoint = f"/api/v1/batch-status/{job_id}"
        payload = ""  # GET запрос - пустой payload
        
        signature = self._generate_signature(payload)
        headers = {"X-Signature": signature}
        
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
        return response.json()
    
    def get_job_results(self, job_id: str):
        """Получает полные результаты задачи"""
        endpoint = f"/api/v1/jobs/{job_id}"
        payload = ""
        
        signature = self._generate_signature(payload)
        headers = {"X-Signature": signature}
        
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
        return response.json()
    
    def get_simple_status(self, job_id: str):
        """Простой статус БЕЗ аутентификации (для polling)"""
        endpoint = f"/api/v1/jobs/{job_id}/status"
        
        # Без заголовков - аутентификация не нужна
        response = requests.get(f"{self.base_url}{endpoint}")
        return response.json()

# Пример использования:
if __name__ == "__main__":
    # Ваши настройки
    BASE_URL = "http://localhost:5000"
    SHARED_KEY = "your-shared-key-here"  # Замените на ваш ключ
    JOB_ID = "365a09ce-5416-49b5-8471-d6aad042761c"
    
    client = ApiClient(BASE_URL, SHARED_KEY)
    
    print("🔐 С аутентификацией:")
    status = client.get_job_status(JOB_ID)
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    print("\n📱 Без аутентификации (polling):")
    simple_status = client.get_simple_status(JOB_ID)
    print(json.dumps(simple_status, indent=2, ensure_ascii=False))