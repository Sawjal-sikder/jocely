from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.shortcuts import render
from rest_framework import generics
from rest_framework import status
from .serializers import *
from .models import *

# Create your views here.
class CategoryCreateListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'id'
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Category deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Category updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
    
# Product views can be added later as needed
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = CreateProductSerializer

# product List view with pagination, filtering, and search
class CustomProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    pagination_class = CustomProductPagination
    search_fields = ['name', 'category__name']
    filterset_fields = ['category__name']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        category = self.request.query_params.get('category', None)
        search = self.request.query_params.get('search', None)

        if category:
            queryset = queryset.filter(category__name__iexact=category)
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset
    

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    lookup_field = 'id'
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Product deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Product updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
    
    
# Review views can be added later as needed
class ReviewCreateListView(generics.ListCreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    
    def get_queryset(self):
        queryset = Review.objects.all()
        product_id = self.request.query_params.get('product', None)

        if product_id:
            queryset = queryset.filter(product__id=product_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data.get('product')
        # Ensure a user can only review a product once
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        serializer.save(user=user)
        
        
class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return Cart.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data.get('product')
        quantity = serializer.validated_data.get('quantity', 1)

        # Prevent duplicates and handle quantity updates
        cart_item, created = Cart.objects.get_or_create(
            user=user, 
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Update the serializer instance to point to the cart_item
        serializer.instance = cart_item

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Build cart items manually
        cart_items = []
        for item in queryset:
            cart_items.append({
                'id': item.id,
                'product': item.product.name,
                'product_image': item.product.image1.url if item.product.image1 else None,
                'quantity': item.quantity,
                'unite_price': item.product.discount_price if item.product.discount_price else item.product.price,
                'total_price': item.get_total_price()
            })

        # Calculate grand total for all cart items
        grand_total = sum(item.get_total_price() for item in queryset)

        return Response({
            'cart_items': cart_items,
            'grand_total_price': round(grand_total, 2)
        })
