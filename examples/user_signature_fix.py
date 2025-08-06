#!/usr/bin/env python3
"""
Генерация правильной подписи для пользовательских данных
"""
import hmac
import hashlib
import json

# Данные пользователя из curl запроса
lots_data = [
    {
        "lot_id": "demo-car-12345",
        "additional_info": "2021 BMW X5, front collision damage, airbags deployed",
        "images": [
            {"url": "https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-5280294760125443694-1024x768.jpeg"},
            {"url": "https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-8256033307301130576-1024x768.jpeg"}
        ]
    }
]

# Ключ
shared_key = "dev-secret-key-for-testing-2024"

# Генерация подписи (точно как в API)
normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)
signature = hmac.new(
    shared_key.encode(),
    normalized.encode(),
    hashlib.sha256
).hexdigest()

print("🔐 Правильная подпись:")
print(f"sha256={signature}")
print("")

# Готовый payload
payload = {
    "signature": f"sha256={signature}",
    "version": "1.0.0",
    "languages": ["en", "ru"],
    "lots": lots_data
}

print("📋 Готовая curl команда:")
print(f"""curl -X POST "https://bach-ai-info3819.replit.app/api/v1/generate-descriptions" \\
  -H "Content-Type: application/json" \\
  -H "User-Agent: CurlDemo/1.0" \\
  -d '{json.dumps(payload, separators=(',', ':'), ensure_ascii=False)}' \\
  --max-time 300""")