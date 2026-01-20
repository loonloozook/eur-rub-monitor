"""
EUR/RUB Rate Monitor - Web Application
Веб-приложение для мониторинга курса EUR/RUB
"""

import os
import json
import re
import time
from datetime import datetime
from typing import Optional, Dict, Any

from flask import Flask, render_template_string, jsonify

import requests

# Опционально: Selenium для парсинга Profinance
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


app = Flask(__name__)

# HTML шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Курс EUR/RUB</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        h1 {
            text-align: center;
            color: #1a1a2e;
            margin-bottom: 30px;
            font-size: 28px;
        }
        
        .btn {
            width: 100%;
            padding: 18px 30px;
            font-size: 18px;
            font-weight: 600;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        
        .result {
            margin-top: 30px;
            display: none;
        }
        
        .result.show {
            display: block;
        }
        
        .rate-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }
        
        .rate-card.highlight {
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            border: 2px solid #4caf50;
        }
        
        .rate-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        
        .rate-value {
            font-size: 24px;
            font-weight: 700;
            color: #1a1a2e;
        }
        
        .rate-value.forecast {
            color: #2e7d32;
            font-size: 28px;
        }
        
        .rate-small {
            font-size: 14px;
            color: #888;
            margin-top: 5px;
        }
        
        .timestamp {
            text-align: center;
            color: #888;
            font-size: 13px;
            margin-top: 20px;
        }
        
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 12px;
            margin-top: 20px;
            display: none;
        }
        
        .error.show {
            display: block;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        
        .loading.show {
            display: block;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .sources {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        
        .source-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            font-size: 14px;
            color: #666;
        }
        
        .source-value {
            font-weight: 600;
            color: #333;
        }
        
        .manual-input {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        
        .manual-input label {
            display: block;
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }
        
        .manual-input input {
            width: 100%;
            padding: 12px 15px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.2s;
        }
        
        .manual-input input:focus {
            border-color: #667eea;
        }
        
        .manual-input small {
            display: block;
            margin-top: 8px;
            color: #888;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💱 Курс EUR/RUB</h1>
        
        <div class="manual-input">
            <label for="manualRate">Курс с Investing.com (опционально):</label>
            <input type="number" id="manualRate" step="0.0001" placeholder="Например: 90.91">
            <small>Если указать — расчёт будет по нему. Иначе — по кросс-курсу через юань.</small>
        </div>
        
        <button class="btn" id="updateBtn" onclick="updateRates()">
            🔄 Получить курс
        </button>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Загрузка данных...</p>
        </div>
        
        <div class="error" id="error"></div>
        
        <div class="result" id="result">
            <div class="rate-card highlight">
                <div class="rate-label">📌 Прогноз курса ЦБ на завтра</div>
                <div class="rate-value forecast" id="forecast">—</div>
            </div>
            
            <div class="rate-card">
                <div class="rate-label">Курс ЦБ сегодня</div>
                <div class="rate-value" id="cbrRate">—</div>
                <div class="rate-small" id="cbrChange"></div>
            </div>
            
            <div class="rate-card">
                <div class="rate-label">Рыночная оценка</div>
                <div class="rate-value" id="marketRate">—</div>
                <div class="rate-small" id="marketSource"></div>
            </div>
            
            <div class="sources">
                <div class="source-item">
                    <span>CNY/RUB (MOEX)</span>
                    <span class="source-value" id="cnyRub">—</span>
                </div>
                <div class="source-item">
                    <span>EUR/CNY</span>
                    <span class="source-value" id="eurCny">—</span>
                </div>
                <div class="source-item">
                    <span>Кросс-курс</span>
                    <span class="source-value" id="crossRate">—</span>
                </div>
            </div>
            
            <div class="timestamp" id="timestamp"></div>
        </div>
    </div>
    
    <script>
        async function updateRates() {
            const btn = document.getElementById('updateBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            const error = document.getElementById('error');
            const manualRate = document.getElementById('manualRate').value;
            
            btn.disabled = true;
            btn.textContent = '⏳ Загрузка...';
            loading.classList.add('show');
            result.classList.remove('show');
            error.classList.remove('show');
            
            try {
                let url = '/api/rates';
                if (manualRate) {
                    url += '?manual_rate=' + manualRate;
                }
                
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Заполняем данные
                document.getElementById('forecast').textContent = data.forecast || '—';
                document.getElementById('cbrRate').textContent = data.cbr_eur ? data.cbr_eur.toFixed(4) + ' ₽' : '—';
                document.getElementById('cbrChange').textContent = data.cbr_change ? 
                    (data.cbr_change >= 0 ? '+' : '') + data.cbr_change.toFixed(4) + ' к вчера' : '';
                document.getElementById('marketRate').textContent = data.market_rate ? data.market_rate.toFixed(4) + ' ₽' : '—';
                document.getElementById('marketSource').textContent = data.market_source || '';
                document.getElementById('cnyRub').textContent = data.cny_rub ? data.cny_rub.toFixed(4) + ' ₽' : '—';
                document.getElementById('eurCny').textContent = data.eur_cny ? data.eur_cny.toFixed(4) + ' ¥' : '—';
                document.getElementById('crossRate').textContent = data.cross_rate ? data.cross_rate.toFixed(4) + ' ₽' : '—';
                document.getElementById('timestamp').textContent = 'Обновлено: ' + data.timestamp;
                
                result.classList.add('show');
                
            } catch (e) {
                error.textContent = '❌ Ошибка: ' + e.message;
                error.classList.add('show');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔄 Получить курс';
                loading.classList.remove('show');
            }
        }
    </script>
</body>
</html>
"""


def get_cbr_rates() -> Dict[str, Any]:
    """Курсы ЦБ РФ"""
    try:
        response = requests.get(
            'https://www.cbr-xml-daily.ru/daily_json.js',
            timeout=10
        )
        data = response.json()
        return {
            'eur': data['Valute']['EUR']['Value'],
            'eur_prev': data['Valute']['EUR']['Previous'],
            'cny': data['Valute']['CNY']['Value'],
            'usd': data['Valute']['USD']['Value'],
            'date': data['Date'][:10]
        }
    except Exception as e:
        print(f"CBR error: {e}")
        return {}


def get_moex_cny_rub() -> Optional[float]:
    """CNY/RUB с Мосбиржи"""
    try:
        url = 'https://iss.moex.com/iss/engines/currency/markets/selt/boards/CETS/securities/CNYRUB_TOM.json'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        marketdata = data.get('marketdata', {}).get('data', [])
        columns = data.get('marketdata', {}).get('columns', [])
        
        if marketdata and columns:
            row = marketdata[0]
            last_idx = columns.index('LAST') if 'LAST' in columns else -1
            wap_idx = columns.index('WAPRICE') if 'WAPRICE' in columns else -1
            
            rate = row[last_idx] if last_idx >= 0 else None
            if not rate and wap_idx >= 0:
                rate = row[wap_idx]
            
            return float(rate) if rate else None
    except Exception as e:
        print(f"MOEX error: {e}")
    return None


def get_eur_cny() -> Optional[float]:
    """EUR/CNY через Frankfurter API"""
    try:
        response = requests.get(
            'https://api.frankfurter.app/latest?from=EUR&to=CNY',
            timeout=10
        )
        data = response.json()
        return data['rates']['CNY']
    except Exception as e:
        print(f"Frankfurter error: {e}")
    return None


def get_profinance_rate() -> Optional[float]:
    """Парсинг Profinance через Selenium"""
    if not SELENIUM_AVAILABLE:
        return None
    
    try:
        options = ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        if WEBDRIVER_MANAGER_AVAILABLE:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        
        driver.set_page_load_timeout(15)
        driver.get('https://www.profinance.ru/currency_eur.asp')
        time.sleep(3)
        
        page_source = driver.page_source
        driver.quit()
        
        # Ищем курс
        patterns = [
            r'EUR/RUB[^\d]*(\d{2}[.,]\d{2,4})',
            r'EURRUB[^\d]*(\d{2}[.,]\d{2,4})',
            r'>(\d{2}[.,]\d{4})<',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            for match in matches:
                val = float(match.replace(',', '.'))
                if 80 < val < 120:
                    return val
    except Exception as e:
        print(f"Profinance error: {e}")
    return None


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/rates')
def api_rates():
    from flask import request
    
    try:
        # Получаем данные
        cbr = get_cbr_rates()
        cny_rub = get_moex_cny_rub()
        eur_cny = get_eur_cny()
        
        # Проверяем ручной ввод
        manual_rate = request.args.get('manual_rate', type=float)
        
        # Пробуем Profinance (если Selenium доступен)
        profinance_rate = None
        if not manual_rate and SELENIUM_AVAILABLE:
            profinance_rate = get_profinance_rate()
        
        # Определяем рыночный курс
        market_rate = None
        market_source = ''
        
        if manual_rate and 80 < manual_rate < 120:
            market_rate = manual_rate
            market_source = 'Ручной ввод'
        elif profinance_rate:
            market_rate = profinance_rate
            market_source = 'Profinance'
        elif cny_rub and eur_cny:
            cross = cny_rub * eur_cny
            market_rate = cross - 1.5  # Корректировка
            market_source = 'Кросс-курс (скорр.)'
        
        # Рассчитываем прогноз
        forecast = None
        if market_rate and cbr.get('eur'):
            estimate = market_rate * 0.6 + cbr['eur'] * 0.4
            low = estimate - 0.2
            high = estimate + 0.2
            forecast = f"{low:.2f} – {high:.2f} ₽/€"
        
        # Кросс-курс для отображения
        cross_rate = None
        if cny_rub and eur_cny:
            cross_rate = cny_rub * eur_cny
        
        return jsonify({
            'timestamp': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'cbr_eur': cbr.get('eur'),
            'cbr_change': cbr['eur'] - cbr['eur_prev'] if cbr.get('eur') and cbr.get('eur_prev') else None,
            'cny_rub': cny_rub,
            'eur_cny': eur_cny,
            'cross_rate': cross_rate,
            'market_rate': market_rate,
            'market_source': market_source,
            'forecast': forecast,
            'profinance_available': SELENIUM_AVAILABLE
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
