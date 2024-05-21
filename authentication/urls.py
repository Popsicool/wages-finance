from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)


from .views import (
    SignupView, 
    LoginView, 
    VerifyPhone, 
    RequestPasswordResetEmail, 
#     PasswordTokenCheckAPI,
    SetNewPasswordAPIView,
    ResendVerificationMail,
    ChangePasswordAPIView,
    )

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('resend-verification-mail/', ResendVerificationMail.as_view(), name='resend-verification-mail'),
    path('verify-phone/', VerifyPhone.as_view(), name='verify-phone'),
    path('refresh-token/', TokenRefreshView.as_view(), name='token-refresh'),
    path('request-reset-password-email/', RequestPasswordResetEmail.as_view(),
         name='request-reset-password-email'),
#     path('password-reset/<uid64>/<token>/',
#          PasswordTokenCheckAPI.as_view(), name='password-reset-confirm'),
    path('set-new-password/', SetNewPasswordAPIView.as_view(),
         name='set-new-password'),
    path('change-password/', ChangePasswordAPIView.as_view(),
         name='change-password')
]
