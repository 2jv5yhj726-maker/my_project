#!/usr/bin/env python3
"""
tce_telegram_monitor.py
Мониторит tce.by/search.html по запросам SEARCH_TEXT и SEARCH_TEXT_2
и шлёт сообщение в Telegram, если кол-во найденных мероприятий
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


# -------- Настройки --------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "7348919449:AAEDdogDWEp1N75iYVPWrniojpirRYAsnJg")
CHAT_ID = os.getenv("CHAT_ID", "235204224")

SEARCH_TEXT = os.getenv("SEARCH_TEXT", "Записки юного врача")
SEARCH_TEXT_2 = os.getenv("SEARCH_TEXT_2", "На чёрной")

URL = os.getenv("URL", "https://tce.by/search.html")

# ожидаемые количества
EXPECTED_COUNT_1 = int(os.getenv("EXPECTED_COUNT_1", "4"))
EXPECTED_COUNT_2 = int(os.getenv("EXPECTED_COUNT_2", "2"))


# -------- Логи --------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("tce_monitor.log"),
        logging.StreamHandler()
    ]
)


# -------- Telegram --------

def send_telegram(text: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        r = requests.post(url, data=payload, timeout=15)
        r.raise_for_status()
        logging.info("Сообщение отправлено в Telegram.")
        return True
    except Exception as e:
        logging.exception("Ошибка отправки Telegram: %s", e)
        return False


# -------- Selenium --------

def get_driver():
    """Создаёт надежный драйвер для Windows, Linux и GitHub Actions."""
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,800")
    options.add_argument("--ignore-certificate-errors")

    # GitHub Actions — только headless
    if os.getenv("GITHUB_ACTIONS") == "true":
        options.add_argument("--headless=new")
    else:
        # На Windows лучше оставить headless включённым
        options.add_argument("--headless=new")

    # Selenium Manager автоматически скачает нужный драйвер
    driver = webdriver.Chrome(options=options)

    return driver


def get_count_with_selenium(search_text: str) -> int:
    """Возвращает количество найденных мероприятий по имени."""
    driver = None
    try:
        driver = get_driver()
        driver.get(URL)

        wait = WebDriverWait(driver, 20)

        input_box = wait.until(EC.presence_of_element_located((By.NAME, "tags")))
        input_box.clear()
        input_box.send_keys(search_text)

        reload_btn = driver.find_element(By.ID, "reload")
        reload_btn.click()

        try:
            wait_short = WebDriverWait(driver, 10)
            wait_short.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#playbill tbody tr"))
            )
        except TimeoutException:
            logging.info("[%s] Нет результатов -> 0", search_text)
            return 0

        rows = driver.find_elements(By.CSS_SELECTOR, "#playbill tbody tr")
        count = len(rows)

        logging.info("[%s] найдено %d мероприятий", search_text, count)

        return count

    except Exception as e:
        logging.exception("Ошибка Selenium при '%s': %s", search_text, e)
        raise

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


# -------- Основная логика --------

def main_once():
    alerts = []

    try:
        # первый запрос
        count1 = get_count_with_selenium(SEARCH_TEXT)
        if count1 != EXPECTED_COUNT_1:
            alerts.append(
                f"🔎 <b>{SEARCH_TEXT}</b>\n"
                f"Ожидалось: <b>{EXPECTED_COUNT_1}</b>, найдено: <b>{count1}</b>\n"
            )

        # второй запрос
        count2 = get_count_with_selenium(SEARCH_TEXT_2)
        if count2 != EXPECTED_COUNT_2:
            alerts.append(
                f"🔎 <b>{SEARCH_TEXT_2}</b>\n"
                f"Ожидалось: <b>{EXPECTED_COUNT_2}</b>, найдено: <b>{count2}</b>\n"
            )

        if alerts:
            msg = "⚠️ <b>Алерт мониторинга tce.by</b>\n\n" + "\n".join(alerts) + f"\n{URL}"
            send_telegram(msg)
        else:
            logging.info("Все значения соответствуют ожидаемым.")

    except Exception as e:
        logging.exception("Ошибка мониторинга: %s", e)
        send_telegram(f"❗ Ошибка мониторинга: {e}")


if __name__ == "__main__":
    main_once()
