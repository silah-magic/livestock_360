
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from livestock import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'profiles', views.UserProfileViewSet)
router.register(r'livestock', views.LivestockViewSet)
router.register(r'health-records', views.HealthRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]



from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('livestock.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]