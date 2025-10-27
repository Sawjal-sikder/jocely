import stripe
import datetime
import logging
from django.conf import settings
from django.utils.timezone import make_aware
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from django.contrib.auth import get_user_model

from .models import *
from .serializers import *
import os
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

User = get_user_model()

def calculate_current_period_end(plan, start_date=None):
    """
    Calculate the current period end date based on plan interval
    
    Args:
        plan: Plan object containing interval and interval_count
        start_date: Starting date (defaults to current time)
    
    Returns:
        datetime: The calculated end date for the current period
    """
    if not start_date:
        start_date = timezone.now()
    
    if plan.interval == "day":
        return start_date + datetime.timedelta(days=plan.interval_count)
    elif plan.interval == "week":
        return start_date + datetime.timedelta(weeks=plan.interval_count)
    elif plan.interval == "month":
        # For monthly subscriptions, add approximately 30 days per month
        # You could also use dateutil.relativedelta for more accurate month calculations
        return start_date + datetime.timedelta(days=30 * plan.interval_count)
    elif plan.interval == "year":
        return start_date + datetime.timedelta(days=365 * plan.interval_count)
    else:
        # Default fallback - 30 days
        return start_date + datetime.timedelta(days=30)

def process_referral_benefits(user, subscription):
    """
    Process referral benefits when a user purchases a subscription.
    
    Args:
        user: The user who purchased the subscription
        subscription: The subscription object
    """
    try:
        logger.info(f"Processing referral benefits for user {user.id}")
        
        # Check if the user was referred by someone
        if user.referred_by:
            try:
                # Find the referrer
                referrer = User.objects.get(referral_code=user.referred_by)
                logger.info(f"Found referrer {referrer.id} for user {user.id}")
                
                # Use current time if current_period_end is not available
                base_time = subscription.current_period_end or timezone.now()
                logger.info(f"Using base time: {base_time}")
                
                # Calculate benefit duration (e.g., 30 days from subscription end)
                benefit_duration = datetime.timedelta(days=30)
                
                # Grant benefits to the referrer
                referrer.is_unlimited = True
                referrer.package_expiry = base_time + benefit_duration
                referrer.save()
                logger.info(f"Granted unlimited access to referrer {referrer.id} until {referrer.package_expiry}")
                
                # Grant benefits to the referee (the purchaser)
                bonus_duration = datetime.timedelta(days=7)
                user.is_unlimited = True
                user.package_expiry = base_time + bonus_duration
                user.save()
                logger.info(f"Granted bonus unlimited access to referee {user.id} until {user.package_expiry}")
                
            except User.DoesNotExist:
                logger.warning(f"Referrer with code {user.referred_by} not found for user {user.id}")
            except Exception as inner_e:
                logger.error(f"Error processing referrer benefits: {str(inner_e)}")
                
        else:
            logger.info(f"User {user.id} was not referred by anyone, skipping referral benefits")
            
    except Exception as e:
        logger.error(f"Error processing referral benefits for user {user.id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer


class PlanListCreateView(generics.ListCreateAPIView):
    queryset = Plan.objects.filter(active=True)
    serializer_class = PlanSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # Convert amount from USD to cents
        try:
            data["amount"] = int(float(data.get("amount", 0)) * 100)
        except ValueError:
            return Response({"error": "Invalid amount format"}, status=status.HTTP_400_BAD_REQUEST)

        name = data.get("name")
        interval = data.get("interval")
        interval_count = int(data.get("interval_count", 1))
        description = data.get("description", "")
        amount = data.get("amount")
        trial_days = int(data.get("trial_days", 0))

        if not all([name, interval, amount]):
            return Response({"error": "name, interval, amount required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create product on Stripe
            product = stripe.Product.create(
                name=name,
                description=description
            )

            # Create price on Stripe
            price = stripe.Price.create(
                product=product.id,
                unit_amount=amount,
                currency="usd",
                recurring={
                    "interval": interval,
                    "interval_count": interval_count,
                },
            )

            # Save to DB
            plan = Plan.objects.create(
                name=name,
                stripe_product_id=product.id,
                stripe_price_id=price.id,
                amount=amount,
                interval=interval,
                interval_count=interval_count,
                description=description,
                trial_days=trial_days,
                active=True,
            )

            serializer = self.get_serializer(plan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PlanUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanUpdateSerializer
    lookup_field = "id"

    def perform_update(self, serializer):
        plan = self.get_object()
        old_amount = getattr(plan, "amount", None)

        # Save all updated fields to DB first
        updated_plan = serializer.save()

        try:
            # Update Stripe Product name
            stripe.Product.modify(
                plan.stripe_product_id,
                name=updated_plan.name
            )

            # If amount changed, create a new Stripe Price
            if "amount" in self.request.data and int(self.request.data["amount"]) != old_amount:
                new_price = stripe.Price.create(
                    product=plan.stripe_product_id,
                    unit_amount=int(self.request.data["amount"]),
                    currency="usd",
                    recurring={
                        "interval": updated_plan.interval,
                        "interval_count": updated_plan.interval_count
                    }
                )
                updated_plan.stripe_price_id = new_price.id
                updated_plan.save()

        except Exception as e:
            # Log error but don't block update
            print("Stripe update error:", e)


class CreateSubscriptionView(APIView):
    def post(self, request):
        plan_id = request.data.get("plan_id")  
        success_url = request.data.get(
            "success_url",
            f"{request.build_absolute_uri('/api/payment/payment-success/')}"
        )
        cancel_url = request.data.get(
            "cancel_url",
            f"{request.build_absolute_uri('/api/payment/payment-cancel/')}"
        )
        
        try:
            plan = Plan.objects.get(pk=plan_id, active=True)
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=404)

        # Check if user already has an active subscription or trial
        existing_subscription = Subscription.get_user_active_subscription(request.user)
        
        if existing_subscription:
            error_data = {
                "current_plan": existing_subscription.plan.name if existing_subscription.plan else "Unknown",
                "status": existing_subscription.status,
                "subscription_id": existing_subscription.id
            }
            
            if existing_subscription.is_trial():
                error_data.update({
                    "error": "You already have an active trial period",
                    "message": "You cannot create a new subscription while your trial is active",
                    "trial_end": existing_subscription.trial_end
                })
            elif existing_subscription.is_paid_active():
                error_data.update({
                    "error": "You already have an active subscription",
                    "message": "You cannot create a new subscription while you have an active plan",
                    "current_period_end": existing_subscription.current_period_end
                })
            
            return Response(error_data, status=400)

        try:
            # ✅ Create or get Stripe customer
            existing_sub = Subscription.objects.filter(user=request.user).first()
            
            if existing_sub and existing_sub.stripe_customer_id:
                # Use existing customer
                customer_id = existing_sub.stripe_customer_id
                customer = stripe.Customer.retrieve(customer_id)
            else:
                # Create new customer
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=getattr(request.user, "full_name", None) or request.user.email,
                    metadata={
                        "user_id": request.user.id,
                        "plan_id": plan.id
                    }
                )

            # ✅ Prepare subscription_data
            subscription_data = {
                "metadata": {
                    "user_id": request.user.id,
                    "plan_id": plan.id,
                }
            }

            # Only add trial if it's > 0
            if plan.trial_days and plan.trial_days > 0:
                subscription_data["trial_period_days"] = plan.trial_days

            # ✅ Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                subscription_data=subscription_data,
                metadata={
                    'user_id': request.user.id,
                    'plan_id': plan.id,
                },
                automatic_tax={'enabled': False},  # Optional
                allow_promotion_codes=True,
            )

            # ✅ Save pending subscription in DB (will be updated by webhook)
            # Calculate initial current_period_end based on plan
            initial_current_period_end = calculate_current_period_end(plan)
            
            subscription = Subscription.objects.create(
                user=request.user,
                plan=plan,
                stripe_customer_id=customer.id,
                stripe_subscription_id=None,  # Will be set by webhook
                status="pending",  # Will be updated by webhook
                trial_end=None,  # Will be set by webhook
                current_period_end=initial_current_period_end,  # Set initial value, will be updated by webhook
            )

            return Response({
                "checkout_url": checkout_session.url,
                "checkout_session_id": checkout_session.id,
                "subscription_id": subscription.id,
                "plan": plan.name,
                "trial_days": plan.trial_days if plan.trial_days > 0 else None,
                "message": (
                    f"Redirecting to Stripe checkout with {plan.trial_days} days trial period"
                    if plan.trial_days > 0 else
                    "Redirecting to Stripe checkout without trial"
                )
            }, status=201)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=400)
        except KeyError as e:
            return Response({"error": f"Missing field: {str(e)}"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=400)



class CheckoutSessionStatusView(APIView):
    """Check the status of a Stripe checkout session"""
    def get(self, request):
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response({"error": "session_id is required"}, status=400)
        
        try:
            # Retrieve the checkout session from Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid' and session.subscription:
                # Get the subscription from Stripe
                stripe_subscription = stripe.Subscription.retrieve(session.subscription)
                
                # Update our database subscription
                user_id = session.metadata.get('user_id')
                if user_id:
                    subscription = Subscription.objects.filter(
                        user_id=user_id,
                        status='pending'
                    ).first()
                    
                    if subscription:
                        subscription.stripe_subscription_id = stripe_subscription.id
                        subscription.status = stripe_subscription.status
                        subscription.trial_end = make_aware(
                            datetime.datetime.fromtimestamp(stripe_subscription.trial_end)
                        ) if stripe_subscription.trial_end else None
                        subscription.current_period_end = make_aware(
                            datetime.datetime.fromtimestamp(stripe_subscription.current_period_end)
                        ) if stripe_subscription.current_period_end else None
                        subscription.save()
                        
                        return Response({
                            "success": True,
                            "subscription": {
                                "id": subscription.id,
                                "status": subscription.status,
                                "trial_end": subscription.trial_end,
                                "current_period_end": subscription.current_period_end,
                                "plan_name": subscription.plan.name
                            }
                        }, status=200)
            
            return Response({
                "success": False,
                "payment_status": session.payment_status,
                "session_status": session.status
            }, status=200)
            
        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class UserSubscriptionStatusView(APIView):
    """Get current user's subscription status"""
    def get(self, request):
        try:
            active_subscription = Subscription.get_user_active_subscription(request.user)
            
            if not active_subscription:
                return Response({
                    "has_subscription": False,
                    "message": "No active subscription found"
                }, status=200)
            
            return Response({
                "has_subscription": True,
                "subscription": {
                    "id": active_subscription.id,
                    "plan_name": active_subscription.plan.name if active_subscription.plan else "Unknown",
                    "status": active_subscription.status,
                    "is_trial": active_subscription.is_trial(),
                    "is_paid_active": active_subscription.is_paid_active(),
                    "trial_end": active_subscription.trial_end,
                    "current_period_end": active_subscription.current_period_end,
                    "created_at": active_subscription.created_at
                }
            }, status=200)
            
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class PaymentSuccessView(APIView):
    permission_classes = [permissions.AllowAny]
    """Handle successful payment completion"""
    def get(self, request):
        return Response({"message": "Payment successful"}, status=200)


class PaymentCancelView(APIView):
      permission_classes = [permissions.AllowAny]
      """Handle cancelled payment"""
      def get(self, request):
            return Response({"message": "Payment cancel"}, status=200)


class TestReferralBenefitsView(APIView):
    """Test endpoint to verify referral benefits functionality"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Test referral benefits processing
        Usage: POST /api/payment/test-referral-benefits/
        Body: {"subscription_id": <subscription_id>}
        """
        subscription_id = request.data.get("subscription_id")
        
        if not subscription_id:
            return Response({"error": "subscription_id is required"}, status=400)
        
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            
            # Process referral benefits for testing
            process_referral_benefits(subscription.user, subscription)
            
            # Return current user status
            user = subscription.user
            referrer = None
            if user.referred_by:
                try:
                    referrer = User.objects.get(referral_code=user.referred_by)
                except User.DoesNotExist:
                    pass
            
            return Response({
                "message": "Referral benefits processed successfully",
                "purchaser": {
                    "id": user.id,
                    "email": user.email,
                    "is_unlimited": user.is_unlimited,
                    "package_expiry": user.package_expiry,
                    "referred_by": user.referred_by
                },
                "referrer": {
                    "id": referrer.id if referrer else None,
                    "email": referrer.email if referrer else None,
                    "is_unlimited": referrer.is_unlimited if referrer else None,
                    "package_expiry": referrer.package_expiry if referrer else None,
                    "referral_code": referrer.referral_code if referrer else None
                } if referrer else None,
                "subscription": {
                    "id": subscription.id,
                    "status": subscription.status,
                    "current_period_end": subscription.current_period_end,
                    "trial_end": subscription.trial_end
                }
            }, status=200)
            
        except Subscription.DoesNotExist:
            return Response({"error": "Subscription not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CheckReferralStatusView(APIView):
    """Check current user's referral status and benefits"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current user's referral status"""
        user = request.user
        
        # Count referrals made by this user
        referral_count = User.objects.filter(referred_by=user.referral_code).count()
        
        # Get referrer info if user was referred
        referrer = None
        if user.referred_by:
            try:
                referrer = User.objects.get(referral_code=user.referred_by)
            except User.DoesNotExist:
                pass
        
        return Response({
            "user": {
                "id": user.id,
                "email": user.email,
                "referral_code": user.referral_code,
                "my_referral_link": user.my_referral_link,
                "referred_by": user.referred_by,
                "is_unlimited": user.is_unlimited,
                "package_expiry": user.package_expiry,
                "favorite_item": user.favorite_item,
                "referral_count": referral_count
            },
            "referrer": {
                "id": referrer.id if referrer else None,
                "email": referrer.email if referrer else None,
                "referral_code": referrer.referral_code if referrer else None
            } if referrer else None,
            "referred_users": [
                {
                    "id": ref_user.id,
                    "email": ref_user.email,
                    "is_active": ref_user.is_active
                }
                for ref_user in User.objects.filter(referred_by=user.referral_code)
            ]
        }, status=200)



@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    logger.info(f"Webhook received - Signature: {sig_header is not None}, Secret configured: {endpoint_secret is not None}")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"Webhook event constructed successfully: {event.get('type', 'unknown')}")
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Webhook construction error: {str(e)}")
        return HttpResponse(status=400)

    try:
        
        WebhookEvent.objects.create(
            event_id=event["id"],
            type=event["type"],
            data=event["data"]["object"],
        )
        
        logger.info(f"Webhook event saved to database: {event['id']}")
    except Exception as e:
        logger.error(f"Failed to save webhook event: {str(e)}")
        # Don't return error here, continue processing

    obj = event["data"]["object"]
    event_type = event["type"]
    
    logger.info(f"Processing webhook event: {event_type}")

    try:
        
        if event_type == "checkout.session.completed":
            logger.info("Processing checkout.session.completed")
            
            # Get user from metadata
            metadata = obj.get("metadata", {})
            user_id = metadata.get("user_id")
            plan_id = metadata.get("plan_id")
            
            logger.info(f"Checkout metadata - user_id: {user_id}, plan_id: {plan_id}")
            
            if user_id and obj.get("subscription"):
                try:
                    # Retrieve the subscription from Stripe
                    stripe_subscription = stripe.Subscription.retrieve(obj["subscription"])
                    logger.info(f"Retrieved Stripe subscription: {stripe_subscription.id}")
                    
                    # Find the pending subscription by user_id and customer_id instead of stripe_subscription_id
                    subscription = Subscription.objects.filter(
                        user_id=user_id,
                        stripe_customer_id=obj.get("customer"),
                        status="pending"
                    ).first()
                    
                    if subscription:
                        # Safely handle timestamps
                        trial_end = None
                        current_period_end = None
                        
                        if hasattr(stripe_subscription, 'trial_end') and stripe_subscription.trial_end:
                            trial_end = make_aware(
                                datetime.datetime.fromtimestamp(stripe_subscription.trial_end)
                            )
                        
                        if hasattr(stripe_subscription, 'current_period_end') and stripe_subscription.current_period_end:
                            current_period_end = make_aware(
                                datetime.datetime.fromtimestamp(stripe_subscription.current_period_end)
                            )
                        else:
                            # Fallback: calculate based on plan if Stripe doesn't provide it
                            if subscription.plan:
                                current_period_end = calculate_current_period_end(
                                    subscription.plan, 
                                    subscription.created_at
                                )
                        
                        subscription.stripe_subscription_id = stripe_subscription.id
                        subscription.status = stripe_subscription.status
                        subscription.trial_end = trial_end
                        subscription.current_period_end = current_period_end
                        subscription.save()
                        
                        logger.info(f"Updated subscription {subscription.id} with Stripe data")
                        
                        # Process referral benefits after successful subscription creation
                        try:
                            process_referral_benefits(subscription.user, subscription)
                        except Exception as e:
                            logger.error(f"Error processing referral benefits: {str(e)}")
                        
                    else:
                        logger.warning(f"No pending subscription found for user {user_id} and customer {obj.get('customer')}")
                        
                except Exception as e:
                    logger.error(f"Error processing checkout.session.completed: {str(e)}")

        elif event_type == "customer.subscription.created":
            logger.info("Processing customer.subscription.created")
            
            try:
                # First, try to find existing subscription by stripe_subscription_id
                subscription = Subscription.objects.filter(stripe_subscription_id=obj["id"]).first()
                
                if not subscription:
                    # If not found, try to find by customer_id and status
                    subscription = Subscription.objects.filter(
                        stripe_customer_id=obj.get("customer"),
                        status="pending"
                    ).first()
                
                if subscription:
                    # Update existing subscription
                    trial_end = None
                    current_period_end = None
                    
                    if obj.get("trial_end"):
                        trial_end = make_aware(
                            datetime.datetime.fromtimestamp(obj["trial_end"])
                        )
                    
                    if obj.get("current_period_end"):
                        current_period_end = make_aware(
                            datetime.datetime.fromtimestamp(obj["current_period_end"])
                        )
                    
                    subscription.stripe_subscription_id = obj["id"]
                    subscription.status = obj["status"]
                    subscription.trial_end = trial_end
                    subscription.current_period_end = current_period_end
                    subscription.save()
                    
                    logger.info(f"Updated existing subscription {subscription.id} with Stripe ID: {obj['id']}")
                else:
                    logger.warning(f"No matching subscription found for Stripe subscription {obj['id']}")
                
            except Exception as e:
                logger.error(f"Error processing customer.subscription.created: {str(e)}")

        # ✅ Handle subscription updated
        elif event_type == "customer.subscription.updated":
            logger.info("Processing customer.subscription.updated")
            
            try:
                # Safely handle timestamps
                trial_end = None
                current_period_end = None
                
                if obj.get("trial_end"):
                    trial_end = make_aware(
                        datetime.datetime.fromtimestamp(obj["trial_end"])
                    )
                
                if obj.get("current_period_end"):
                    current_period_end = make_aware(
                        datetime.datetime.fromtimestamp(obj["current_period_end"])
                    )
                
                updated_count = Subscription.objects.filter(
                    stripe_subscription_id=obj["id"]
                ).update(
                    status=obj["status"],
                    trial_end=trial_end,
                    current_period_end=current_period_end,
                )
                
                logger.info(f"Updated {updated_count} subscriptions for Stripe ID: {obj['id']}")
                
            except Exception as e:
                logger.error(f"Error processing customer.subscription.updated: {str(e)}")

        # ✅ Handle subscription deleted/cancelled
        elif event_type == "customer.subscription.deleted":
            logger.info("Processing customer.subscription.deleted")
            
            try:
                updated_count = Subscription.objects.filter(
                    stripe_subscription_id=obj["id"]
                ).update(status="canceled")
                
                logger.info(f"Canceled {updated_count} subscriptions for Stripe ID: {obj['id']}")
                
            except Exception as e:
                logger.error(f"Error processing customer.subscription.deleted: {str(e)}")
        
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing webhook event {event_type}: {str(e)}")
        return HttpResponse(status=500)

    logger.info(f"Webhook processing completed successfully for event: {event_type}")
    return HttpResponse(status=200)



class SubscriptionListView(generics.ListAPIView):
    """List all subscriptions (admin only)"""
    queryset = Subscription.objects.all().order_by('-created_at')
    serializer_class = SubscriptionSerializer
    # permission_classes = [permissions.IsAdminUser]
    # pagination_class = None  # Disable pagination for simplicity
    
    

class SubscriptionStopAutoRenewalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        
        try:
            active_subscription = Subscription.get_user_active_subscription(request.user)
            request_auto_renew = request.data.get("auto_renew", False)
            
            if not active_subscription or not active_subscription.stripe_subscription_id:
                return Response({"error": "No active subscription found"}, status=404)
            
            # The request parameter indicates what the user wants auto_renew to be set to
            if request_auto_renew == False:
                # User wants to stop auto-renewal
                stripe.Subscription.modify(
                    active_subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )

                active_subscription.auto_renew = False
                active_subscription.save()
                return Response({
                    "message": "Auto-renewal stopped. Subscription will cancel at the end of the current period",
                    "subscription": {
                        "id": active_subscription.id,
                        "auto_renew": active_subscription.auto_renew,
                        "current_period_end": active_subscription.current_period_end
                    }
                }, status=200)
            else:
                # User wants to enable auto-renewal
                stripe.Subscription.modify(
                    active_subscription.stripe_subscription_id,
                    cancel_at_period_end=False
                )

                active_subscription.auto_renew = True
                active_subscription.save()
            
                return Response({
                    "message": "Auto-renewal enabled. Subscription will continue at the end of the current period",
                    "subscription": {
                        "id": active_subscription.id,
                        "auto_renew": active_subscription.auto_renew,
                        "current_period_end": active_subscription.current_period_end
                    }
                }, status=200)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in stop auto-renewal: {str(e)}")
            return Response({"error": f"Stripe error: {str(e)}"}, status=400)
        except Exception as e:
            logger.error(f"Error in stop auto-renewal: {str(e)}")
            return Response({"error": str(e)}, status=500)