from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
   UserProfile, Livestock, HealthRecord, HealthCertificate,
    Vehicle, TransportRequest, PoolingGroup, Trip, TripManifest,
    TripAnimal, MarketListing, Transaction, PriceData,
    Notification, OfflineAction
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # nested user info

    class Meta:
        model = UserProfile
        fields = '__all__'

class LivestockSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    health_status = serializers.SerializerMethodField()

    class Meta:
        model = Livestock
        fields = '__all__'

    def get_health_status(self, obj):
        return obj.get_health_status()

class HealthRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthRecord
        fields = '__all__'

class HealthCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCertificate
        fields = '__all__'


class HealthCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCertificate
        fields = '__all__'

class VehicleSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Vehicle
        fields = '__all__'

class TransportRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.username', read_only=True)

    class Meta:
        model = TransportRequest
        fields = '__all__'

class PoolingGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolingGroup
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'

class TripManifestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripManifest
        fields = '__all__'

class TripAnimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripAnimal
        fields = '__all__'

class MarketListingSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.username', read_only=True)

    class Meta:
        model = MarketListing
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

class PriceDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceData
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class OfflineActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineAction
        fields = '__all__'