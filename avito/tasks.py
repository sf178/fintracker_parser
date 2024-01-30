from celery import shared_task
from .parser_cls import AvitoParse  # Импортируйте ваш парсер
import configparser
import re
from .city import *

config = configparser.ConfigParser()  # создаём объекта парсера
config.read("/Users/dmitrynekrylov/inmanage-back/glob_parse/settings.ini")  # читаем конфиг
try:
    """Багфикс проблем с экранированием"""
    url = config["Avito"]["URL"]  # начальный url
except Exception:
    with open('/Users/dmitrynekrylov/inmanage-back/glob_parse/settings.ini') as file:
        line_url = file.readlines()[1]
        regex = r"http.+"
        url = re.search(regex, line_url)[0]
num_ads = config["Avito"]["NUM_ADS"]
freq = config["Avito"]["FREQ"]
keys = config["Avito"]["KEYS"].split(', ')
max_price = config["Avito"].get("MAX_PRICE", "0") or "0"
min_price = config["Avito"].get("MIN_PRICE", "0") or "0"

@shared_task
def parse_avito_task(src, property_id, city, square):
    city_url = get_city(city)
    correct_url = url.replace('%city%', city_url)
    parser = AvitoParse(src=src, property_id=property_id, url=correct_url, geo=city, square=square,
                        count=int(num_ads), min_price=min_price, max_price=max_price, keysword_list=keys)
    parser.parse()

