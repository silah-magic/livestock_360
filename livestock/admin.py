from django.contrib import admin
from .models import (
    UserProfile, Livestock, HealthRecord, HealthCertificate,
    Vehicle, TransportRequest, PoolingGroup, Trip, TripManifest,
    TripAnimal, MarketListing, Transaction, PriceData,
    Notification, OfflineAction
)

# Register each model
admin.site.register(UserProfile)
admin.site.register(Livestock)
admin.site.register(HealthRecord)
admin.site.register(HealthCertificate)
admin.site.register(Vehicle)
admin.site.register(TransportRequest)
admin.site.register(PoolingGroup)
admin.site.register(Trip)
admin.site.register(TripManifest)
admin.site.register(TripAnimal)
admin.site.register(MarketListing)
admin.site.register(Transaction)
admin.site.register(PriceData)
admin.site.register(Notification)
admin.site.register(OfflineAction)