from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/categories/', views.get_categories, name='get_categories'),
    path('api/brands/', views.get_brands, name='get_brands'),
    path('api/models/', views.get_models, name='get_models'),
    path('api/variants/', views.get_variants, name='get_variants'),
    path('api/years/', views.get_years, name='get_years'),
]