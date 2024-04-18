import os
import random
import time
import csv
import re

import aiofiles
import requests
from datetime import datetime, timedelta
from django.urls import reverse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from seleniumbase.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from django.urls import reverse
from fintracker_parser import settings
from selenium.webdriver.common.print_page_options import PrintOptions


from notifiers.logging import NotificationHandler
from seleniumbase import SB
from loguru import logger
from avito.locator import LocatorAvito
from avito.proxy import get_proxy
# from selenium import webdriver
# from webdriver_manager.chrome import ChromeDriverManager
#
# driver = webdriver.Chrome(ChromeDriverManager().install())



class AvitoParse:
    """
    Парсинг товаров на avito.ru
    """

    def __init__(self,
                 src: str,
                 url: str,
                 keysword_list: list,
                 count: int = 10,
                 property_id: int = 0,
                 max_price: int = 0,
                 min_price: int = 0,
                 geo: str = None,
                 square: float = 0.0,
                 debug_mode: int = 0
                 ):
        self.driver = None
        self.url = url
        self.sender = src
        self.keys_word = keysword_list
        self.count = count
        self.property_id = property_id
        self.data = []
        self.title_file = self.__get_file_title()
        self.max_price = int(max_price)
        self.min_price = int(min_price)
        self.geo = geo
        self.square = square
        self.debug_mode = debug_mode
        self.proxy_list = get_proxy()  # Получаем список прокси

    def __get_url(self):
        # for proxy in self.proxy_list:
        try:
                # print('op')
                # self._setup_driver_with_proxy()  # Настроим драйвер с прокси
                # print('zaloopa1')
              # Используйте get вместо open
            self.driver.get(self.url)
            # time.sleep(60)
            logger.info(f'Ссылка: {self.url}')
            search = self.driver.find_element(By.CSS_SELECTOR, "[data-marker='search-form/suggest']")
            search.send_keys(f'{self.keys_word[0]} {self.keys_word[1]} {self.keys_word[2]}')
            search_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-marker='search-form/submit-button']")
            search_btn.click()
            self.driver.open_new_window()  # сразу открываем и вторую вкладку
            self.driver.switch_to_window(window=0)
        # if "Доступ ограничен" not in self.driver.title:
            #     pass  # Успешное подключение, выходим из цикла
        except Exception as error:
            logger.error(f"Ошибка при подключении: {error}")

    def _setup_driver_with_proxy(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Добавить headless режим
            # chrome_options.add_argument("--no-sandbox")  # Решение проблем с правами
            # chrome_options.add_argument("--disable-dev-shm-usage")  # Решение проблем с правами
            # chrome_options.add_argument("--disable-gpu")  # Решение проблем с правами
            # chrome_options.add_argument("--disable-extensions")  # Решение проблем с правами

            service = Service(executable_path=ChromeDriverManager().install())
            # chrome_options.add_argument(f'--proxy-server={proxy}')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print('opana')
        except Exception as e:
            print(f"Ошибка при инициализации драйвера: {e}")

    def __paginator(self):
        """Кнопка далее"""
        logger.info('Страница успешно загружена. Просматриваю объявления')
        # page = self.driver.print_page()
        # with open('page.html', mode='w', encoding='utf-8') as f:
        #     f.write(page)
        # logger.info('Заголовок страницы:', page)
        self.__create_file_csv()
        while self.count > 0:
            self.__parse_page()
            time.sleep(random.randint(5, 7))
            """Проверяем есть ли кнопка далее"""
            if self.driver.find_elements(*LocatorAvito.NEXT_BTN):
                self.driver.find_element(*LocatorAvito.NEXT_BTN).click()
                self.count -= 1
                logger.debug("Следующая страница")
            else:
                logger.info("Нет кнопки дальше")
                break

    @logger.catch
    def __parse_page(self):
        """Парсит открытую страницу"""

        """Ограничение количества просмотренных объявлений"""
        if os.path.isfile('viewed.txt'):
            with open('viewed.txt', 'r') as file:
                self.viewed_list = list(map(str.rstrip, file.readlines()))
                if len(self.viewed_list) > 5000:
                    self.viewed_list = self.viewed_list[-900:]
        else:
            with open('viewed.txt', 'w') as file:
                self.viewed_list = []
        # titles = self.driver.find_elements(By.CSS_SELECTOR,'div[data-marker="item"]')
        # elements = WebDriverWait(self.driver, 10).until(
        #     EC.presence_of_all_elements_located((By.CSS_SELECTOR,'data-marker="item"'))
        # )
        # print(elements)

        titles = self.driver.find_elements(By.CSS_SELECTOR, "[data-marker='item']")

        # titles = self.driver.find_elements(*LocatorAvito.TITLES)
        for title in titles:
            name = title.find_element(*LocatorAvito.NAME).text

            if title.find_elements(*LocatorAvito.DESCRIPTIONS):
                description = title.find_element(*LocatorAvito.DESCRIPTIONS).text
            else:
                description = ''

            url = title.find_element(*LocatorAvito.URL).get_attribute("href")
            price = title.find_element(*LocatorAvito.PRICE).get_attribute("content")
            ads_id = title.get_attribute("data-item-id")

            if self.is_viewed(ads_id):
                continue
            self.viewed_list.append(ads_id)
            data = {
                'name': name,
                'description': description,
                'url': url,
                'price': price
            }
            """Определяем нужно ли нам учитывать ключевые слова"""
            if self.keys_word != ['']:

                if any([item.lower() in (description.lower() + name.lower()) for item in self.keys_word]) \
                        and \
                        self.min_price <= int(price) <= self.max_price:
                    parsed_data = self.__parse_full_page(url, data)
                    if parsed_data.get("is_within_range", False):
                        self.data.append(parsed_data)
                    """Проверка адреса если нужно"""
                    if self.geo and self.geo.lower() not in self.data[-1].get("geo", self.geo.lower()):
                        continue
                    """Отправляем в телеграм"""
                    self.__pretty_log(data=data)
                    self.__save_data(data=data)
            elif self.min_price <= int(price) <= self.max_price:

                self.data.append(self.__parse_full_page(url, data))

                """Проверка адреса если нужно"""
                if self.geo and self.geo.lower() not in self.data[-1].get("geo", self.geo.lower()):
                    continue
                """Отправляем в телеграм"""
                self.__pretty_log(data=data)
                self.__save_data(data=data)
            else:
                continue

    def __pretty_log(self, data):
        """Красивый вывод"""
        logger.success(
            f'Название: {data.get("name", "-")}\n'
            f'Цена: {data.get("price", "-")}\n'
            f'Описание: {data.get("description", "-")}\n'
            f'Просмотров: {data.get("views", "-")}\n'
            f'Дата публикации: {data.get("date_public", "-")}\n'
            f'Продавец: {data.get("seller_name", "-")}\n'
            f'Ссылка: {data.get("url", "-")}\n'
            f'About: {data.get("about_prop", "-")}')

    def wait_for_page_load(self, timeout=30):
        try:
            # Ожидаем, пока состояние документа станет 'complete'
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.debug("Страница полностью загружена.")
        except TimeoutException:
            logger.error("Превышено время ожидания загрузки страницы.")

    def parse_date(self, date_str):
        now = datetime.now()

        if "сегодня" in date_str:
            time_part = re.search(r'(\d{2}:\d{2})', date_str)
            if time_part:
                time_str = time_part.group(0)
                date_str = now.strftime("%Y-%m-%d ") + time_str
        elif "вчера" in date_str:
            yesterday = now - timedelta(days=1)
            time_part = re.search(r'(\d{2}:\d{2})', date_str)
            if time_part:
                time_str = time_part.group(0)
                date_str = yesterday.strftime("%Y-%m-%d ") + time_str
        else:
            # Добавляем ноль перед месяцем, если необходимо
            match = re.search(r'(\d+)\s+(\w+)\s+в\s+(\d{2}:\d{2})', date_str)
            if match:
                day, month_str, time = match.groups()
                months = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
                          'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
                          'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'}
                month = months.get(month_str.lower())
                if month:
                    date_str = f"{now.year}-{month}-{day.zfill(2)} {time}"
                else:
                    raise ValueError(f"Неизвестное название месяца: {month_str}")

        return datetime.strptime(date_str, "%Y-%m-%d %H:%M")

    def __extract_square_footage(self, square_footage_str: str) -> float:
        match = re.search(r"(\d+(?:\.\d+)?)\s*м²", square_footage_str)
        if match:
            return float(match.group(1))
        return 0

    def __parse_full_page(self, url: str, data: dict) -> dict:

        """Парсит для доп. информации открытое объявление на отдельной вкладке"""

        # Получаем идентификаторы всех открытых окон
        # windows = self.driver.window_handles

        # Переключаемся на второе окно (если оно есть) или открываем новое
        # if len(windows) > 1:
        #     self.driver.switch_to.window(windows[1])
        # else:
        #     self.driver.execute_script("window.open();")
        #     self.driver.switch_to.window(self.driver.window_handles[1])
        self.driver.switch_to_window(window=1)

        self.driver.get(url)

        """Если не дождались загрузки"""
        try:

            self.wait_for_page_load(timeout=15)
            logger.debug("Страница полностью загружена.")

        except Exception:
            """Проверка на бан по ip"""
            if "Доступ ограничен" in self.driver.title:
                logger.success("Доступ ограничен: проблема с IP. \nПоследние объявления будут без подробностей")

            # Возвращаемся на первое окно
            self.driver.switch_to.window(window=0)
            logger.debug("Не дождался загрузки страницы")
