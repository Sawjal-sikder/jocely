from django.urls import path
from .views import *

urlpatterns = [
    path('categories/', CategoryCreateListView.as_view(), name='category-list-create'),
    path('categories/<int:id>/', CategoryDetailView.as_view(), name='category-detail'),
]