
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(text):
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text})

print("🔍 ДЕБАГ РЕЖИМ - проверяем что видит парсер\n")

# Тест 1: Avito
print("="*60)
print("TEST 1: Avito")
print("="*60)

url = "https://www.avito.ru/rossiya/tovary_dlya_kompyutera/komplektuyuschie/protsessory-ASgBAgICAkTGB~pm7gniZw?f=ASgBAgICA0TGB~pm7gniZ_i8DZbSNA&q=i5-12400F"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    r = requests.get(url, headers=headers, timeout=15)
    
    print(f"Status code: {r.status_code}")
    print(f"Content length: {len(r.text)} символов")
    
    # Сохраняем HTML
    with open("avito_debug.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    
    print("✅ HTML сохранён в avito_debug.html")
    
    # Проверяем что в HTML
    if "₽" in r.text or "руб" in r.text.lower():
        print("  ✅ Символ ₽ найден на странице!")
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Ищем все что содержит цифры и рубли
        for elem in soup.find_all(string=lambda text: text and "₽" in text):
            print(f"  Найден текст с ₽: {elem.strip()[:100]}")
    else:
        print("  ❌ Символ ₽ НЕ найден")
        
        # Проверяем что вообще пришло
        if "captcha" in r.text.lower() or "robot" in r.text.lower():
            print("  ⚠️ КАПЧА! Avito определил что это бот")
        elif len(r.text) < 5000:
            print("  ⚠️ Слишком короткий ответ - возможно блокировка")
            print(f"  Первые 500 символов: {r.text[:500]}")
            
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n")

# Тест 2: Goofish через Selenium
print("="*60)
print("TEST 2: Goofish (Selenium)")
print("="*60)

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.binary_location = "/usr/bin/chromium-browser"

try:
    driver = webdriver.Chrome(options=options)
    url = "https://www.goofish.com/search?q=i5-12400F"
    
    print(f"Открываю: {url}")
    driver.get(url)
    time.sleep(5)
    
    # Сохраняем HTML
    html = driver.page_source
    with open("goofish_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ HTML сохранён в goofish_debug.html")
    print(f"   Размер: {len(html)} символов")
    
    # Проверяем что в HTML
    if "¥" in html or "￥" in html:
        print("  ✅ Символ ¥ найден на странице!")
    else:
        print("  ❌ Символ ¥ НЕ найден")
        
    if "login" in html.lower() or "登录" in html:
        print("  ⚠️ Goofish требует авторизацию!")
        
    driver.quit()
    
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n")
print("="*60)
print("✅ Дебаг завершён!")
print("Файлы avito_debug.html и goofish_debug.html сохранены")
print("="*60)

send_telegram("🔍 Дебаг завершён! Проверяю HTML файлы...")
