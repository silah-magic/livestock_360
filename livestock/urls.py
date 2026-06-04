# livestock/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    RegisterView, CustomTokenObtainPairView,
    MpesaMarketplaceSTKView, MpesaCallbackView,
)

router = DefaultRouter()
router.register(r'users',              views.UserViewSet)
router.register(r'profiles',           views.UserProfileViewSet)
router.register(r'livestock',          views.LivestockViewSet)
router.register(r'health-records',     views.HealthRecordViewSet)
router.register(r'health-certificates',views.HealthCertificateViewSet)
router.register(r'vet-requests',       views.VetRequestViewSet)     
router.register(r'vehicles',           views.VehicleViewSet)
router.register(r'transport-requests', views.TransportRequestViewSet)
router.register(r'pooling-groups',     views.PoolingGroupViewSet)
router.register(r'trips',              views.TripViewSet)
router.register(r'trip-manifests',     views.TripManifestViewSet)
router.register(r'trip-animals',       views.TripAnimalViewSet)
router.register(r'market-listings',    views.MarketListingViewSet)
router.register(r'transactions',       views.TransactionViewSet)
router.register(r'price-data',         views.PriceDataViewSet)
router.register(r'notifications',      views.NotificationViewSet)
router.register(r'offline-actions',    views.OfflineActionViewSet)
router.register(r'activity-logs', views.ActivityLogViewSet, basename='activity-logs')

urlpatterns = [
    path('', include(router.urls)),
    path('register/',       RegisterView.as_view(),              name='register'),
    path('token/',          CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('mpesa/stk/',      MpesaMarketplaceSTKView.as_view(),   name='mpesa_stk'),
    path('mpesa/callback/', MpesaCallbackView.as_view(),         name='mpesa_callback'),
]