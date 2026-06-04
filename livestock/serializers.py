from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from .models import ActivityLog
from .models import (
    UserProfile, Livestock, HealthRecord, HealthCertificate,
    Vehicle, TransportRequest, PoolingGroup, Trip, TripManifest,
    TripAnimal, MarketListing, Transaction, PriceData,
    Notification, OfflineAction, VetRequest
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model  = UserProfile
        fields = '__all__'


class LivestockSerializer(serializers.ModelSerializer):
    owner_name    = serializers.CharField(source='owner.username', read_only=True)
    health_status = serializers.SerializerMethodField()

    class Meta:
        model  = Livestock
        fields = '__all__'
        read_only_fields = ['owner', 'owner_name', 'created_at', 'updated_at']

    def get_health_status(self, obj):
        return obj.get_health_status()

    def validate_species(self, value):
        return value.upper()


class HealthRecordSerializer(serializers.ModelSerializer):
    veterinarian_name = serializers.CharField(
        source='veterinarian.username', read_only=True, default=''
    )
    class Meta:
        model  = HealthRecord
        fields = '__all__'
        read_only_fields = ['veterinarian', 'created_at']


class HealthCertificateSerializer(serializers.ModelSerializer):
    animal_tag     = serializers.CharField(source='animal.tag_id',      read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.username',  read_only=True)

    class Meta:
        model  = HealthCertificate
        fields = '__all__'
        read_only_fields = ['issued_by', 'issued_date']


class VetRequestSerializer(serializers.ModelSerializer):
    pastoralist_name  = serializers.CharField(source='pastoralist.username',         read_only=True)
    pastoralist_phone = serializers.CharField(source='pastoralist.profile.phone_number',
                          read_only=True, default='')
    vet_name          = serializers.CharField(source='vet.username',
                          read_only=True, default='')
    vet_phone         = serializers.CharField(source='vet.profile.phone_number',
                          read_only=True, default='')
    animal_details    = serializers.SerializerMethodField()
    pastoralist_location = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model  = VetRequest
        fields = '__all__'
        read_only_fields = [
            'pastoralist', 'vet', 'status', 'accepted_at', 'completed_at',
            'mpesa_receipt', 'mpesa_checkout_request_id',
            'payment_status', 'vet_current_location', 'created_at',
        ]

    def get_animal_details(self, obj):
        a = obj.animal
        return {
            'id':            a.id,
            'tag_id':        a.tag_id,
            'species':       a.species,
            'breed':         a.breed,
            'colour':        a.colour,
            'health_status': a.get_health_status(),
            'image':         a.image.url if a.image else None,
        }

    def validate_pastoralist_location(self, value):
        if value and value.startswith('POINT'):
            try:
                coords = value.replace('POINT(', '').replace(')', '').split()
                return Point(float(coords[0]), float(coords[1]), srid=4326)
            except Exception:
                raise serializers.ValidationError('Invalid GPS format. Expected POINT(lng lat)')
        return None


class VehicleSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    class Meta:
        model  = Vehicle
        fields = '__all__'
        read_only_fields = ['owner']


class TransportRequestSerializer(serializers.ModelSerializer):
    requester_name    = serializers.CharField(source='requester.username',             read_only=True)
    requester_phone   = serializers.CharField(source='requester.profile.phone_number', read_only=True, default='')
    accepted_by_name  = serializers.CharField(source='accepted_by.username',           read_only=True, default='')
    accepted_by_phone = serializers.CharField(source='accepted_by.profile.phone_number', read_only=True, default='')
    suggested_vehicle_size = serializers.SerializerMethodField()

    # ✅ FIX: expose pastoralist pickup GPS as plain lat/lng numbers for the driver
    origin_lat = serializers.SerializerMethodField()
    origin_lng = serializers.SerializerMethodField()

    # Accept WKT string from frontend
    origin          = serializers.CharField(required=True)
    destination_name = serializers.CharField(required=True)

    class Meta:
        model  = TransportRequest
        fields = '__all__'
        read_only_fields = [
            'requester', 'status', 'pooling_group', 'created_at',
            'accepted_by', 'trip_cost', 'payment_status',
            'mpesa_receipt', 'suggested_vehicle_size',
            'origin_lat', 'origin_lng',
            'driver_current_location',
        ]

    def get_suggested_vehicle_size(self, obj):
        return obj.get_vehicle_size()

    def get_origin_lat(self, obj):
        """Pastoralist's pickup latitude — visible to driver after acceptance."""
        try:
            if obj.origin:
                return round(obj.origin.y, 6)
        except Exception:
            pass
        return None

    def get_origin_lng(self, obj):
        """Pastoralist's pickup longitude — visible to driver after acceptance."""
        try:
            if obj.origin:
                return round(obj.origin.x, 6)
        except Exception:
            pass
        return None

    def validate(self, data):
        origin_str = data.get('origin', '')
        if isinstance(origin_str, str) and origin_str.startswith('POINT'):
            try:
                coords = origin_str.replace('POINT(', '').replace(')', '').split()
                data['origin'] = Point(float(coords[0]), float(coords[1]), srid=4326)
            except Exception:
                raise serializers.ValidationError({'origin': 'Invalid GPS format.'})
        count = data.get('animal_count', 0)
        data['vehicle_size_preference'] = (
            'PICKUP' if count <= 10 else 'MEDIUM' if count <= 30 else 'LARGE'
        )
        return data


class PoolingGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PoolingGroup
        fields = '__all__'


class TripSerializer(serializers.ModelSerializer):
    vehicle_registration = serializers.CharField(source='vehicle.registration_number', read_only=True)
    vehicle_type         = serializers.CharField(source='vehicle.vehicle_type',        read_only=True)
    transporter_name     = serializers.CharField(source='vehicle.owner.username',      read_only=True)
    transporter_phone    = serializers.CharField(source='vehicle.owner.profile.phone_number',
                             read_only=True, default='')
    class Meta:
        model  = Trip
        fields = '__all__'


class TripManifestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TripManifest
        fields = '__all__'


class TripAnimalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TripAnimal
        fields = '__all__'


class MarketListingSerializer(serializers.ModelSerializer):
    seller_name    = serializers.CharField(source='seller.username', read_only=True)
    seller_phone   = serializers.SerializerMethodField()
    animal_details = serializers.SerializerMethodField()
    health_status  = serializers.SerializerMethodField()

    class Meta:
        model  = MarketListing
        fields = '__all__'
        read_only_fields = ['seller', 'listed_date', 'views']

    def get_seller_phone(self, obj):
        try:    return obj.seller.profile.phone_number
        except: return None

    def get_animal_details(self, obj):
        return {
            'id':            obj.animal.id,
            'tag_id':        obj.animal.tag_id,
            'species':       obj.animal.species,
            'breed':         obj.animal.breed,
            'colour':        obj.animal.colour,
            'health_status': obj.animal.get_health_status(),
            'image':         obj.animal.image.url if obj.animal.image else None,
        }

    def get_health_status(self, obj):
        return obj.animal.get_health_status()


class TransactionSerializer(serializers.ModelSerializer):
    buyer_name      = serializers.CharField(source='buyer.username',  read_only=True)
    seller_name     = serializers.CharField(source='seller.username', read_only=True)
    listing_details = MarketListingSerializer(source='listing', read_only=True)

    class Meta:
        model  = Transaction
        fields = '__all__'
        read_only_fields = [
            'buyer', 'seller', 'transaction_date', 'is_completed',
            'mpesa_receipt', 'mpesa_checkout_request_id',
        ]


class PriceDataSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PriceData
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = '__all__'
        read_only_fields = ['recipient', 'created_at']


class OfflineActionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OfflineAction
        fields = '__all__'
        read_only_fields = ['user', 'created_at']

class ActivityLogSerializer(serializers.ModelSerializer):
    username   = serializers.CharField(source='user.username',         read_only=True, default='—')
    user_email = serializers.CharField(source='user.email',            read_only=True, default='')
    role_label = serializers.CharField(source='get_role_display',      read_only=True)
    timestamp_local = serializers.SerializerMethodField()
 
    class Meta:
        model  = ActivityLog
        fields = [
            'id', 'username', 'user_email', 'role', 'role_label',
            'action', 'method', 'endpoint', 'status_code',
            'ip_address', 'timestamp', 'timestamp_local',
        ]
        read_only_fields = fields
 
    def get_timestamp_local(self, obj):
        # Return ISO string; frontend formats it
        return obj.timestamp.isoformat()
