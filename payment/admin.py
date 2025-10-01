from django.contrib import admin
from .models import *
# Register your models here.
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "interval", "amount", "trial_days", "active")
    list_filter = ("interval", "active")
    search_fields = ("name",)
    
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "trial_end", "current_period_end", "created_at")
    list_filter = ("status", "plan")
    search_fields = ("user__username", "plan__name", "stripe_subscription_id")