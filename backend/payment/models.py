from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Plan(models.Model):
    Interval_choices = (("day", "day"),
                        ("week", "week"), 
                        ("month", "month"), 
                        ("year", "year"))
    
    name = models.CharField(max_length=50, unique=True)
    stripe_product_id = models.CharField(max_length=255, blank=True, null=True)  
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.PositiveIntegerField(default=0, help_text="Amount in cents")  
    interval = models.CharField(max_length=20, choices=Interval_choices, default="month")
    interval_count = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)
    trial_days = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['amount']
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"

    def __str__(self):
        return (
            f"{self.name} "
            f"({self.interval_count} {self.get_interval_display()}{'s' if self.interval_count > 1 else ''}) "
            f"- ${self.amount / 100:.2f}"
        )

    def stripe_recurring(self):
        return {
            "interval": self.interval,
            "interval_count": self.interval_count,
        }



class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=50, 
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("trialing", "Trialing"),
            ("active", "Active"),
            ("past_due", "Past Due"),
            ("canceled", "Canceled"),
            ("unpaid", "Unpaid")
        ]
    )  # pending → trialing → active → canceled
    trial_end = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        return self.status in ["active"]

    def is_trial(self):
        """Check if subscription is in trial period"""
        from django.utils import timezone
        if not self.trial_end:
            return False
        return (
            self.status in ["trialing", "active"] and 
            self.trial_end > timezone.now()
        )



    def is_paid_active(self):
        return self.status == "active"
    
    def is_trialing(self):
        return self.status == "trialing"

    @classmethod
    def get_user_active_subscription(cls, user):
        """Get user's active subscription active or on trial"""
        return cls.objects.filter(
            user=user, 
            status__in=['active', 'trialing']
        ).first()

    def __str__(self):
        return f"{self.user} - {self.plan.name if self.plan else 'N/A'} ({self.status})"



class WebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=255)
    data = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.event_id}"