#            return data

        """Гео"""
        try:
            if self.geo and self.driver.find_elements(*LocatorAvito.GEO):
                geo = self.driver.find_element(*LocatorAvito.GEO).text
                data["geo"] = geo.lower()
                logger.debug(f"Гео: {data['geo']}")
        except NoSuchElementException:
            logger.error("Элемент ГЕО не найден")

        """Количество просмотров"""
        try:
            if self.driver.find_elements(*LocatorAvito.TOTAL_VIEWS):

                total_views = self.driver.find_element(*LocatorAvito.TOTAL_VIEWS).text.split()[0]
                data["views"] = total_views
                logger.debug(f"Просмотры: {data['views']}")
        except NoSuchElementException:
            logger.error("Элемент Просмотры не найден")

        """Дата публикации"""
        try:
            if self.driver.find_elements(*LocatorAvito.DATE_PUBLIC):
                date_public = self.driver.find_element(*LocatorAvito.DATE_PUBLIC).text
                if "· " in date_public:
                    date_public = date_public.replace("· ", '')
                date_public = self.parse_date(date_public)
                data["date_public"] = date_public
                logger.debug(f"Дата: {data['date_public']}")
        except NoSuchElementException:
            logger.error("Элемент Дата не найден")

        """Имя продавца"""
        try:
            if self.driver.find_elements(*LocatorAvito.SELLER_NAME):
                seller_name = self.driver.find_element(*LocatorAvito.SELLER_NAME).text
                data["seller_name"] = seller_name
                logger.debug(f"Имя продавца: {data['seller_name']}")
        except NoSuchElementException:
            logger.error("Элемент Имя продавца не найден")

        """Информация о помещении"""
        try:
            try:
                about_prop_element = self.driver.find_element(*LocatorAvito.ABOUT_PROP)
                about_prop_items = about_prop_element.find_elements(By.XPATH,
                                                                    ".//li[contains(@class, 'params-paramsList__item-')]")
                about_prop_data = {}
                for item in about_prop_items:
                    try:
                        header_element = item.find_element(By.XPATH, ".//span[contains(@class, 'desktop-')]")
                        header = header_element.text
                        text = item.text[len(header):].strip()
                        key = header.lower().replace('\xa0', ' ').strip(': ')
                        value = text.lower().replace('\xa0', ' ')
                        about_prop_data[key] = value
                        logger.debug(f"Обработан элемент о помещении: {key} - {value}")
                    except NoSuchElementException:
                        logger.error("Не удалось обработать элемент списка о помещении")
                data["about_prop"] = about_prop_data
            except NoSuchElementException:
                logger.error("Элемент О помещении не найден")
            about_prop = data.get("about_prop", {})
            square_footage_str = about_prop.get("общая площадь", "")
            square_footage = self.__extract_square_footage(square_footage_str)

            if square_footage:
                # Check if the square footage is within the specified range
                if self.square - 20 <= square_footage <= self.square + 20:
                    data["is_within_range"] = True
                else:
                    data["is_within_range"] = False
            else:
                data["is_within_range"] = False
        except Exception as e:
            logger.error(e)
        """Возвращается на вкладку №1"""
        self.driver.switch_to_window(window=0)
        return data

    def is_viewed(self, ads_id: str) -> bool:
        """Проверяет, смотрели мы это или нет"""
        if ads_id in self.viewed_list:
            return True
        return False

    def __save_data(self, data: dict):
        with open(f"result/{self.title_file}.csv", mode="a", newline='', encoding='utf-8', errors='ignore') as file:
            writer = csv.writer(file)
            writer.writerow([
                data.get("name", '-'),
                data.get("price", '-'),
                data.get("url", '-'),
                data.get("description", '-'),
                data.get("views", '-'),
                data.get("date_public", '-'),
                data.get("seller_name", 'no'),
                data.get("geo", '-'),
                # Добавляем новое поле
                str(data.get("about_prop", {}))  # Преобразуем словарь в строку для сохранения в CSV
            ])

        """сохраняет просмотренные объявления"""
        with open('viewed.txt', 'w') as file:
            for item in set(self.viewed_list):
                file.write("%s\n" % item)

    @property
    def __is_csv_empty(self) -> bool:
        """Пустой csv или нет"""
        os.makedirs(os.path.dirname("result/"), exist_ok=True)
        try:
            with open(f"result/{self.title_file}.csv", 'r', encoding='utf-8', errors='ignore') as file:
                reader = csv.reader(file)
                try:
                    # Попытка чтения первой строки
                    first_row = next(reader)
                except StopIteration:
                    # файл пустой
                    return True
                return False
        except FileNotFoundError:
            return True

    @logger.catch
    def __create_file_csv(self):
        if self.__is_csv_empty:
            with open(f"result/{self.title_file}.csv", 'a', encoding='utf-8', errors='ignore') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Название",
                    "Цена",
                    "Ссылка",
                    "Описание",
                    "Просмотров",
                    "Дата публикации",
                    "Продавец",
                    "Адрес",
                    "О помещении"  # Новый заголовок
                ])

    # def send_file_name_to_server(self):
    #     # Создание полного URL с использованием reverse
    #     url_path = reverse('your_view_name')  # 'your_view_name' - это имя вашей view-функции в urls.py
    #     full_url = f"http://web:8000/{url_path}"  # SITE_URL должен быть определен в settings.py
    #
    #     data = {'id': self.id}
    #     response = requests.post(full_url, data=data)
    #     if response.status_code == 200:
    #         logger.info("File name sent successfully.")
    #     else:
    #         logger.error(f"Error sending file name: {response.status_code}")

    def __get_file_title(self) -> str:
        """Определяет название файла"""
        # if self.keys_word != ['']:
        #     title_file = "-".join(list(map(str.lower, self.keys_word)))
        #
        # else:
        #     title_file = 'all'
        title_file = f'result_{self.sender}_{self.property_id}'
        return title_file

    @logger.catch
    async def count_average(self):
        async with aiofiles.open(self.title_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            total_price = 0
            count = 0
            async for row in reader:
                if count == 0:  # Пропуск заголовка
                    count += 1
                    continue
                price = float(row[1])  # Предполагается, что цена находится во втором столбце
                if price > 10:
                    total_price += price
                    count += 1

        # Вычисление средней цены
        if count > 1:
            average_price = total_price / (count - 1)
        else:
            average_price = 0

        update_url = f"http://web/{self.sender}/properties/up/{self.property_id}"  # Укажите здесь URL вашего API
        response = requests.patch(update_url, json={'actual_price': average_price})

        if response.status_code == 200:
            logger.success("Property updated successfully.")
        else:
            logger.warning(f"Error updating property: {response.status_code}")

    def parse(self):
        """Метод для вызова"""
        # with SB(uc=True,
        #         # headed=True if self.debug_mode else False,
        #         headless=True,
        #         page_load_strategy="eager",
        #         block_images=True
        #         #skip_js_waits=True,
        #         ) as self.driver:

        selenium_url = "http://selenium:4444/wd/hub"

        # Настройка опций для Chrome
        from selenium.webdriver.chrome.options import Options
        options = Options()
        if self.debug_mode:
            options.headless = False  # Если в debug режиме, отключаем headless
        else:
            options.headless = True  # Включаем headless режим
        options.set_capability('platformName', 'ANY')        # Дополнительные настройки, если требуются
        # options.add_argument("--disable-gpu")  # Если есть проблемы с производительностью
        # options.add_argument("window-size=1200x600")  # Задаем размер окна

        # Подключаемся к Selenium Server
        self.driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options
        )
        # self._setup_driver_with_proxy()
        try:
            self.__get_url()
            self.__paginator()

        except Exception as error:
            print({error})
                    #logger.error(f"Ошибка: {error}")


