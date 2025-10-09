from rest_framework import serializers
from .models import Plan, Subscription

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"
        read_only_fields = ("stripe_price_id","stripe_product_id")
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert amount from cents to dollars
        monthly_amount = float(instance.amount) / 100
        representation['amount'] = monthly_amount
        
        # Calculate total cost based on interval_count
        total_cost = monthly_amount * instance.interval_count
        representation['total_cost'] = round(total_cost, 2)
        
        # Build price_display string
        representation['price_display'] = f"$ {monthly_amount}/month"
        
        return representation
        
class PlanUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["name", "interval","interval_count", "amount", "trial_days", "description", "active"]

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = (
            "user",
            "stripe_customer_id",
            "stripe_subscription_id",
            "status",
            "auto_renew",
            "trial_end",
            "current_period_end",
            "created_at",
            "updated_at",
        )


class SubscriptionListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscription
        fields = ['id', 'user', 'plan', 'status', 'auto_renew', 'trial_end', 'current_period_end', 'created_at']
        read_only_fields = (
            "user",
            "stripe_customer_id",
            "stripe_subscription_id",
            "status",
            "auto_renew",
            "trial_end",
            "current_period_end",
            "created_at",
            "updated_at",
        )
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = instance.user.full_name
        representation['plan'] = instance.plan.name
        return representation