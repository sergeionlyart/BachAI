#!/usr/bin/env python3
"""
Генератор HMAC подписи для curl запросов
"""
import hmac
import hashlib
import json

def generate_signature_for_lots(lots_data, shared_key):
    """Генерирует подпись для массива lots"""
    # Нормализация для подписи (как в API)
    normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)
    
    # HMAC-SHA256
    signature = hmac.new(
        shared_key.encode(),
        normalized.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"

# Демонстрационные данные
lots_data = [
    {
        "lot_id": "demo-car-12345",
        "additional_info": "2021 BMW X5, front collision damage, airbags deployed",
        "images": [
            {"url": "https://images.unsplash.com/photo-1549399811-9b0c893bd7c1?w=800"},
            {"url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"}
        ]
    }
]

# Ключ для разработки
shared_key = "dev-secret-key-for-testing-2024"

# Генерируем подпись
signature = generate_signature_for_lots(lots_data, shared_key)
print(f"Подпись для демо данных: {signature}")

# Полный payload для curl
payload = {
    "signature": signature,
    "version": "1.0.0",
    "languages": ["en", "ru"],
    "lots": lots_data
}

print("\n📋 Готовый JSON для curl:")
print(json.dumps(payload, indent=2, ensure_ascii=False))

print(f"\n🔗 Готовая curl команда:")
print(f"""curl -X POST "https://bach-ai-info3819.replit.app/api/v1/generate-descriptions" \\
  -H "Content-Type: application/json" \\
  -H "User-Agent: CurlDemo/1.0" \\
  -d '{json.dumps(payload, separators=(',', ':'), ensure_ascii=False)}' \\
  --max-time 300""")