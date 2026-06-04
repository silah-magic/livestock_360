from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from datetime import date, timedelta


class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('PASTORALIST', 'Pastoralist'),
        ('VET',         'Veterinarian'),
        ('TRANSPORTER', 'Transporter'),
        ('BUYER',       'Buyer'),
        ('ADMIN',       'Administrator'),
    )
    user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number       = models.CharField(max_length=15,
        validators=[RegexValidator(r'^\+?254\d{9}$', message='Enter a valid Kenyan phone number')])
    user_type          = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='PASTORALIST')
    county             = models.CharField(max_length=100, default='Kajiado')
    sub_county         = models.CharField(max_length=100, blank=True)
    location           = models.PointField(srid=4326, blank=True, null=True)
    preferred_language = models.CharField(max_length=10, default='Maa')
    is_verified        = models.BooleanField(default=False)
    registered_at      = models.DateTimeField(auto_now_add=True)
    last_active        = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_user_type_display()})"


class Livestock(models.Model):
    SPECIES_CHOICES       = (('GOAT','Goat'),('SHEEP','Sheep'),('CATTLE','Cattle'))
    STATUS_CHOICES        = (('ACTIVE','Active'),('SOLD','Sold'),('DECEASED','Deceased'))
    HEALTH_STATUS_CHOICES = (('GREEN','Healthy'),('YELLOW','Due Soon'),('RED','Needs Care'))

    owner                = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livestock')
    tag_id               = models.CharField(max_length=50, unique=True)
    rfid_tag             = models.CharField(max_length=50, blank=True, unique=True, null=True)
    name                 = models.CharField(max_length=100, blank=True)
    species              = models.CharField(max_length=10, choices=SPECIES_CHOICES)
    breed                = models.CharField(max_length=50, blank=True)
    birth_date           = models.DateField(blank=True, null=True)
    birth_date_estimated = models.BooleanField(default=False)
    colour               = models.CharField(max_length=50, blank=True)
    distinctive_marks    = models.TextField(blank=True)
    current_location     = models.PointField(srid=4326, blank=True, null=True)
    status               = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    health_status_manual = models.CharField(max_length=10, choices=HEALTH_STATUS_CHOICES,
                             blank=True, default='GREEN')
    image                = models.ImageField(upload_to='livestock/images/', blank=True, null=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "livestock"
        indexes = [models.Index(fields=['owner','status']), models.Index(fields=['species'])]

    def __str__(self):
        return f"{self.tag_id} ({self.get_species_display()})"

    def get_health_status(self):
        if self.health_status_manual:
            return self.health_status_manual
        if self.certificates.filter(is_valid=True, valid_until__gte=date.today()).exists():
            return 'GREEN'
        if self.health_records.filter(
            next_due_date__lte=date.today() + timedelta(days=7),
            next_due_date__gte=date.today()
        ).exists():
            return 'YELLOW'
        return 'GREEN'


class HealthRecord(models.Model):
    RECORD_TYPE_CHOICES = (
        ('VACCINATION','Vaccination'),('TREATMENT','Treatment'),
        ('CHECKUP','Checkup'),('CERTIFICATION','Certification'),
    )
    animal          = models.ForeignKey(Livestock, on_delete=models.CASCADE, related_name='health_records')
    record_type     = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    veterinarian    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                        limit_choices_to={'profile__user_type':'VET'},
                        related_name='health_records_given')
    service_date    = models.DateField()
    next_due_date   = models.DateField(blank=True, null=True)
    diagnosis       = models.CharField(max_length=200, blank=True)
    treatment_given = models.TextField(blank=True)
    medication_used = models.CharField(max_length=200, blank=True)
    dosage          = models.CharField(max_length=50, blank=True)
    certificate_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['next_due_date'])]

    def __str__(self):
        return f"{self.animal} - {self.get_record_type_display()} on {self.service_date}"


