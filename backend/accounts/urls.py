from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView)

from .social_auth import *
from .views import *

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='registration'),
    path('auth/user/', UserDetailView.as_view(), name='user_detail'),
    path('auth/active/user/', UserRegistrationVerifyCodeView.as_view(), name='verify_code'),
    path('auth/resend/code/', ResendCodeView.as_view(), name='resend_code'),
    path('auth/login/', TokenObtainPairView.as_view(), name='access_token'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='refresh_token'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/verify_code/', VerifyCodeView.as_view(), name='verify_code'),
    path('auth/set_new_password/', SetNewPasswordView.as_view(), name='set_new_password'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path("auth/account-delete/", DeleteAccountView.as_view(), name="account-delete"),

    # for social login
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('auth/apple/', AppleLoginView.as_view(), name='apple_login'),

    # update profile
    path('auth/profile/update/', UpdateProfileView.as_view(), name='profile-update'),
    path('user/profile/<int:pk>/', UserUpdateView.as_view(), name='user-update'),
    path('auth/user/list/', UserListView.as_view(), name='user-list'),

    path('auth/user/question/', UserQuestionAnswerCreateListView.as_view(), name='user-question'),
    path('auth/user/question/<int:pk>/', UserQuestionAnswerRetrieveView.as_view(), name='user-question-detail'),

    # Dashboard
    path('auth/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('auth/cretiential/', ProjectCretientialsView.as_view(), name='project-cretiential'),
    path('auth/cretiential/<int:pk>/'), ProjectCretientialsDetailView.as_view(), name='project-cretiential-detail'),
]
