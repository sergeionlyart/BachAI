/**
 * JavaScript/Node.js клиент для Generation Service
 * Поддерживает синхронный и асинхронный режимы с polling
 */

const crypto = require('crypto');
const axios = require('axios');

class GenerationServiceClient {
    constructor(baseUrl, sharedKey) {
        this.baseUrl = baseUrl;
        this.sharedKey = sharedKey;
        this.axios = axios.create({
            timeout: 300000, // 5 минут
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'GenerationServiceClient-JS/1.0'
            }
        });
    }

    /**
     * Генерация HMAC-SHA256 подписи
     */
    generateSignature(lotsData) {
        const normalized = JSON.stringify(lotsData, Object.keys(lotsData).sort());
        return crypto
            .createHmac('sha256', this.sharedKey)
            .update(normalized)
            .digest('hex');
    }

    /**
     * Синхронная генерация описаний (1 автомобиль)
     */
    async syncGenerate(lotId, images, additionalInfo = '', languages = ['en']) {
        const lots = [{
            lot_id: lotId,
            additional_info: additionalInfo,
            images: images.map(url => ({ url }))
        }];

        const payload = {
            signature: this.generateSignature(lots),
            version: '1.0.0',
            languages,
            lots
        };

        try {
            const response = await this.axios.post(
                `${this.baseUrl}/api/v1/generate-descriptions`,
                payload
            );
            return response.data;
        } catch (error) {
            throw new Error(`Sync generation failed: ${error.response?.data?.error || error.message}`);
        }
    }

    /**
     * Создание пакетного задания (2+ автомобилей)
     */
    async createBatchJob(carsData, languages = ['en']) {
        const payload = {
            signature: this.generateSignature(carsData),
            version: '1.0.0',
            languages,
            lots: carsData
        };

        try {
            const response = await this.axios.post(
                `${this.baseUrl}/api/v1/generate-descriptions`,
                payload
            );
            return response.data.job_id;
        } catch (error) {
            throw new Error(`Batch job creation failed: ${error.response?.data?.error || error.message}`);
        }
    }

    /**
     * Проверка статуса задания
     */
    async getJobStatus(jobId) {
        try {
            const response = await this.axios.get(
                `${this.baseUrl}/api/v1/batch-status/${jobId}`
            );
            return response.data;
        } catch (error) {
            throw new Error(`Status check failed: ${error.response?.data?.error || error.message}`);
        }
    }

    /**
     * Получение результатов задания
     */
    async getResults(jobId) {
        try {
            const response = await this.axios.get(
                `${this.baseUrl}/api/v1/batch-results/${jobId}`
            );
            return response.data;
        } catch (error) {
            if (error.response?.status === 202) {
                return null; // Еще не готово
            }
            throw new Error(`Results fetch failed: ${error.response?.data?.error || error.message}`);
        }
    }

    /**
     * Ожидание завершения с автоматическим polling
     */
    async waitForCompletion(jobId, maxWaitTime = 3600, pollInterval = 30) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitTime * 1000) {
            const status = await this.getJobStatus(jobId);
            
            console.log(`Статус: ${status.status} - ${status.progress.completion_percentage}%`);
            
            if (status.status === 'completed') {
                return await this.getResults(jobId);
            } else if (['failed', 'cancelled'].includes(status.status)) {
                throw new Error(`Job ${status.status}: ${status.error_message || 'Unknown error'}`);
            }
            
            await this.sleep(pollInterval * 1000);
        }
        
        throw new Error(`Job timeout after ${maxWaitTime} seconds`);
    }

    /**
     * Отмена задания
     */
    async cancelJob(jobId) {
        try {
            const response = await this.axios.post(
                `${this.baseUrl}/api/v1/batch-jobs/${jobId}/cancel`
            );
            return response.data;
        } catch (error) {
            throw new Error(`Job cancellation failed: ${error.response?.data?.error || error.message}`);
        }
    }

    /**
     * Список заданий с фильтрацией
     */
    async listJobs(status = null, limit = 10, offset = 0) {
        const params = new URLSearchParams();
        if (status) params.append('status', status);
        params.append('limit', limit.toString());
        params.append('offset', offset.toString());

        try {
            const response = await this.axios.get(
                `${this.baseUrl}/api/v1/batch-jobs?${params}`
            );
            return response.data;
        } catch (error) {
            throw new Error(`Jobs list failed: ${error.response?.data?.error || error.message}`);
        }
    }

    /**
     * Утилита для задержки
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Пример использования
async function example() {
    const client = new GenerationServiceClient(
        'https://your-service.replit.app',
        'your-shared-key'
    );

    try {
        // 1. Синхронный режим (1 автомобиль)
        console.log('🚗 Синхронная обработка...');
        const syncResult = await client.syncGenerate(
            'demo-car-123',
            [
                'https://example.com/car1-front.jpg',
                'https://example.com/car1-side.jpg'
            ],
            '2019 Tesla Model 3, minor damage',
            ['en', 'ru']
        );
        
        console.log(`✅ Получено ${syncResult.lots[0].descriptions.length} описаний`);

        // 2. Асинхронный режим (множество автомобилей)
        console.log('\n🔄 Пакетная обработка...');
        const cars = [
            {
                lot_id: 'fleet-001',
                additional_info: '2020 BMW X3',
                images: [{ url: 'https://example.com/bmw1.jpg' }]
            },
            {
                lot_id: 'fleet-002',
                additional_info: '2021 Audi A4',
                images: [{ url: 'https://example.com/audi1.jpg' }]
            }
        ];

        const jobId = await client.createBatchJob(cars, ['en', 'ru', 'de']);
        console.log(`📋 Задание создано: ${jobId}`);

        // Polling с прогрессом
        const results = await client.waitForCompletion(jobId, 1800, 15);
        console.log(`✅ Обработано ${results.results.lots.length} автомобилей`);

        // 3. Список активных заданий
        const activeJobs = await client.listJobs('processing', 5);
        console.log(`📊 Активных заданий: ${activeJobs.jobs.length}`);

    } catch (error) {
        console.error('❌ Ошибка:', error.message);
    }
}

// Обработка ошибок подключения
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

module.exports = GenerationServiceClient;

// Запуск примера
if (require.main === module) {
    example();
}