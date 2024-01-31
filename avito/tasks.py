import json

import requests
from celery import shared_task
from .parser_cls import AvitoParse  # Импортируйте ваш парсер
import configparser
import re
from .city import *
from fintracker_parser.settings import env
import logging

config = configparser.ConfigParser()  # создаём объекта парсера
config.read("/app/avito/settings.ini")  # читаем конфиг

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



try:
    """Багфикс проблем с экранированием"""
    url = config["Avito"]["URL"]  # начальный url
except Exception:
    with open('/app/avito/settings.ini') as file:
        line_url = file.readlines()[1]
        regex = r"http.+"
        url = re.search(regex, line_url)[0]
num_ads = config["Avito"]["NUM_ADS"]
freq = config["Avito"]["FREQ"]
keys = config["Avito"]["KEYS"].split(', ')
max_price = config["Avito"].get("MAX_PRICE", "0") or "0"
min_price = config["Avito"].get("MIN_PRICE", "0") or "0"


def authenticate():
    """ Функция для аутентификации и получения токена. """
    auth_url = 'http://194.87.252.100/auth/login/'
    # username = os.getenv('SERVICE_USER')
    # password = os.getenv('SERVICE_PASSWORD')

    # Данные для отправки в теле запроса
    auth_data = {
        'phone_number': env('SERVICE_USER'),
        'password': env('SERVICE_PASSWORD')
    }

    try:
        auth_response = requests.post(auth_url, data=auth_data)
        auth_response.raise_for_status()
        return auth_response.json().get('access')
    except requests.RequestException as e:
        logger.error(f"Ошибка аутентификации: {e}")
        return None


@shared_task
def parse_avito_task(src, property_id, city, square):
    city_url = get_city(city)
    correct_url = url.replace('%city%', city_url)
    parser = AvitoParse(src=src, property_id=property_id, url=correct_url, geo=city, square=square,
                        count=int(num_ads), min_price=min_price, max_price=max_price, keysword_list=keys)
    parser.parse()


@shared_task
def currency_rates_task():
    api_key = 'db8d9f75688041cf831131e1b35655e3'  # Установите ваш API ключ
    currencies = ['EUR', 'GBP', 'JPY', 'CNY', 'USD']  # Выбранные валюты
    data_url = 'http://194.87.252.100/balance/currency/'

    # Аутентификация и получение токена
    auth_token = authenticate()
    if not auth_token:
        return {'error': 'Ошибка аутентификации'}
    data_to_send = []

    # Получение курсов валют
    rates_in_rub = get_rates_in_rub(api_key, currencies)
    if rates_in_rub:
        for currency in rates_in_rub:
            data_to_send.append({'name': currency, 'price': rates_in_rub[currency]})
        # data_to_send = [{'name': currency, 'price': rates_in_rub[currency]} for currency in rates_in_rub]

        try:
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = requests.post(data_url, json=data_to_send, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при отправке запроса: {e}")
            return {'error': str(e)}
    else:
        return {'error': 'Не удалось получить данные о курсах валют'}


def get_exchange_rates(api_key, base='USD'):
    url = f"https://openexchangerates.org/api/latest.json?app_id={api_key}&base={base}"
    response = requests.get(url)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        print("Ошибка при получении данных:", response.status_code)
        return None


def convert_to_rub(rates, rub_rate):
    converted_rates = {}
    for currency, rate in rates.items():
        # Пересчет курса валюты к RUB
        converted_rates[currency] = rub_rate / rate
    return converted_rates


def get_rates_in_rub(api_key, currencies):
    rates = get_exchange_rates(api_key)
    if rates:
        rub_exchange_rate = rates['rates']['RUB']
        rates_in_rub = convert_to_rub(rates['rates'], rub_exchange_rate)
        return {currency: rates_in_rub[currency] for currency in currencies}


