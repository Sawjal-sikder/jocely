from django.urls import path
from .views import *

urlpatterns = [
    path('categories/', CategoryCreateListView.as_view(), name='category-list-create'),
    path('categories/<int:id>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # product URLs can be added later as needed
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/list/', ProductListView.as_view(), name='product-list'),
    path('products/<int:id>/', ProductDetailView.as_view(), name='product-detail'),
    
    # Review URLs can be added later as needed
    path('reviews/', ReviewCreateListView.as_view(), name='review-list-create'),
]