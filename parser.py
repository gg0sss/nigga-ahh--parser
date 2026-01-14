import os
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

# Курс юаня к рублю (примерно)
CNY_TO_RUB = 13.5
DELIVERY = 300

# Товары для отслеживания
PRODUCTS = {
    "i5-12400F": {
        "goofish": "i5-12400F",
        "avito": "i5-12400F"
    },
    "Ryzen 5 7500f": {
        "goofish": "Ryzen 5 7500f",
        "avito": "Ryzen 5 7500f"
    },
    "Acer Predator RAM": {
        "goofish": "宏基掠夺者6400 C32 32G",
        "avito": "Acer Predator Vesta II RGB 32"
    }
}

def parse_avito(query):
    """Парсинг Avito"""
    url = f"https://www.avito.ru/rossiya?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Ищем цены (Avito хранит их в data-атрибутах)
        prices = []
        items = soup.find_all("div", {"data-marker": "item"})
        
        for item in items[:5]:  # Берём топ-5 объявлений
            price_elem = item.find("meta", {"itemprop": "price"})
            if price_elem and price_elem.get("content"):
                price = int(price_elem["content"])
                prices.append(price)
        
        if prices:
            return min(prices)  # Возвращаем минимальную цену
        return None
    except Exception as e:
        print(f"Ошибка парсинга Avito: {e}")
        return None

def parse_goofish(query):
    """Парсинг Goofish через Selenium"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium-browser"
    
    try:
        driver = webdriver.Chrome(options=options)
        url = f"https://www.goofish.com/search?q={query}"
        driver.get(url)
        
        # Ждём загрузки товаров
        time.sleep(5)
        
        # Ищем цены
        prices = []
        price_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='price']")
        
        for elem in price_elements[:10]:
            try:
                text = elem.text.replace("¥", "").replace(",", "").strip()
                if text.replace(".", "").isdigit():
                    price = float(text)
                    prices.append(price)
            except:
                continue
        
        driver.quit()
        
        if prices:
            return min(prices)  # Минимальная цена в юанях
        return None
    except Exception as e:
        print(f"Ошибка парсинга Goofish: {e}")
        return None

# Загрузка старых данных
try:
    with open("products.json", "r", encoding="utf-8") as f:
        old_data = json.load(f)
except:
    old_data = {}

new_data = {}

send_telegram("🤖 Парсер запущен!")

# Парсим каждый товар
for product_name, queries in PRODUCTS.items():
    print(f"\n📦 Проверяю: {product_name}")
    
    # Avito
    avito_price = parse_avito(queries["avito"])
    print(f"  Avito: {avito_price}₽" if avito_price else "  Avito: не найдено")
    
    # Goofish
    goofish_price_cny = parse_goofish(queries["goofish"])
    if goofish_price_cny:
        goofish_price_rub = (goofish_price_cny * CNY_TO_RUB) + DELIVERY
        print(f"  Goofish: {goofish_price_cny}¥ = {goofish_price_rub:.0f}₽")
    else:
        goofish_price_rub = None
        print(f"  Goofish: не найдено")
    
    # Сохраняем данные
    new_data[product_name] = {
        "avito": avito_price,
        "goofish_cny": goofish_price_cny,
        "goofish_rub": goofish_price_rub
    }
    
    # Считаем выгоду
    if avito_price and goofish_price_rub:
        profit = avito_price - goofish_price_rub
        profit_percent = (profit / avito_price) * 100
        
        print(f"  💰 Выгода: {profit:.0f}₽ ({profit_percent:.1f}%)")
        
        # Если выгода > 40% - шлём уведомление
        if profit_percent > 40:
            msg = f"🔥 ВЫГОДНО!\n\n"
            msg += f"📦 {product_name}\n\n"
            msg += f"Goofish: {goofish_price_cny}¥ ({goofish_price_rub:.0f}₽)\n"
            msg += f"Avito: {avito_price}₽\n\n"
            msg += f"💰 Выгода: {profit:.0f}₽ ({profit_percent:.1f}%)"
            send_telegram(msg)

# Сохраняем данные
with open("products.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

send_telegram("✅ Проверка завершена!")
