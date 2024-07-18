from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)


from .views import (
    SignupView, 
    LoginView, 
    VerifyPhone,
    SetBvnView,
#     PasswordTokenCheckAPI,
    SetNewPasswordAPIView,
    ResendVerificationMail,
    RequestPasswordResetPhoneView,
    ChangePasswordAPIView,
    VerifyBVNView,
    SetNinView,
    VerifyNINView,
    VerifyPasswordResetCode,

    )

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('request-reset-password-phone/', RequestPasswordResetPhoneView.as_view(),
         name='request-reset-password-phone'),
    path('verify_reset_code/', VerifyPasswordResetCode.as_view(), name='user_verify_reset__code'),
    path('resend-verification-code/', ResendVerificationMail.as_view(), name='resend-verification-mail'),
    path('verify-phone/', VerifyPhone.as_view(), name='verify-phone'),
    path('refresh-token/', TokenRefreshView.as_view(), name='token-refresh'),
    
    path('reset_password/', SetNewPasswordAPIView.as_view(),
         name='set-new-password'),
    path('change-password/', ChangePasswordAPIView.as_view(),
         name='change-password'),
    path('bvn/', SetBvnView.as_view(),
         name='set_bvn'),
    path('nin/', SetNinView.as_view(),
         name='set_bvn'),
    path('verify_bvn/', VerifyBVNView.as_view(),
         name='set_bvn'),
    path('verify_nin/', VerifyNINView.as_view(),
         name='verify_bvn'),
]
