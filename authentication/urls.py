from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)


from .views import (
    SignupView, 
    LoginView, 
    VerifyPhone,
    SetBvnView, 
    RequestPasswordResetEmail, 
#     PasswordTokenCheckAPI,
    SetNewPasswordAPIView,
    ResendVerificationMail,
    ChangePasswordAPIView,
    VerifyBVNView,
    SetNinView,
    VerifyNINView,
    )

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('resend-verification-code/', ResendVerificationMail.as_view(), name='resend-verification-mail'),
    path('verify-phone/', VerifyPhone.as_view(), name='verify-phone'),
    path('refresh-token/', TokenRefreshView.as_view(), name='token-refresh'),
    path('request-reset-password-email/', RequestPasswordResetEmail.as_view(),
         name='request-reset-password-email'),
    path('set-new-password/', SetNewPasswordAPIView.as_view(),
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
         name='set_bvn')
]
