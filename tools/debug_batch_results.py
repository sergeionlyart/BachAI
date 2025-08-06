#!/usr/bin/env python3
"""
Отладочный скрипт для проверки структуры результатов от OpenAI Batch API
"""
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.openai_client import OpenAIClient

def debug_batch_results():
    """Проверить структуру результатов batch"""
    client = OpenAIClient()
    
    # ID vision batch для задачи клиента
    vision_batch_id = "batch_6892698998ac8190b410b61c561fb05f"
    
    try:
        # Получаем статус batch
        batch_status = client.get_batch_status(vision_batch_id)
        print(f"Batch Status: {batch_status['status']}")
        print(f"Output File ID: {batch_status.get('output_file_id')}")
        
        # Загружаем результаты
        results_content = client.download_batch_results(batch_status['output_file_id'])
        
        # Анализируем первые несколько результатов
        lines = results_content.strip().split('\n')
        print(f"\nВсего строк результатов: {len(lines)}")
        
        for i, line in enumerate(lines[:3]):  # Первые 3 результата
            if line:
                result = json.loads(line)
                print(f"\n=== Результат {i+1} ===")
                print(f"Custom ID: {result.get('custom_id')}")
                
                response = result.get('response', {})
                print(f"Response keys: {list(response.keys())}")
                
                if 'body' in response:
                    body = response['body']
                    print(f"Body keys: {list(body.keys()) if isinstance(body, dict) else type(body)}")
                    
                    # Проверяем разные форматы
                    if isinstance(body, dict):
                        # Новый формат (Responses API)
                        if 'output' in body:
                            output = body['output']
                            print(f"Output (Responses API): '{output}' (len: {len(str(output))})")
                        
                        # Старый формат (Chat API)
                        if 'choices' in body:
                            choices = body['choices']
                            print(f"Choices count: {len(choices) if choices else 0}")
                            if choices and len(choices) > 0:
                                choice = choices[0]
                                if 'message' in choice:
                                    content = choice['message'].get('content', '')
                                    print(f"Content (Chat API): '{content}' (len: {len(content)})")
                
                # Показываем полную структуру для понимания
                print(f"Полная структура response:")
                print(json.dumps(response, indent=2)[:500] + "...")
                
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    debug_batch_results()