# coding=utf-8
cities = {'Москва': 'moskva',
          'Санкт-Петербург': 'sankt-peterburg',
          'Астрахань': 'astrahan',
          'Барнаул': 'barnaul',
          'Волгоград': 'volgograd',
          'Воронеж': 'voronezh',
          'Екатеринбург': 'ekaterinburg',
          'Ижевск': 'izhevsk',
          'Иркутск': 'irkutsk',
          'Казань': 'kazan',
          'Калининград': 'kaliningrad',
          'Краснодар': 'krasnodar',
          'Красноярск': 'krasnoyarsk',
          'Набережные Челны': 'naberezhnye_chelny',
          'Нижний Новгород': 'nizhniy_novgorod',
          'Новосибирск': 'novosibirsk',
          'Омск': 'omsk',
          'Оренбург': 'orenburg',
          'Пермь':'perm',
          'Растов-на-Дону': 'rostov-na-donu',
          'Самара': 'samara',
          'Саратов': 'saratov',
          'Ставрополь': 'stavropol',
          'Тольятти': 'tolyatti',
          'Тула': 'tula',
          'Тюмень': 'tyumen',
          'Уьляновск': 'ulyanovsk',
          'Уфа': 'ufa',
          'Челябинск': 'chelyabinsk',
          'Ярославль': 'yaroslavl'}


def get_city(name):
    # Normalize the input to lowercase
    normalized_name = name.lower()

    # Iterate through the dictionary and compare normalized keys
    for city in cities:
        if city.lower() == normalized_name:
            return cities[city]

    # If the city is not found
    return None