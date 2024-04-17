
from django.urls import path
from .views import *

urlpatterns = [
    path('', calculate_average_price, name='parse_avito'),
    path('parse/', ParserView.as_view(), name='parse')
]