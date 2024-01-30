import csv
import aiofiles
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


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
