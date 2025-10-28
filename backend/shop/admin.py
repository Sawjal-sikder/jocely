from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Review, Cart, Order, OrderDetail
from django.contrib.auth import get_user_model
User = get_user_model()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'parent']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    ordering = ['name']
    prepopulated_fields = {}
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'parent')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discount_price', 'stock', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at', 'type_of_product']
    search_fields = ['name', 'description', 'type_of_product']
    list_editable = ['price', 'discount_price', 'stock', 'is_active']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'description', 'type_of_product')
        }),
        ('Images', {
            'fields': ('image1', 'image2', 'image3')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price', 'stock')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_discount_percentage_display(self, obj):
        percentage = obj.get_discount_percentage()
        if percentage > 0:
            return f"{percentage}%"
        return "No discount"
    get_discount_percentage_display.short_description = "Discount %"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at', 'product__category']
    search_fields = ['product__name', 'user__email', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('product', 'user', 'rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'get_total_price_display', 'added_at']
    list_filter = ['added_at', 'product__category']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['added_at', 'updated_at', 'get_total_price_display']
    ordering = ['-added_at']
    
    def get_total_price_display(self, obj):
        return f"${obj.get_total_price():.2f}"
    get_total_price_display.short_description = "Total Price"
    
    fieldsets = (
        (None, {
            'fields': ('user', 'product', 'quantity')
        }),
        ('Calculated Fields', {
            'fields': ('get_total_price_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class OrderDetailInline(admin.TabularInline):
    model = OrderDetail
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total', 'status', 'payment_method', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_status', 'created_at']
    search_fields = ['user__email', 'shipping_address', 'notes']
    list_editable = ['status', 'payment_status']
    readonly_fields = ['created_at', 'updated_at', 'total']
    ordering = ['-created_at']
    inlines = [OrderDetailInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'total', 'status')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('Shipping Information', {
            'fields': ('shipping_address', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_display(self, obj):
        colors = {
            'Pending': 'orange',
            'Processing': 'blue',
            'Shipped': 'purple',
            'Completed': 'green',
            'Cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_display.short_description = "Status"


@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'get_total_price']
    list_filter = ['order__status', 'product__category']
    search_fields = ['order__id', 'product__name']
    readonly_fields = ['get_total_price']
    ordering = ['-order__created_at']
    
    def get_total_price(self, obj):
        return f"${obj.quantity * obj.price:.2f}"
    get_total_price.short_description = "Total Price"
    
    fieldsets = (
        (None, {
            'fields': ('order', 'product', 'quantity', 'price')
        }),
        ('Calculated Fields', {
            'fields': ('get_total_price',),
            'classes': ('collapse',)
        }),
    )
