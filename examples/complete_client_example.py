#!/usr/bin/env python3
"""
Полный пример клиента для API генерации описаний автомобилей
"""
import os
import json
import hmac
import hashlib
import requests
import time
from typing import Optional, List, Dict, Any

class CarDescriptionClient:
    """
    Клиент для API генерации описаний автомобилей
    """
    
    def __init__(self, base_url: str, shared_key: str):
        self.base_url = base_url.rstrip('/')
        self.shared_key = shared_key
    
    def _generate_signature(self, payload: str) -> str:
        """Генерирует HMAC-SHA256 подпись"""
        return hmac.new(
            self.shared_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Выполняет аутентифицированный запрос"""
        url = f"{self.base_url}{endpoint}"
        
        if data:
            payload = json.dumps(data, separators=(',', ':'))
            headers = {
                "Content-Type": "application/json",
                "X-Signature": self._generate_signature(payload)
            }
            
            if method.upper() == "POST":
                return requests.post(url, data=payload, headers=headers)
        else:
            payload = ""
            headers = {"X-Signature": self._generate_signature(payload)}
            
            if method.upper() == "GET":
                return requests.get(url, headers=headers)
        
        raise ValueError(f"Unsupported method: {method}")
    
    def create_job(self, lots: List[Dict[str, Any]], languages: Optional[List[str]] = None, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Создает задачу для генерации описаний
        
        Args:
            lots: Список лотов с изображениями
            languages: Список языков для перевода (опционально)
            webhook_url: URL для webhook уведомлений (опционально)
        
        Returns:
            Dict: Информация о созданной задаче
        """
        data: Dict[str, Any] = {"lots": lots}
        
        if languages:
            data["languages"] = languages
        
        if webhook_url:
            data["webhook_url"] = webhook_url
        
        response = self._make_request("POST", "/api/v1/generate", data)
        return response.json()
    
    def get_job_status(self, job_id: str) -> Dict:
        """
        Получает детальный статус задачи (с аутентификацией)
        
        Args:
            job_id: ID задачи
        
        Returns:
            Dict: Детальная информация о статусе
        """
        response = self._make_request("GET", f"/api/v1/batch-status/{job_id}")
        return response.json()
    
    def get_simple_status(self, job_id: str) -> Dict:
        """
        Получает простой статус задачи (без аутентификации)
        
        Args:
            job_id: ID задачи
        
        Returns:
            Dict: Базовая информация о статусе
        """
        url = f"{self.base_url}/api/v1/jobs/{job_id}/status"
        response = requests.get(url)
        return response.json()
    
    def get_job_results(self, job_id: str) -> Dict:
        """
        Получает полные результаты задачи
        
        Args:
            job_id: ID задачи
        
        Returns:
            Dict: Полные результаты обработки
        """
        response = self._make_request("GET", f"/api/v1/jobs/{job_id}")
        return response.json()
    
    def wait_for_completion(self, job_id: str, timeout: int = 3600, check_interval: int = 30) -> Dict:
        """
        Ожидает завершения задачи с polling
        
        Args:
            job_id: ID задачи
            timeout: Максимальное время ожидания в секундах
            check_interval: Интервал проверки в секундах
        
        Returns:
            Dict: Результаты задачи
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_simple_status(job_id)
            
            print(f"Статус: {status['status']}")
            
            if status['status'] == 'completed':
                return self.get_job_results(job_id)
            elif status['status'] == 'failed':
                raise Exception(f"Задача завершилась с ошибкой: {status.get('error', 'Unknown error')}")
            
            time.sleep(check_interval)
        
        raise TimeoutError(f"Задача не завершилась за {timeout} секунд")

def main():
    """Пример использования клиента"""
    
    # Настройки (измените на свои)
    BASE_URL = "http://localhost:5000"
    SHARED_KEY = os.environ.get("SHARED_KEY", "your-secret-key-here")
    
    # Создаем клиента
    client = CarDescriptionClient(BASE_URL, SHARED_KEY)
    
    # Пример данных
    test_lots = [
        {
            "lot_id": "test-car-1",
            "images": [
                "https://example.com/car1-front.jpg",
                "https://example.com/car1-side.jpg"
            ]
        },
        {
            "lot_id": "test-car-2", 
            "images": [
                "https://example.com/car2-front.jpg"
            ]
        }
    ]
    
    languages = ["en", "ru", "de"]
    
    try:
        # 1. Создаем задачу
        print("🚀 Создание задачи...")
        job = client.create_job(test_lots, languages)
        job_id = job["job_id"]
        print(f"✅ Задача создана: {job_id}")
        
        # 2. Проверяем детальный статус
        print("\n🔍 Проверка детального статуса...")
        detailed_status = client.get_job_status(job_id)
        print(json.dumps(detailed_status, indent=2, ensure_ascii=False))
        
        # 3. Простое polling
        print("\n⏱️ Ожидание завершения...")
        try:
            results = client.wait_for_completion(job_id, timeout=300, check_interval=10)
            print("\n✅ Задача завершена!")
            print(json.dumps(results, indent=2, ensure_ascii=False))
        except TimeoutError:
            print("⏰ Время ожидания истекло, но задача продолжает выполняться")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к серверу")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()