class HealthCertificate(models.Model):
    animal             = models.ForeignKey(Livestock, on_delete=models.CASCADE, related_name='certificates')
    certificate_number = models.CharField(max_length=50, unique=True)
    issued_by          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                           limit_choices_to={'profile__user_type':'VET'},
                           related_name='certificates_issued')
    issued_date        = models.DateField(auto_now_add=True)
    valid_until        = models.DateField()
    is_valid           = models.BooleanField(default=True)
    qr_code            = models.ImageField(upload_to='certificates/qrcodes/', blank=True)
    pdf_file           = models.FileField(upload_to='certificates/pdfs/', blank=True)

    def __str__(self):
        return f"Certificate {self.certificate_number} for {self.animal}"


class VetRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING','Pending'),('ACCEPTED','Accepted'),
        ('IN_PROGRESS','In Progress'),('COMPLETED','Completed'),('CANCELLED','Cancelled'),
    )
    URGENCY_CHOICES = (
        ('LOW','Low — routine'),('MEDIUM','Medium — needs attention'),('HIGH','High — urgent'),
    )
    PAYMENT_STATUS_CHOICES = (('PENDING','Pending'),('PAID','Paid'),('FAILED','Failed'))

    pastoralist                = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='vet_requests_made')
    vet                        = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='vet_requests_accepted',
                                   limit_choices_to={'profile__user_type':'VET'})
    animal                     = models.ForeignKey(Livestock, on_delete=models.CASCADE,
                                   related_name='vet_requests')
    status                     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    urgency                    = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='MEDIUM')
    symptoms                   = models.TextField()
    additional_notes           = models.TextField(blank=True)
    pastoralist_location       = models.PointField(srid=4326, blank=True, null=True)
    pastoralist_location_name  = models.CharField(max_length=200, blank=True)
    vet_current_location       = models.PointField(srid=4326, blank=True, null=True)
    preferred_date             = models.DateField(blank=True, null=True)
    accepted_at                = models.DateTimeField(blank=True, null=True)
    completed_at               = models.DateTimeField(blank=True, null=True)
    consultation_fee           = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_status             = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    mpesa_receipt              = models.CharField(max_length=50, blank=True)
    mpesa_checkout_request_id  = models.CharField(max_length=100, blank=True)
    created_at                 = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes   = [models.Index(fields=['status','created_at'])]
        ordering  = ['-created_at']

    def __str__(self):
        return f"VetRequest #{self.id} — {self.animal.tag_id} ({self.status})"


class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = (
        ('PICKUP','Pickup (up to 10 animals)'),
        ('MEDIUM','Medium Truck (10–30 animals)'),
        ('LARGE', 'Large Carrier (30+ animals)'),
    )
    owner                  = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='vehicles',
                               limit_choices_to={'profile__user_type':'TRANSPORTER'})
    registration_number    = models.CharField(max_length=20, unique=True)
    vehicle_type           = models.CharField(max_length=30, choices=VEHICLE_TYPE_CHOICES)
    capacity               = models.IntegerField()
    has_ventilation        = models.BooleanField(default=True)
    has_partitions         = models.BooleanField(default=True)
    insurance_valid_until  = models.DateField()
    inspection_valid_until = models.DateField()
    current_location       = models.PointField(srid=4326, blank=True, null=True)
    is_available           = models.BooleanField(default=True)
    created_at             = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.registration_number} ({self.vehicle_type})"


class TransportRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING','Pending'),('POOLED','Pooled'),('ASSIGNED','Assigned'),
        ('IN_TRANSIT','In Transit'),('COMPLETED','Completed'),('CANCELLED','Cancelled'),
    )
    TIME_WINDOW_CHOICES  = (('MORNING','Morning'),('AFTERNOON','Afternoon'),('ANY','Any'))
    VEHICLE_SIZE_CHOICES = (
        ('PICKUP','Pickup (up to 10 animals)'),
        ('MEDIUM','Medium Truck (10–30 animals)'),
        ('LARGE', 'Large Carrier (30+ animals)'),
    )

    requester               = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='transport_requests')
    accepted_by             = models.ForeignKey(User, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='accepted_requests',
                                limit_choices_to={'profile__user_type':'TRANSPORTER'})
    animal_count            = models.IntegerField()
    origin                  = models.PointField(srid=4326)
    destination_name        = models.CharField(max_length=200, default='')
    preferred_date          = models.DateField()
    preferred_time_window   = models.CharField(max_length=20, choices=TIME_WINDOW_CHOICES, default='ANY')
    vehicle_size_preference = models.CharField(max_length=20, choices=VEHICLE_SIZE_CHOICES, default='PICKUP')
    status                  = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    pooling_group           = models.ForeignKey('PoolingGroup', on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='requests')
    trip_cost               = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mpesa_receipt           = models.CharField(max_length=50, blank=True)
    payment_status          = models.CharField(max_length=20,
                                choices=[('PENDING','Pending'),('PAID','Paid'),('FAILED','Failed')],
                                default='PENDING')

    # ✅ FIX: store driver GPS directly on the request — no Vehicle required
    driver_current_location = models.PointField(srid=4326, blank=True, null=True,
                                help_text="Driver live GPS — updated every 15 s after acceptance")

    created_at              = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['status','preferred_date'])]

    def __str__(self):
        return f"Request #{self.id} — {self.animal_count} animals to {self.destination_name}"

    def get_vehicle_size(self):
        if self.animal_count <= 10: return 'PICKUP'
        if self.animal_count <= 30: return 'MEDIUM'
        return 'LARGE'


class PoolingGroup(models.Model):
    created_at    = models.DateTimeField(auto_now_add=True)
    total_animals = models.IntegerField()
    vehicle       = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True,
                      related_name='pooling_groups')
    trip          = models.ForeignKey('Trip', on_delete=models.SET_NULL, null=True, blank=True,
                      related_name='pooling_groups')
    is_confirmed  = models.BooleanField(default=False)

    def __str__(self):
        return f"PoolingGroup #{self.id} ({self.total_animals} animals)"


class Trip(models.Model):
    STATUS_CHOICES = (
        ('PLANNED','Planned'),('IN_PROGRESS','In Progress'),
        ('COMPLETED','Completed'),('CANCELLED','Cancelled'),
    )
    vehicle           = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips')
    route             = models.LineStringField(srid=4326, blank=True, null=True)
    departure_time    = models.DateTimeField()
    estimated_arrival = models.DateTimeField()
    actual_arrival    = models.DateTimeField(blank=True, null=True)
    total_animals     = models.IntegerField()
    total_cost        = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_animal   = models.DecimalField(max_digits=8, decimal_places=2)
    distance_km       = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip #{self.id} — {self.vehicle.registration_number}"


class TripManifest(models.Model):
    trip             = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='manifests')
    request          = models.ForeignKey(TransportRequest, on_delete=models.CASCADE)
    animals          = models.ManyToManyField(Livestock, through='TripAnimal')
    collection_point = models.PointField(srid=4326)
    collection_time  = models.DateTimeField(blank=True, null=True)
    farmer_confirmed = models.BooleanField(default=False)


class TripAnimal(models.Model):
    trip_manifest  = models.ForeignKey(TripManifest, on_delete=models.CASCADE)
    animal         = models.ForeignKey(Livestock, on_delete=models.CASCADE)
    loaded_at      = models.DateTimeField(blank=True, null=True)
    unloaded_at    = models.DateTimeField(blank=True, null=True)
    health_checked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('trip_manifest', 'animal')


