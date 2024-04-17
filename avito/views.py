import base64
import csv
import json
import configparser
import re

import aiofiles
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from avito.city import get_city
from avito.tasks import parse_avito_cars_task, parse_avito_prop_task


def generate_year_url_segment(year):
    year_dict = {"from": year, "to": year}
    year_json = json.dumps(year_dict)
    year_base64 = base64.urlsafe_b64encode(year_json.encode()).decode()
    # Убрать возможные '==' в конце, если они не нужны в URL
    year_base64 = year_base64.rstrip('=')
    return f"~{year_base64}"


def get_url(url, city):
    # Определение URL для запроса
    if city:
        city_url = get_city(city)  # Функция для преобразования города в часть URL
        correct_url = url.replace('%city%', city_url)
    else:
        correct_url = url  # Используем предоставленный URL, если город не указан

    return correct_url


class ParserView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        src = data.get('src')
        property_id = data.get('id', 0)
        count = int(data.get('count', 10))


        config = configparser.ConfigParser()
        keywords_list = []

        if src == 'auto':
            owner_count = data.get('owner_count', '')
            year = data.get('year', '')
            mark = data.get('mark', '')
            model = data.get('model', '')
             # создаём объекта парсера
            config.read("/app/avito/settings_cars.ini")  # читаем конфиг
            min_price = int(config["Avito"].get("MIN_PRICE", "0") or "0")
            max_price = int(config["Avito"].get("MAX_PRICE", "0") or "0")
            try:
                """Багфикс проблем с экранированием"""
                url = config["Avito"]["URL"]  # начальный url
            except Exception:
                with open('/app/avito/settings_cars.ini') as file:
                    line_url = file.readlines()[1]
                    regex = r"http.+"
                    url = re.search(regex, line_url)[0]
            if owner_count:
                owner_filters = {
                    '0': '',  # Без фильтра
                    '1-3': '?f=ASgBAgICAUSeEp64Ag',  # Один владелец
                    '4-6': '?f=ASgBAgICAUSeEqaqjQM'  # Не более трех
                }
                owner_filter_part = owner_filters.get(owner_count, '')
                if owner_filter_part:
                    url += owner_filter_part

            if year:
                year_segment = generate_year_url_segment(int(year))
                url += year_segment
            keywords_list = ['автомобиль', mark, model, year]  # Дополнительные ключевые слова можно включить
            if not (src and url and keywords_list):
                return Response({'error': 'Insufficient data to start parsing.'}, status=status.HTTP_400_BAD_REQUEST)
            parse_avito_cars_task.delay(
                src=src,
                property_id=property_id,
                url=url,
                # geo=city,
                # square=square,
                count=count,
                min_price=min_price,
                max_price=max_price,
                keywords_list=keywords_list
            )
        else:
            city = data.get('city', '')
            square = float(data.get('square', 0.0))
            config.read("/app/avito/settings_prop.ini")  # читаем конфиг
            min_price = int(config["Avito"].get("MIN_PRICE", "0") or "0")
            max_price = int(config["Avito"].get("MAX_PRICE", "0") or "0")
            try:
                """Багфикс проблем с экранированием"""
                url = config["Avito"]["URL"]  # начальный url
            except Exception:
                with open('/app/avito/settings_prop.ini') as file:
                    line_url = file.readlines()[1]
                    regex = r"http.+"
                    url = re.search(regex, line_url)[0]
            if city:
                url = get_url(url, city)

            keywords_list = config["Avito"]["KEYS"].split(', ')
            if not (src and url and keywords_list):
                return Response({'error': 'Insufficient data to start parsing.'}, status=status.HTTP_400_BAD_REQUEST)
            parse_avito_prop_task.delay(
                src=src,
                property_id=property_id,
                url=url,
                geo=city,
                square=square,
                count=count,
                min_price=min_price,
                max_price=max_price,
                keywords_list=keywords_list
            )
        return Response({'message': 'Parsing task has been started.'}, status=status.HTTP_202_ACCEPTED)

        # Проверка, достаточно ли данных для парсинга


        # Запуск задачи парсинга
        # parse_avito_task.delay(
        #     src=src,
        #     property_id=property_id,
        #     url=url,
        #     geo=city,
        #     square=square,
        #     count=count,
        #     min_price=min_price,
        #     max_price=max_price,
        #     keywords_list=keywords_list
        # )



@csrf_exempt
@require_http_methods(["POST"])
async def calculate_average_price(request):
    try:
        # Получение ID из тела запроса
        body = await request.body.decode()
        property_id = body.get('id')

        # Путь к файлу CSV
        file_path = f'result/result_id{property_id}.csv'

        # Асинхронное чтение файла
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
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

        return JsonResponse({'average_price': average_price})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
