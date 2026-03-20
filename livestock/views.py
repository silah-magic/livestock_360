from rest_framework import viewsets, permissions
from django.contrib.auth.models import User
from .models import Livestock, HealthRecord, UserProfile,HealthCertificate, Vehicle, TransportRequest, PoolingGroup,Trip,TripManifest,TripAnimal,MarketListing,Transaction,PriceData, Notification,OfflineAction
from .serializers import (
    UserSerializer, UserProfileSerializer,
    LivestockSerializer, HealthRecordSerializer,HealthCertificateSerializer, VehicleSerializer, TransportRequestSerializer, PoolingGroupSerializer,TripSerializer, TripManifestSerializer, TripAnimalSerializer,MarketListingSerializer, TransactionSerializer, PriceDataSerializer, NotificationSerializer,OfflineActionSerializer
)
from .utils.sms import send_sms
from rest_framework.decorators import action
from rest_framework.response import Response

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing users (read-only)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        profile = self.get_queryset().first()
        if not profile:
            return Response({'detail': 'Profile not found'}, status=404)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

class LivestockViewSet(viewsets.ModelViewSet):
    queryset = Livestock.objects.all()
    serializer_class = LivestockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return only livestock belonging to the logged-in user
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the owner to the current user
        serializer.save(owner=self.request.user)

class HealthRecordViewSet(viewsets.ModelViewSet):
    queryset = HealthRecord.objects.all()
    serializer_class = HealthRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Optionally filter by animal (if query param provided)
        queryset = self.queryset
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            queryset = queryset.filter(animal_id=animal_id)
        return queryset
class HealthCertificateViewSet(viewsets.ModelViewSet):
    queryset = HealthCertificate.objects.all()
    serializer_class = HealthCertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Transporters see their own vehicles; others might see all? Adjust as needed.
        return self.queryset.filter(owner=self.request.user)

class TransportRequestViewSet(viewsets.ModelViewSet):
    queryset = TransportRequest.objects.all()
    serializer_class = TransportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(requester=self.request.user)

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)

    def perform_update(self, serializer):
     old_instance = self.get_object()
     print(f"Old status: {old_instance.status}")
     instance = serializer.save()
     print(f"New status: {instance.status}")
     if instance.status == 'POOLED' and old_instance.status != 'POOLED':
        phone = instance.requester.profile.phone_number
        print(f"Sending SMS to {phone}")
        msg = f"Your transport request for {instance.animal_count} animals has been pooled! Check the app for details."
        from .utils.sms import send_sms   
        send_sms([phone], msg)
     return instance

class PoolingGroupViewSet(viewsets.ModelViewSet):
    queryset = PoolingGroup.objects.all()
    serializer_class = PoolingGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

class TripManifestViewSet(viewsets.ModelViewSet):
    queryset = TripManifest.objects.all()
    serializer_class = TripManifestSerializer
    permission_classes = [permissions.IsAuthenticated]

class TripAnimalViewSet(viewsets.ModelViewSet):
    queryset = TripAnimal.objects.all()
    serializer_class = TripAnimalSerializer
    permission_classes = [permissions.IsAuthenticated]

class MarketListingViewSet(viewsets.ModelViewSet):
    queryset = MarketListing.objects.all()
    serializer_class = MarketListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # For standard list, return user's own listings
        return self.queryset.filter(seller=self.request.user)

    @action(detail=False, methods=['get'])
    def public(self, request):
        # Return all active listings (not sold)
        public_listings = MarketListing.objects.filter(status='ACTIVE')
        serializer = self.get_serializer(public_listings, many=True)
        return Response(serializer.data)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

class PriceDataViewSet(viewsets.ReadOnlyModelViewSet):  # Read-only for most users
    queryset = PriceData.objects.all()
    serializer_class = PriceDataSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(recipient=self.request.user)

class OfflineActionViewSet(viewsets.ModelViewSet):
    queryset = OfflineAction.objects.all()
    serializer_class = OfflineActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
