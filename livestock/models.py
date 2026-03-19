from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

# ------------------------------------------------------------------
# User Profile Model – extends the built-in User
# ------------------------------------------------------------------
class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('PASTORALIST', 'Pastoralist'),
        ('VET', 'Veterinarian'),
        ('TRANSPORTER', 'Transporter'),
        ('BUYER', 'Buyer'),
        ('ADMIN', 'Administrator'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?254\d{9}$', message='Enter a valid Kenyan phone number')]
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='PASTORALIST')
    county = models.CharField(max_length=100, default='Kajiado')
    sub_county = models.CharField(max_length=100, blank=True)
    # GPS location of the homestead / base
    location = models.PointField(srid=4326, blank=True, null=True)
    preferred_language = models.CharField(max_length=10, default='Maa')
    is_verified = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_user_type_display()})"


# ------------------------------------------------------------------
# Livestock (Animal) Model
# ------------------------------------------------------------------
class Livestock(models.Model):
    SPECIES_CHOICES = (
        ('GOAT', 'Goat'),
        ('SHEEP', 'Sheep'),
        ('CATTLE', 'Cattle'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('SOLD', 'Sold'),
        ('DECEASED', 'Deceased'),
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livestock')
    tag_id = models.CharField(max_length=50, unique=True, help_text="Visual ear tag or unique identifier")
    rfid_tag = models.CharField(max_length=50, blank=True, unique=True, null=True, help_text="Optional electronic RFID")
    name = models.CharField(max_length=100, blank=True, help_text="Optional name given by farmer")
    species = models.CharField(max_length=10, choices=SPECIES_CHOICES)
    breed = models.CharField(max_length=50, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    birth_date_estimated = models.BooleanField(default=False)
    colour = models.CharField(max_length=50, blank=True)
    distinctive_marks = models.TextField(blank=True)
    current_location = models.PointField(srid=4326, blank=True, null=True, help_text="Last known GPS location")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "livestock"
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['species']),
        ]

    def __str__(self):
        return f"{self.tag_id} ({self.get_species_display()})"


# ------------------------------------------------------------------
# Health Record (vaccinations, treatments, checkups)
# ------------------------------------------------------------------
class HealthRecord(models.Model):
    RECORD_TYPE_CHOICES = (
        ('VACCINATION', 'Vaccination'),
        ('TREATMENT', 'Treatment'),
        ('CHECKUP', 'Checkup'),
        ('CERTIFICATION', 'Certification'),
    )
    animal = models.ForeignKey(Livestock, on_delete=models.CASCADE, related_name='health_records')
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    veterinarian = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'profile__user_type': 'VET'},
        related_name='health_records_given'
    )
    service_date = models.DateField()
    next_due_date = models.DateField(blank=True, null=True, help_text="For vaccinations that require boosters")
    diagnosis = models.CharField(max_length=200, blank=True)
    treatment_given = models.TextField(blank=True)
    medication_used = models.CharField(max_length=200, blank=True)
    dosage = models.CharField(max_length=50, blank=True)
    certificate_number = models.CharField(max_length=50, blank=True, unique=True, null=True,
                                          help_text="Official certificate ID if any")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['next_due_date']),
        ]

    def __str__(self):
        return f"{self.animal} - {self.get_record_type_display()} on {self.service_date}"


# ------------------------------------------------------------------
# Health Certificate (digital passport)
# ------------------------------------------------------------------
class HealthCertificate(models.Model):
    animal = models.ForeignKey(Livestock, on_delete=models.CASCADE, related_name='certificates')
    certificate_number = models.CharField(max_length=50, unique=True)
    issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'profile__user_type': 'VET'},
        related_name='certificates_issued'
    )
    issued_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField()
    is_valid = models.BooleanField(default=True)
    qr_code = models.ImageField(upload_to='certificates/qrcodes/', blank=True)
    pdf_file = models.FileField(upload_to='certificates/pdfs/', blank=True)

    def __str__(self):
        return f"Certificate {self.certificate_number} for {self.animal}"


# ------------------------------------------------------------------
# Vehicle (for transporters)
# ------------------------------------------------------------------
class Vehicle(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vehicles',
        limit_choices_to={'profile__user_type': 'TRANSPORTER'}
    )
    registration_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=30, help_text="e.g., Livestock Carrier, Pickup")
    capacity = models.IntegerField(help_text="Number of animals (sheep/goat equivalent)")
    has_ventilation = models.BooleanField(default=True)
    has_partitions = models.BooleanField(default=True)
    insurance_valid_until = models.DateField()
    inspection_valid_until = models.DateField()
    current_location = models.PointField(srid=4326, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.registration_number} ({self.vehicle_type})"


