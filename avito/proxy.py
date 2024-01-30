import requests
from bs4 import BeautifulSoup

def get_html(url, proxy=None):
    try:
        if proxy:
            proxies = {"http": proxy, "https": proxy}
            response = requests.get(url, proxies=proxies)
        else:
            response = requests.get(url)
        response.raise_for_status()  # вызывает исключение для статусов 4xx/5xx
        return response.text
    except requests.RequestException as e:
        print(f"Ошибка при запросе {url} с прокси {proxy}: {e}")
        return None

def get_list_ip(html):
    soup = BeautifulSoup(html, "lxml")
    list_ip = []
    elements = soup.find("tbody").find_all("tr")
    for element in elements:
        ip = element.find_all("td")[0].text
        port = element.find_all("td")[1].text
        proxy = "{}:{}".format(ip, port)
        list_ip.append(proxy)
    return list_ip

def get_proxy():
    """ Функция возвращает список https прокси. """
    url = "https://www.sslproxies.org/"
    html = get_html(url)
    if html:
        return get_list_ip(html)
    return []

def fetch_url_with_proxy_rotation(url):
    proxy_list = get_proxy()
    for proxy in proxy_list:
        html = get_html(url, proxy=proxy)
        if html:
            return html
    print("Не удалось получить данные с использованием прокси.")
    return None