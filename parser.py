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

# Курс юаня к рублю
CNY_TO_RUB = 13.5
DELIVERY = 300

# Товары для отслеживания
PRODUCTS = {
    "i5-12400F": {
        "goofish": "i5-12400F",
        "avito": "i5-12400F",
        "category": "cpu"  # процессор
    },
    "Ryzen 5 7500f": {
        "goofish": "Ryzen 5 7500f",
        "avito": "Ryzen 5 7500f",
        "category": "cpu"
    },
    "Acer Predator RAM": {
        "goofish": "宏基掠夺者6400 C32 32G",
        "avito": "Acer Predator Vesta II RGB 32",
        "category": "ram"  # оперативная память
    }
}

def parse_avito(query, category):
    """Парсинг Avito с фильтрами"""
    
    # URL с фильтрами для процессоров (новое)
    if category == "cpu":
        # Категория процессоры + состояние новое
        base_url = "https://www.avito.ru/rossiya/tovary_dlya_kompyutera/komplektuyuschie/protsessory-ASgBAgICAkTGB~pm7gniZw"
        params = "?f=ASgBAgICA0TGB~pm7gniZ_i8DZbSNA"  # фильтр "новое"
    else:  # ram
        # Категория оперативная память + новое
        base_url = "https://www.avito.ru/rossiya/tovary_dlya_kompyutera/komplektuyuschie/operativnaya_pamyat-ASgBAgICAkTGB~pm7griZQ"
        params = "?f=ASgBAgICA0TGB~pm7griZf4vA2W0jQ"  # фильтр "новое"
    
    url = f"{base_url}{params}&q={query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"  Avito URL: {url}")
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Ищем цены - Avito использует разные селекторы
        prices = []
        
        # Вариант 1: meta itemprop="price"
        items = soup.find_all("div", {"data-marker": "item"})
        for item in items[:10]:
            price_elem = item.find("meta", {"itemprop": "price"})
            if price_elem and price_elem.get("content"):
                try:
                    price = int(price_elem["content"])
                    prices.append(price)
                    print(f"    Найдена цена: {price}₽")
                except:
                    pass
        
        # Вариант 2: span с ценой
        if not prices:
            price_spans = soup.find_all("span", class_=lambda x: x and "price" in x.lower())
            for span in price_spans[:10]:
                text = span.get_text().replace(" ", "").replace("₽", "").strip()
                if text.isdigit():
                    prices.append(int(text))
                    print(f"    Найдена цена: {text}₽")
        
        if prices:
            min_price = min(prices)
            print(f"  ✅ Avito: минимальная цена {min_price}₽ (найдено {len(prices)} объявлений)")
            return min_price
        else:
            print(f"  ❌ Avito: цены не найдены")
            return None
            
    except Exception as e:
        print(f"  ❌ Ошибка парсинга Avito: {e}")
        return None

def parse_goofish(query):
    """Парсинг Goofish через Selenium с фильтром 全新"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.binary_location = "/usr/bin/chromium-browser"
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        url = f"https://www.goofish.com/search?q={query}"
        print(f"  Goofish URL: {url}")
        
        driver.get(url)
        time.sleep(3)  # Ждём загрузки
        
        # Пытаемся найти и кликнуть фильтр "全新" (новое)
        try:
            # Ищем кнопку/чекбокс с текстом "全新"
            new_filter = driver.find_element(By.XPATH, "//*[contains(text(), '全新')]")
            new_filter.click()
            print(f"    Кликнул фильтр '全新'")
            time.sleep(3)  # Ждём обновления результатов
        except:
            print(f"    Фильтр '全新' не найден, парсим без фильтра")
        
        # Парсим цены
        prices = []
        
        # Ищем элементы с ценами (разные варианты селекторов)
        price_selectors = [
            "[class*='Price']",
            "[class*='price']",
            ".price",
            "[class*='priceText']"
        ]
        
        for selector in price_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:15]:
                    text = elem.text.strip()
                    # Убираем символы и пробелы
                    clean_text = text.replace("¥", "").replace("￥", "").replace(",", "").replace(" ", "").strip()
                    
                    # Проверяем что это число
                    if clean_text.replace(".", "").isdigit():
                        price = float(clean_text)
                        if 10 < price < 50000:  # Фильтр адекватных цен
                            prices.append(price)
                            print(f"    Найдена цена: {price}¥")
            except:
                continue
        
        driver.quit()
        
        if prices:
            min_price = min(prices)
            print(f"  ✅ Goofish: минимальная цена {min_price}¥ (найдено {len(prices)} объявлений)")
            return min_price
        else:
            print(f"  ❌ Goofish: цены не найдены")
            return None
            
    except Exception as e:
        print(f"  ❌ Ошибка парсинга Goofish: {e}")
        if driver:
            driver.quit()
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
for product_name, info in PRODUCTS.items():
    print(f"\n{'='*60}")
    print(f"📦 Проверяю: {product_name}")
    print(f"{'='*60}")
    
    # Avito
    avito_price = parse_avito(info["avito"], info["category"])
    
    # Goofish
    goofish_price_cny = parse_goofish(info["goofish"])
    if goofish_price_cny:
        goofish_price_rub = (goofish_price_cny * CNY_TO_RUB) + DELIVERY
        print(f"  💱 Goofish в рублях: {goofish_price_rub:.0f}₽ (курс {CNY_TO_RUB})")
    else:
        goofish_price_rub = None
    
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
        
        print(f"\n  💰 РАСЧЁТ ВЫГОДЫ:")
        print(f"     Goofish: {goofish_price_cny}¥ → {goofish_price_rub:.0f}₽")
        print(f"     Avito:   {avito_price}₽")
        print(f"     Выгода:  {profit:.0f}₽ ({profit_percent:.1f}%)")
        
        # Если выгода > 40% - шлём уведомление
        if profit_percent > 40:
            msg = f"🔥 ВЫГОДНОЕ ПРЕДЛОЖЕНИЕ!\n\n"
            msg += f"📦 {product_name}\n\n"
            msg += f"Goofish: {goofish_price_cny}¥ ({goofish_price_rub:.0f}₽)\n"
            msg += f"Avito: {avito_price}₽\n\n"
            msg += f"💰 Выгода: {profit:.0f}₽ ({profit_percent:.1f}%)"
            send_telegram(msg)
            print(f"  ✉️ Отправлено уведомление в Telegram!")
    
    time.sleep(2)  # Пауза между товарами

# Сохраняем данные
with open("products.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print("✅ Проверка завершена!")
print(f"{'='*60}")

send_telegram("✅ Проверка завершена!")
