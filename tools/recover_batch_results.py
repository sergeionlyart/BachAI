#!/usr/bin/env python3
"""
Скрипт для восстановления результатов из OpenAI batch API
Используется когда результаты анализа изображений не сохранились в базе данных
"""
import os
import sys
import json
import logging
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.openai_client import OpenAIClient
from services.database_manager import DatabaseManager  
from database.models import db, BatchJob, BatchLot
from app import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchResultsRecovery:
    def __init__(self):
        self.openai_client = OpenAIClient()
        
    def recover_job_results(self, job_id: str):
        """Восстановить результаты для конкретной задачи"""
        with app.app_context():
            db_manager = DatabaseManager(db.session)
            
            # Получаем задачу из БД
            job = db_manager.get_batch_job(job_id)
            if not job:
                logger.error(f"Задача {job_id} не найдена")
                return False
                
            logger.info(f"Восстанавливаем результаты для задачи {job_id}")
            logger.info(f"Статус: {job.status}")
            logger.info(f"Vision Batch ID: {job.openai_vision_batch_id}")
            logger.info(f"Translation Batch ID: {job.openai_translation_batch_id}")
            
            # Проверяем vision batch
            if job.openai_vision_batch_id:
                success = self._recover_vision_results(job, db_manager)
                if success:
                    logger.info("Vision результаты успешно восстановлены!")
                    # Обновляем статус задачи на completed
                    db_manager.update_batch_job_status(job_id, 'completed', None)
                    return True
                else:
                    logger.error("Не удалось восстановить vision результаты")
                    return False
            else:
                logger.error("Vision Batch ID не найден")
                return False
    
    def _recover_vision_results(self, job, db_manager):
        """Восстановить результаты анализа изображений"""
        try:
            # Проверяем статус batch в OpenAI
            batch_status = self.openai_client.get_batch_status(job.openai_vision_batch_id)
            logger.info(f"OpenAI batch статус: {batch_status['status']}")
            
            if batch_status['status'] != 'completed':
                logger.error(f"OpenAI batch не завершен: {batch_status['status']}")
                return False
            
            # Загружаем результаты
            results_content = self.openai_client.download_batch_results(
                batch_status['output_file_id']
            )
            logger.info(f"Загружено {len(results_content.split())} строк результатов")
            
            # Парсим результаты
            vision_results = self._parse_batch_results(results_content)
            logger.info(f"Распарсено {len(vision_results)} результатов")
            
            # Сохраняем в БД
            return self._save_vision_results(job, vision_results, db_manager)
            
        except Exception as e:
            logger.error(f"Ошибка восстановления vision результатов: {str(e)}")
            return False
    
    def _parse_batch_results(self, results_content: str):
        """Парсить результаты batch от OpenAI"""
        import json
        results = []
        
        for line in results_content.strip().split('\n'):
            if line:
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError as e:
                    logger.warning(f"Не удалось распарсить строку: {line[:100]}...")
                    
        return results
    
    def _save_vision_results(self, job, vision_results: list, db_manager):
        """Сохранить результаты анализа изображений в БД"""
        try:
            # Получаем все лоты для этой задачи
            lots = db_manager.session.query(BatchLot).filter(
                BatchLot.batch_job_id == job.id
            ).all()
            
            lot_map = {getattr(lot, 'lot_id'): lot for lot in lots}
            logger.info(f"Найдено {len(lots)} лотов для обработки")
            
            successful_lots = 0
            
            for result in vision_results:
                if not isinstance(result, dict):
                    continue
                    
                custom_id = result.get('custom_id', '')
                if not custom_id.startswith('vision:'):
                    continue
                
                # Извлекаем lot_id из custom_id
                parts = custom_id.split(':')
                if len(parts) == 2:
                    lot_id = parts[1]
                elif len(parts) >= 3:
                    lot_id = parts[2]
                else:
                    continue
                
                # Извлекаем текст анализа из ответа
                vision_text = ''
                response_data = result.get('response', {})
                
                logger.info(f"Debug lot {lot_id}: response keys = {list(response_data.keys()) if response_data else 'None'}")
                
                if isinstance(response_data, dict):
                    body = response_data.get('body', {})
                    logger.info(f"Debug lot {lot_id}: body type = {type(body)}, keys = {list(body.keys()) if isinstance(body, dict) else 'N/A'}")
                    
                    if isinstance(body, dict):
                        # Пробуем новый формат (Responses API)
                        output = body.get('output', [])
                        if output and isinstance(output, list):
                            # Ищем объект с type='message' в массиве output
                            for item in output:
                                if isinstance(item, dict) and item.get('type') == 'message':
                                    content_list = item.get('content', [])
                                    if content_list and isinstance(content_list, list):
                                        # Ищем объект с type='output_text'
                                        for content_item in content_list:
                                            if isinstance(content_item, dict) and content_item.get('type') == 'output_text':
                                                text = content_item.get('text', '')
                                                if text:
                                                    vision_text = text
                                                    logger.info(f"Found text (Responses API) for {lot_id}: {len(text)} chars")
                                                    break
                                    if vision_text:
                                        break
                        
                        # Fallback: если output это строка
                        elif output and isinstance(output, str):
                            vision_text = output
                            logger.info(f"Found output string (Responses API) for {lot_id}: {len(output)} chars")
                        
                        # Если не нашли в Responses API, пробуем старый формат (Chat API)  
                        if not vision_text:
                            choices = body.get('choices', [{}])
                            if choices and len(choices) > 0:
                                message = choices[0].get('message', {})
                                content = message.get('content', '')
                                if content and isinstance(content, str):
                                    vision_text = content
                                    logger.info(f"Found content (Chat API) for {lot_id}: {len(content)} chars")
                    
                    # Если ничего не найдено, показываем что именно получили
                    if not vision_text:
                        output_info = f"output type: {type(body.get('output'))}, len: {len(body.get('output', []))}"
                        logger.warning(f"No text found for {lot_id}. {output_info}")
                
                # Сохраняем результат
                if lot_id in lot_map and vision_text:
                    lot = lot_map[lot_id]
                    setattr(lot, 'vision_result', vision_text)
                    setattr(lot, 'status', 'completed')
                    setattr(lot, 'updated_at', datetime.utcnow())
                    successful_lots += 1
                    logger.info(f"Восстановлен результат для лота {lot_id}: {len(vision_text)} символов")
                else:
                    logger.warning(f"Не удалось восстановить результат для лота {lot_id}")
            
            # Обновляем статистику задачи
            setattr(job, 'processed_lots', successful_lots)
            setattr(job, 'updated_at', datetime.utcnow())
            
            # Сохраняем в БД
            db_manager.session.commit()
            logger.info(f"Успешно восстановлено {successful_lots} из {len(lots)} лотов")
            
            return successful_lots > 0
            
        except Exception as e:
            db_manager.session.rollback()
            logger.error(f"Ошибка сохранения результатов: {str(e)}")
            return False

def main():
    if len(sys.argv) != 2:
        print("Использование: python recover_batch_results.py <job_id>")
        print("Пример: python recover_batch_results.py 365a09ce-5416-49b5-8471-d6aad042761c")
        sys.exit(1)
    
    job_id = sys.argv[1]
    recovery = BatchResultsRecovery()
    
    print(f"🔄 Начинаем восстановление результатов для задачи {job_id}")
    
    success = recovery.recover_job_results(job_id)
    
    if success:
        print("✅ Результаты успешно восстановлены!")
        print("Теперь вы можете получить полные результаты через API")
    else:
        print("❌ Не удалось восстановить результаты")
        print("Проверьте логи для деталей")

if __name__ == "__main__":
    main()