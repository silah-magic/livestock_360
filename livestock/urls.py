# livestock/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'profiles', views.UserProfileViewSet)
router.register(r'livestock', views.LivestockViewSet)
router.register(r'health-records', views.HealthRecordViewSet)
router.register(r'health-certificates', views.HealthCertificateViewSet)
router.register(r'vehicles', views.VehicleViewSet)
router.register(r'transport-requests', views.TransportRequestViewSet)
router.register(r'pooling-groups', views.PoolingGroupViewSet)
router.register(r'trips', views.TripViewSet)
router.register(r'trip-manifests', views.TripManifestViewSet)
router.register(r'trip-animals', views.TripAnimalViewSet)
router.register(r'market-listings', views.MarketListingViewSet)
router.register(r'transactions', views.TransactionViewSet)
router.register(r'price-data', views.PriceDataViewSet)
router.register(r'notifications', views.NotificationViewSet)
router.register(r'offline-actions', views.OfflineActionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]