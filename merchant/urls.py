from django.urls import path, include
from rest_framework.routers import DefaultRouter
from merchant.views import (
    ProductViewSet,
    ProductVariantViewSet,
    OrderViewSet,
    MerchantRegistrationView,
    MerchantLoginView
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'variants', ProductVariantViewSet, basename='variant')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('auth/register/', MerchantRegistrationView.as_view(), name='merchant-register'),
    path('auth/login/', MerchantLoginView.as_view(), name='merchant-login'),
    path('', include(router.urls)),
]
