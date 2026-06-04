from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import (
    UserProfile, Livestock, HealthRecord, HealthCertificate,
    VetRequest, Vehicle, TransportRequest, PoolingGroup,
    Trip, TripManifest, TripAnimal, MarketListing,
    Transaction, PriceData, Notification, OfflineAction,
    ActivityLog,
)


# ─── UserProfile ──────────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'user_type', 'phone_number', 'county', 'sub_county', 'is_verified', 'registered_at')
    list_filter   = ('user_type', 'county', 'is_verified')
    search_fields = ('user__username', 'user__email', 'phone_number')
    ordering      = ('-registered_at',)


# ─── Livestock ────────────────────────────────────────────────────────────────
@admin.register(Livestock)
class LivestockAdmin(GISModelAdmin):
    list_display  = ('tag_id', 'species', 'breed', 'owner', 'health_status_manual', 'status', 'created_at')
    list_filter   = ('species', 'status', 'health_status_manual')
    search_fields = ('tag_id', 'owner__username', 'rfid_tag')
    ordering      = ('-created_at',)


# ─── Health Records ───────────────────────────────────────────────────────────
@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display  = ('animal', 'record_type', 'veterinarian', 'service_date', 'next_due_date')
    list_filter   = ('record_type',)
    search_fields = ('animal__tag_id', 'veterinarian__username', 'diagnosis')
    ordering      = ('-service_date',)


@admin.register(HealthCertificate)
class HealthCertificateAdmin(admin.ModelAdmin):
    list_display  = ('certificate_number', 'animal', 'issued_by', 'issued_date', 'valid_until', 'is_valid')
    list_filter   = ('is_valid',)
    search_fields = ('certificate_number', 'animal__tag_id')
    ordering      = ('-issued_date',)


# ─── VetRequest ───────────────────────────────────────────────────────────────
@admin.register(VetRequest)
class VetRequestAdmin(GISModelAdmin):
    list_display  = ('id', 'animal', 'pastoralist', 'vet', 'status', 'urgency',
                     'consultation_fee', 'payment_status', 'created_at')
    list_filter   = ('status', 'urgency', 'payment_status')
    search_fields = ('animal__tag_id', 'pastoralist__username', 'vet__username', 'symptoms')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'accepted_at', 'completed_at',
                       'mpesa_receipt', 'mpesa_checkout_request_id')


# ─── Vehicle ──────────────────────────────────────────────────────────────────
@admin.register(Vehicle)
class VehicleAdmin(GISModelAdmin):
    list_display  = ('registration_number', 'owner', 'vehicle_type', 'capacity', 'is_available')
    list_filter   = ('vehicle_type', 'is_available')
    search_fields = ('registration_number', 'owner__username')


# ─── TransportRequest ─────────────────────────────────────────────────────────
@admin.register(TransportRequest)
class TransportRequestAdmin(GISModelAdmin):
    list_display  = ('id', 'requester', 'accepted_by', 'animal_count',
                     'destination_name', 'status', 'trip_cost', 'payment_status', 'created_at')
    list_filter   = ('status', 'payment_status', 'vehicle_size_preference')
    search_fields = ('requester__username', 'accepted_by__username', 'destination_name')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'trip_cost', 'mpesa_receipt')


# ─── Pooling & Trip ───────────────────────────────────────────────────────────
@admin.register(PoolingGroup)
class PoolingGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'total_animals', 'is_confirmed', 'created_at')
    list_filter  = ('is_confirmed',)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display  = ('id', 'vehicle', 'status', 'total_animals', 'total_cost', 'distance_km', 'departure_time')
    list_filter   = ('status',)
    ordering      = ('-departure_time',)

admin.site.register(TripManifest)
admin.site.register(TripAnimal)


# ─── Marketplace ──────────────────────────────────────────────────────────────
@admin.register(MarketListing)
class MarketListingAdmin(admin.ModelAdmin):
    list_display  = ('id', 'animal', 'seller', 'asking_price', 'status', 'listed_date', 'views')
    list_filter   = ('status',)
    search_fields = ('animal__tag_id', 'seller__username')
    ordering      = ('-listed_date',)


# ─── Transactions ─────────────────────────────────────────────────────────────
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ('id', 'transaction_type', 'buyer', 'seller',
                     'amount', 'is_completed', 'mpesa_receipt', 'transaction_date')
    list_filter   = ('transaction_type', 'is_completed')
    search_fields = ('buyer__username', 'seller__username', 'mpesa_receipt')
    ordering      = ('-transaction_date',)
    readonly_fields = ('transaction_date', 'mpesa_receipt', 'mpesa_checkout_request_id')


# ─── Price Data ───────────────────────────────────────────────────────────────
@admin.register(PriceData)
class PriceDataAdmin(admin.ModelAdmin):
    list_display  = ('market', 'species', 'average_price', 'min_price', 'max_price', 'date', 'source')
    list_filter   = ('market', 'species')
    ordering      = ('-date',)


# ─── Notifications ────────────────────────────────────────────────────────────
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('recipient', 'notification_type', 'title', 'is_read', 'sent_via_sms', 'created_at')
    list_filter   = ('notification_type', 'is_read', 'sent_via_sms')
    search_fields = ('recipient__username', 'title', 'message')
    ordering      = ('-created_at',)


# ─── Offline Actions ──────────────────────────────────────────────────────────
@admin.register(OfflineAction)
class OfflineActionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'model_name', 'action_type', 'created_at', 'synced_at')
    list_filter   = ('action_type', 'model_name')
    search_fields = ('user__username',)
    ordering      = ('-created_at',)


# ─── ActivityLog ─────────────────────────────────────────────────────────────
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display  = ('timestamp', 'user', 'role', 'action', 'method',
                     'status_code', 'ip_address')
    list_filter   = ('role', 'method', 'status_code')
    search_fields = ('user__username', 'action', 'endpoint', 'ip_address')
    ordering      = ('-timestamp',)
    # Make all fields read-only — logs must never be edited
    readonly_fields = (
        'user', 'role', 'action', 'method', 'endpoint',
        'status_code', 'ip_address', 'user_agent', 'timestamp',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False   # logs are auto-generated only

    def has_change_permission(self, request, obj=None):
        return False   # read-only in admin

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete log entries
        return request.user.is_superuser