# if __name__ == '__main__':
#     """Здесь заменить данные на свои"""
#     import configparser
#
#     config_cars = configparser.ConfigParser()  # создаём объекта парсера
#     config_cars.read("settings_cars.ini")  # читаем конфиг
#
#     try:
#         """Багфикс проблем с экранированием"""
#         url = config_cars["Avito"]["URL"]  # начальный url
#     except Exception:
#         with open('settings_cars.ini') as file:
#             line_url = file.readlines()[1]
#             regex = r"http.+"
#             url = re.search(regex, line_url)[0]
#     # chat_id = config_prop["Avito"]["CHAT_ID"]
#     # token = config_prop["Avito"]["TG_TOKEN"]
#     num_ads = config_cars["Avito"]["NUM_ADS"]
#     freq = config_cars["Avito"]["FREQ"]
#     # keys = config_cars["Avito"]["KEYS"]
#     max_price = config_cars["Avito"].get("MAX_PRICE", "0") or "0"
#     min_price = config_cars["Avito"].get("MIN_PRICE", "0") or "0"
#     geo = config_cars["Avito"].get("GEO", "") or ""
#
#     # if token and chat_id:
#     #     params = {
#     #         'token': token,
#     #         'chat_id': chat_id
#     #     }
#     #     tg_handler = NotificationHandler("telegram", defaults=params)
#     #
#     #     """Все логи уровня SUCCESS и выше отсылаются в телегу"""
#     #     logger.add(tg_handler, level="SUCCESS", format="{message}")
#
#     while True:
#         try:
#             print('start parsing')
#             AvitoParse(
#                 src='auto',
#                 url=url,
#                 count=int(num_ads),
#                 keysword_list=['автомобиль', 'mercedes', 'w124', '1996'],
#                 max_price=int(max_price),
#                 min_price=int(min_price),
#             ).parse()
#             print('started')
#             logger.info("Пауза")
#             time.sleep(int(freq) * 60)
#         except Exception as error:
#             logger.error(error)
#             logger.error('Произошла ошибка, но работа будет продолжена через 30 сек. '
#                          'Если ошибка повторится несколько раз - перезапустите скрипт.'
#                          'Если и это не поможет - обратитесь к разработчику по ссылке ниже')
#             time.sleep(30)

# while True:
#     AvitoParse(src='auto', url='https://www.avito.ru/all/avtomobili', property_id=123, keysword_list=['автомобиль', 'bmw', 'e34', '1995']).parse()