from rest_framework import serializers
from django.db.models import Avg
from .models import *

class CategorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'is_active', 'created_at']
        read_only_fields = ['id']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['productCount'] = instance.products.count()
        return representation
        

# ProductSerializer can be added later as needed
class CreateProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        fields = ['id', 'category', 'name', 'description', 'image1', 'image2', 'image3', 'price', 'discount_price', 'type_of_product', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

        
class ProductListSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        fields = ['id', 'category', 'name', 'description', 'image1', 'image2', 'image3', 'price', 'discount_price', 'type_of_product', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['discount_percentage'] = instance.get_discount_percentage()
        representation['category'] = instance.category.name if instance.category else None
        representation['total_reviews'] = instance.reviews.count()
        representation['average_rating'] = instance.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0
        representation['reviews'] = SimpleReviewSerializer(instance.reviews.all(), many=True).data

        return representation
    

class SimpleReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'rating', 'comment']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'product', 'user', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        


class CartSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'product', 'product_name', 'quantity', 'added_at', 'updated_at', 'total_price']
        read_only_fields = ['id', 'user', 'added_at', 'updated_at', 'product_name', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()
    
