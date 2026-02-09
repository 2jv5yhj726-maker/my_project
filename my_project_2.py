#!/usr/bin/env python3
"""
tce_telegram_monitor.py
Мониторит tce.by/search.html по запросам SEARCH_TEXT, SEARCH_TEXT_2, SEARCH_TEXT_3
и шлёт сообщение в Telegram, если количество найденных мероприятий
отличается от ожидаемого.
"""

import os
import logging
from dotenv import load_dotenv
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# ============================================================
# Загрузка переменных окружения
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SEARCH_TEXT = os.getenv("SEARCH_TEXT", "Записки юного врача")
SEARCH_TEXT_2 = os.getenv("SEARCH_TEXT_2", "На чёрной")
SEARCH_TEXT_3 = os.getenv("SEARCH_TEXT_3", "Хутар")

URL = os.getenv("URL", "https://tce.by/search.html")

EXPECTED_COUNT_1 = 4
EXPECTED_COUNT_2 = 5
EXPECTED_COUNT_3 = 2


# ============================================================
# Логи
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)


# ============================================================
# Telegram
# ============================================================

def send_telegram(text: str):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=15)
        logging.info("Отправлено сообщение в Telegram")
    except Exception as e:
        logging.exception("Ошибка отправки Telegram: %s", e)


# ============================================================
# Selenium driver (универсальный)
# ============================================================

def get_driver():
    from selenium.webdriver.chrome.options import Options

    options = Options()

    # GitHub Actions принудительно headless
    if os.getenv("GITHUB_ACTIONS") == "true":
        options.add_argument("--headless=new")
    else:
        options.add_argument("--headless=new")

    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,800")

    driver = webdriver.Chrome(options=options)
    return driver


# ============================================================
# Основной поиск
# ============================================================

def get_count_with_selenium(search_text: str) -> int:
    driver = None

    try:
        driver = get_driver()
        driver.get(URL)

        wait = WebDriverWait(driver, 20)

        input_box = wait.until(
            EC.presence_of_element_located((By.NAME, "tags"))
        )
        input_box.clear()
        input_box.send_keys(search_text)

        reload_btn = driver.find_element(By.ID, "reload")
        reload_btn.click()

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#playbill tbody tr"))
            )
        except TimeoutException:
            logging.info("[%s] Результатов нет → 0", search_text)
            return 0

        rows = driver.find_elements(By.CSS_SELECTOR, "#playbill tbody tr")
        count = len(rows)

        logging.info("[%s] найдено %d мероприятий", search_text, count)

        return count

    except Exception as e:
        logging.exception("Ошибка Selenium для '%s': %s", search_text, e)
        raise

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


# ============================================================
# Основная логика мониторинга
# ============================================================

def main_once():
    alerts = []

    try:
        # Проверка 1
        count1 = get_count_with_selenium(SEARCH_TEXT)
        if count1 != EXPECTED_COUNT_1:
            alerts.append(
                f"🔎 <b>{SEARCH_TEXT}</b>\n"
                f"Ожидалось: <b>{EXPECTED_COUNT_1}</b>, найдено: <b>{count1}</b>\n"
            )
        else:
            logging.info("OK: %s = %d", SEARCH_TEXT, count1)

        # Проверка 2
        count2 = get_count_with_selenium(SEARCH_TEXT_2)
        if count2 != EXPECTED_COUNT_2:
            alerts.append(
                f"🔎 <b>{SEARCH_TEXT_2}</b>\n"
                f"Ожидалось: <b>{EXPECTED_COUNT_2}</b>, найдено: <b>{count2}</b>\n"
            )
        else:
            logging.info("OK: %s = %d", SEARCH_TEXT_2, count2)

        # Проверка 3
        count3 = get_count_with_selenium(SEARCH_TEXT_3)
        if count3 != EXPECTED_COUNT_3:
            alerts.append(
                f"🔎 <b>{SEARCH_TEXT_3}</b>\n"
                f"Ожидалось: <b>{EXPECTED_COUNT_3}</b>, найдено: <b>{count3}</b>\n"
            )
        else:
            logging.info("OK: %s = %d", SEARCH_TEXT_3, count3)

        # Если есть алерты → отправляем
        if alerts:
            msg = (
                "⚠️ <b>Алерт мониторинга tce.by</b>\n\n"
                + "\n".join(alerts)
                + f"\n{URL}"
            )
            send_telegram(msg)
        else:
            logging.info("Все значения соответствуют ожидаемым.")

    except Exception as e:
        logging.exception("Ошибка мониторинга: %s", e)
        send_telegram(f"❗ Ошибка мониторинга: {e}")


# ============================================================
# Запуск
# ============================================================

if __name__ == "__main__":
    main_once()



