# ------------------------------------------------------------------
# Transport Request (from farmer)
# ------------------------------------------------------------------
class TransportRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('POOLED', 'Pooled'),
        ('ASSIGNED', 'Assigned'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    TIME_WINDOW_CHOICES = (
        ('MORNING', 'Morning'),
        ('AFTERNOON', 'Afternoon'),
        ('ANY', 'Any'),
    )
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transport_requests')
    animal_count = models.IntegerField()
    origin = models.PointField(srid=4326, help_text="Pickup location (boma)")
    destination = models.PointField(srid=4326, help_text="Market or slaughterhouse")
    preferred_date = models.DateField()
    preferred_time_window = models.CharField(max_length=20, choices=TIME_WINDOW_CHOICES, default='ANY')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    pooling_group = models.ForeignKey('PoolingGroup', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='requests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'preferred_date']),
        ]

    def __str__(self):
        return f"Request #{self.id} by {self.requester.username} for {self.animal_count} animals"


# ------------------------------------------------------------------
# Pooling Group – groups several requests together
# ------------------------------------------------------------------
class PoolingGroup(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    total_animals = models.IntegerField()
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='pooling_groups')
    trip = models.ForeignKey('Trip', on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='pooling_groups')
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"PoolingGroup #{self.id} ({self.total_animals} animals)"


# ------------------------------------------------------------------
# Trip – actual journey of a vehicle
# ------------------------------------------------------------------
class Trip(models.Model):
    STATUS_CHOICES = (
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips')
    route = models.LineStringField(srid=4326, blank=True, null=True, help_text="Optimized route")
    departure_time = models.DateTimeField()
    estimated_arrival = models.DateTimeField()
    actual_arrival = models.DateTimeField(blank=True, null=True)
    total_animals = models.IntegerField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_animal = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip #{self.id} with {self.vehicle.registration_number}"


# ------------------------------------------------------------------
# Trip Manifest – links animals to a trip (through TripAnimal)
# ------------------------------------------------------------------
class TripManifest(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='manifests')
    request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE)
    # Many-to-many through TripAnimal to record when each animal was loaded/unloaded
    animals = models.ManyToManyField(Livestock, through='TripAnimal')
    collection_point = models.PointField(srid=4326)
    collection_time = models.DateTimeField(blank=True, null=True)
    farmer_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"Manifest for trip #{self.trip.id}"


# ------------------------------------------------------------------
# Through model for TripManifest -> Livestock
# ------------------------------------------------------------------
class TripAnimal(models.Model):
    trip_manifest = models.ForeignKey(TripManifest, on_delete=models.CASCADE)
    animal = models.ForeignKey(Livestock, on_delete=models.CASCADE)
    loaded_at = models.DateTimeField(blank=True, null=True)
    unloaded_at = models.DateTimeField(blank=True, null=True)
    health_checked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('trip_manifest', 'animal')

    def __str__(self):
        return f"{self.animal} on manifest #{self.trip_manifest.id}"


# ------------------------------------------------------------------
# Marketplace: Listing of an animal for sale
# ------------------------------------------------------------------
class MarketListing(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('SOLD', 'Sold'),
        ('WITHDRAWN', 'Withdrawn'),
    )
    animal = models.ForeignKey(Livestock, on_delete=models.CASCADE, related_name='listings')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    asking_price = models.DecimalField(max_digits=10, decimal_places=2)
    listed_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    views = models.IntegerField(default=0)

    def __str__(self):
        return f"Listing #{self.id}: {self.animal.tag_id} @ KES {self.asking_price}"


# ------------------------------------------------------------------
# Transaction – completed sale
# ------------------------------------------------------------------
class Transaction(models.Model):
    listing = models.ForeignKey(MarketListing, on_delete=models.SET_NULL, null=True, related_name='transactions')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    mpesa_receipt = models.CharField(max_length=50, blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Transaction #{self.id}: KES {self.amount}"


# ------------------------------------------------------------------
# Price Data – for market intelligence
# ------------------------------------------------------------------
class PriceData(models.Model):
    market = models.CharField(max_length=100, help_text="e.g., Kiserian, Ilbisil")
    species = models.CharField(max_length=10, choices=Livestock.SPECIES_CHOICES)
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    source = models.CharField(max_length=50, blank=True, help_text="e.g., Slaughterhouse, Trader reports")

    class Meta:
        indexes = [
            models.Index(fields=['market', 'species', 'date']),
        ]

    def __str__(self):
        return f"{self.market} {self.species} - {self.date}"


# ------------------------------------------------------------------
# Notifications (in-app and SMS)
# ------------------------------------------------------------------
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('REMINDER', 'Reminder'),
        ('ALERT', 'Alert'),
        ('CONFIRMATION', 'Confirmation'),
        ('INFO', 'Information'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_via_sms = models.BooleanField(default=False)
    sms_delivery_status = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient.username}"


# ------------------------------------------------------------------
# Offline Action Queue – for operations performed offline
# ------------------------------------------------------------------
class OfflineAction(models.Model):
    ACTION_TYPES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=50, help_text="e.g., 'Livestock'")
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    data = models.JSONField(help_text="Serialized data of the object")
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.action_type} {self.model_name} by {self.user.username} at {self.created_at}"