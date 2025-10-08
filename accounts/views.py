from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework import generics, status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView

from payment.serializers import SubscriptionListSerializer, SubscriptionSerializer
from .serializers import *
from .models import *
from payment.models import *

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["referral_code_used"] = self.kwargs.get("referral_code_used")
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_data = self.get_serializer(user).data  
        return Response({"message": "Your account was created successfully. Please activate your account using the OTP sent to your email to log in."}, status=status.HTTP_201_CREATED)

class VerifyCodeView(generics.CreateAPIView):
    serializer_class = VerifyActiveCodeSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Email verified successfully. Account activated."},
            status=status.HTTP_200_OK
        )
        

class ResendCodeView(generics.CreateAPIView):
    serializer_class = ResendCodeSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "A new verification code has been sent to your email."}, status=status.HTTP_200_OK)


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Reset code sent to email."}, status=status.HTTP_200_OK)
    
    
class UserRegistrationVerifyCodeView(generics.GenericAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save activates the user and marks OTP as used
        serializer.save()

        return Response({"message": "Account activated successfully."}, status=status.HTTP_200_OK)

       
class VerifyCodeView(generics.GenericAPIView):
    serializer_class = VerfifyCodeSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # You can access validated user and code here if needed:
        user = serializer.user
        reset_code = serializer.reset_code

        # Optionally mark the code as not used
        reset_code.is_used = False
        reset_code.save()

        return Response({"message": "Code verified successfully."}, status=status.HTTP_200_OK)


class SetNewPasswordView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        user = serializer.user
        refresh = RefreshToken.for_user(user)
        
        return Response(
            {"message": "Your password has been changed successfully.",
                          "tokens": {
                              "access": str(refresh.access_token),
                              "refresh": str(refresh)
                          }
                         }, status=200)



class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    # permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
    
class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    # permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data['refresh']

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)


class UpdateProfileView(generics.UpdateAPIView):
    serializer_class = UpdateProfileSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_object(self):
        return self.request.user
    
class UserUpdateView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserUpdateSerializer
    
    
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    queryset = CustomUser.objects.all()


class UserDetailView(APIView):

    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
class DeleteAccountView(generics.DestroyAPIView):

    def get_object(self):
        # Get the user making the request
        user = self.request.user
        password = self.request.data.get("password")
        conform_password = self.request.data.get("conform_password")
        
        # Validate password and conform_password
        if not password or not conform_password:
            raise ValidationError({"detail": "Both password and conform_password are required."})
        if password != conform_password:
            raise ValidationError({"detail": "Passwords do not match."})
        if user.check_password(password) is False:
            raise ValidationError({"detail": "Incorrect password."})
        return user
    
    # account deletion
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response({"detail": "Account deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
    

class UserQuestionAnswerCreateListView(generics.ListCreateAPIView):
    queryset = UserQuestionAnswer.objects.all()
    serializer_class = UserQuestionAnswerSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserQuestionAnswerRetrieveView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserQuestionAnswer.objects.all()
    serializer_class = UserQuestionAnswerSerializer

    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            raise PermissionDenied("You do not have permission to access this object.")
        return obj
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"detail": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
    def patch(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"detail": "Update Successful", "data": serializer.data}, status=status.HTTP_200_OK)
    
    
class DashboardView(APIView):
    # return user dashboard data like total users, total active users, total inactive users, recent users and total subscriptions, total active subscriptions, total inactive subscriptions
    def get(self, request, *args, **kwargs):
        total_users = CustomUser.objects.count()
        total_active_users = CustomUser.objects.filter(is_active=True).count()
        recent_users = CustomUser.objects.order_by('-created_at')[:5]
        recent_users_data = UserSerializer(recent_users, many=True).data[-5:]
        
        # total subscriptions, total active subscriptions, total inactive subscriptions
        total_subscriptions = Subscription.objects.count()
        total_pending_subscriptions = Subscription.objects.filter(status='pending').count()
        total_trial_subscriptions = Subscription.objects.filter(status='trialing').count()
        total_active_subscriptions = Subscription.objects.filter(status='active').count()
        total_active_subscriptions_plan = Plan.objects.filter(active=True).count()
        recent_subscriptions = Subscription.objects.order_by('-created_at')[:5]
        recent_subscriptions_data = SubscriptionListSerializer(recent_subscriptions, many=True).data[-5:]

        data = {
            "total_users": total_users,
            "total_active_users": total_active_users,
            "recent_users": recent_users_data,
            "total_subscriptions": total_subscriptions,
            "total_pending_subscriptions": total_pending_subscriptions,
            "total_trial_subscriptions": total_trial_subscriptions,
            "total_active_subscriptions": total_active_subscriptions,
            "total_subscription_plans": total_active_subscriptions_plan,
            "recent_subscriptions_data": recent_subscriptions_data,
        }
        return Response(data, status=status.HTTP_200_OK)