class MarketListing(models.Model):
    STATUS_CHOICES = (('ACTIVE','Active'),('SOLD','Sold'),('WITHDRAWN','Withdrawn'))
    animal       = models.ForeignKey(Livestock, on_delete=models.CASCADE, related_name='listings')
    seller       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    asking_price = models.DecimalField(max_digits=10, decimal_places=2)
    listed_date  = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    views        = models.IntegerField(default=0)

    def __str__(self):
        return f"Listing #{self.id}: {self.animal.tag_id} @ KES {self.asking_price}"


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('MARKETPLACE','Animal Purchase'),
        ('TRANSPORT',  'Transport Payment'),
        ('VET',        'Veterinary Payment'),
    )
    listing                   = models.ForeignKey(MarketListing, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='transactions')
    transport_request         = models.ForeignKey(TransportRequest, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='transactions')
    vet_request               = models.ForeignKey('VetRequest', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='transactions')
    buyer                     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    seller                    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales')
    amount                    = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type          = models.CharField(max_length=20,
                                  choices=TRANSACTION_TYPE_CHOICES, default='MARKETPLACE')
    transaction_date          = models.DateTimeField(auto_now_add=True)
    mpesa_receipt             = models.CharField(max_length=50, blank=True)
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True)
    is_completed              = models.BooleanField(default=False)
    origin_name               = models.CharField(max_length=200, blank=True)
    destination_name          = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Transaction #{self.id}: KES {self.amount} ({self.transaction_type})"


class PriceData(models.Model):
    market        = models.CharField(max_length=100)
    species       = models.CharField(max_length=10, choices=Livestock.SPECIES_CHOICES)
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_price     = models.DecimalField(max_digits=10, decimal_places=2)
    max_price     = models.DecimalField(max_digits=10, decimal_places=2)
    date          = models.DateField(auto_now_add=True)
    source        = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [models.Index(fields=['market','species','date'])]

    def __str__(self):
        return f"{self.market} {self.species} — {self.date}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('REMINDER','Reminder'),('ALERT','Alert'),('CONFIRMATION','Confirmation'),
        ('INFO','Information'),('PAYMENT','Payment'),
        ('VET_REQUEST','Vet Request'),('VET_ACCEPTED','Vet Accepted'),
    )
    recipient            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type    = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title                = models.CharField(max_length=200)
    message              = models.TextField()
    is_read              = models.BooleanField(default=False)
    created_at           = models.DateTimeField(auto_now_add=True)
    sent_via_sms         = models.BooleanField(default=False)
    sms_delivery_status  = models.CharField(max_length=20, blank=True)
    related_transport_id = models.IntegerField(null=True, blank=True)
    related_listing_id   = models.IntegerField(null=True, blank=True)
    related_vet_id       = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_notification_type_display()} → {self.recipient.username}"


class OfflineAction(models.Model):
    ACTION_TYPES = (('CREATE','Create'),('UPDATE','Update'),('DELETE','Delete'))
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    model_name  = models.CharField(max_length=50)
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    data        = models.JSONField()
    created_at  = models.DateTimeField(auto_now_add=True)
    synced_at   = models.DateTimeField(blank=True, null=True)

    
class ActivityLog(models.Model):
    """
    Automatic audit trail — one row per authenticated API request.
    Written by ActivityLogMiddleware in livestock/middleware.py.
    Never written to directly from views.
    """
 
    ROLE_CHOICES = (
        ('PASTORALIST', 'Pastoralist'),
        ('VET',         'Veterinarian'),
        ('TRANSPORTER', 'Transporter'),
        ('BUYER',       'Buyer'),
        ('ADMIN',       'Administrator'),
        ('UNKNOWN',     'Unknown'),
    )
    METHOD_CHOICES = (
        ('GET',    'GET'),
        ('POST',   'POST'),
        ('PATCH',  'PATCH'),
        ('PUT',    'PUT'),
        ('DELETE', 'DELETE'),
    )
 
    user        = models.ForeignKey(
                    'auth.User', on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='activity_logs'
                  )
    role        = models.CharField(max_length=20, choices=ROLE_CHOICES, default='UNKNOWN')
    action      = models.CharField(max_length=300, help_text='Human-readable description')
    method      = models.CharField(max_length=10, choices=METHOD_CHOICES, default='GET')
    endpoint    = models.CharField(max_length=200)
    status_code = models.IntegerField(default=200)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.CharField(max_length=200, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-timestamp']
        indexes  = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['role', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
 
    def __str__(self):
        username = self.user.username if self.user else 'deleted-user'
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {username} — {self.action}'