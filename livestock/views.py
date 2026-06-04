import math
import base64
from datetime import datetime

import requests as http_req
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Livestock, HealthRecord, UserProfile, HealthCertificate,
    Vehicle, TransportRequest, PoolingGroup, Trip, TripManifest,
    TripAnimal, MarketListing, Transaction, PriceData,
    Notification, OfflineAction, VetRequest,ActivityLog
)
from .serializers import (
    UserSerializer, UserProfileSerializer,
    LivestockSerializer, HealthRecordSerializer, HealthCertificateSerializer,
    VehicleSerializer, TransportRequestSerializer, PoolingGroupSerializer,
    TripSerializer, TripManifestSerializer, TripAnimalSerializer,
    MarketListingSerializer, TransactionSerializer, PriceDataSerializer,
    NotificationSerializer, OfflineActionSerializer, VetRequestSerializer ,ActivityLogSerializer
)

# ─── Market GPS coordinates ───────────────────────────────────────────────────
MARKET_COORDS = {
    'Kajiado Market':    (-1.8500,  36.7820),
    'Kiserian Market':   (-1.3833,  36.6833),
    'Ngong Market':      (-1.3667,  36.6500),
    'Isinya Market':     (-1.9167,  36.9000),
    'Namanga Market':    (-2.5500,  36.7833),
    'Loitokitok Market': (-2.9000,  37.5167),
    'Bissil Market':     (-2.0833,  36.9500),
    'Ilbisil Market':    (-2.0667,  36.9333),
}
KES_PER_KM_PER_ANIMAL = 15


def haversine_km(lat1, lng1, lat2, lng2):
    R  = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lng2 - lng1)
    a  = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── Notification helper ──────────────────────────────────────────────────────
def create_notification(recipient, title, message, notif_type='INFO',
                        related_transport_id=None, related_listing_id=None,
                        related_vet_id=None, send_sms_msg=False):
    notif = Notification.objects.create(
        recipient=recipient, title=title, message=message,
        notification_type=notif_type,
        related_transport_id=related_transport_id,
        related_listing_id=related_listing_id,
        related_vet_id=related_vet_id,
    )
    if send_sms_msg:
        try:
            from .utils.sms import send_sms
            send_sms([recipient.profile.phone_number], message)
            notif.sent_via_sms = True
            notif.save()
        except Exception:
            pass
    return notif


# ─── Daraja helpers ───────────────────────────────────────────────────────────
def get_mpesa_access_token():
    key    = getattr(settings, 'MPESA_CONSUMER_KEY', '')
    secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
    creds  = base64.b64encode(f"{key}:{secret}".encode()).decode()
    url    = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    r      = http_req.get(url, headers={'Authorization': f'Basic {creds}'}, timeout=15)
    return r.json().get('access_token', '')


def stk_push(phone_number, amount, account_ref, description, callback_url):
    access_token = get_mpesa_access_token()
    shortcode    = getattr(settings, 'MPESA_SHORTCODE', '174379')
    passkey      = getattr(settings, 'MPESA_PASSKEY', '')
    timestamp    = datetime.now().strftime('%Y%m%d%H%M%S')
    password     = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    phone = str(phone_number).replace('+', '').replace(' ', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]

    payload = {
        "BusinessShortCode": shortcode, "Password": password,
        "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline",
        "Amount": int(float(amount)), "PartyA": phone, "PartyB": shortcode,
        "PhoneNumber": phone, "CallBackURL": callback_url,
        "AccountReference": account_ref, "TransactionDesc": description,
    }
    r = http_req.post(
        'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
        json=payload,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=20,
    )
    return r.json()


# ─── JWT ──────────────────────────────────────────────────────────────────────
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_type'] = user.profile.user_type
        token['username']  = user.username
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ─── Registration ─────────────────────────────────────────────────────────────
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username     = request.data.get('username')
        password     = request.data.get('password')
        email        = request.data.get('email', '')
        phone_number = request.data.get('phone_number', '')
        county       = request.data.get('county', 'Kajiado')
        sub_county   = request.data.get('sub_county', '')
        user_type    = request.data.get('user_type', 'PASTORALIST')

        if not username or not password:
            return Response({'error': 'Username and password required'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=400)

        user = User.objects.create_user(username=username, password=password, email=email)
        UserProfile.objects.create(
            user=user, phone_number=phone_number,
            county=county, sub_county=sub_county, user_type=user_type,
        )
        return Response({'message': 'User created successfully'}, status=201)


# ─── ViewSets ─────────────────────────────────────────────────────────────────
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = User.objects.all()
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.profile.user_type == 'ADMIN':
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset           = UserProfile.objects.all()
    serializer_class   = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.profile.user_type == 'ADMIN':
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(self.get_serializer(profile).data)


class LivestockViewSet(viewsets.ModelViewSet):
    queryset           = Livestock.objects.all()
    serializer_class   = LivestockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut == 'ADMIN':       return Livestock.objects.all()
        if ut == 'PASTORALIST': return Livestock.objects.filter(owner=self.request.user)
        if ut == 'VET':
            accepted_ids = VetRequest.objects.filter(
                vet=self.request.user,
                status__in=['ACCEPTED', 'IN_PROGRESS', 'COMPLETED']
            ).values_list('animal_id', flat=True)
            return Livestock.objects.filter(id__in=accepted_ids)
        return Livestock.objects.none()

    def perform_create(self, serializer):
        if self.request.user.profile.user_type not in ['PASTORALIST', 'ADMIN']:
            raise PermissionError("Only pastoralists can add livestock.")
        serializer.save(owner=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        hs = request.data.get('health_status')
        if hs in ('GREEN', 'YELLOW', 'RED'):
            instance.health_status_manual = hs
            instance.save()
            return Response(self.get_serializer(instance).data)
        return super().partial_update(request, *args, **kwargs)


class HealthRecordViewSet(viewsets.ModelViewSet):
    queryset           = HealthRecord.objects.all()
    serializer_class   = HealthRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut  = self.request.user.profile.user_type
        qs  = HealthRecord.objects.all()
        aid = self.request.query_params.get('animal')
        if aid:
            qs = qs.filter(animal_id=aid)
        if ut == 'ADMIN': return qs
        if ut == 'VET':
            accepted_ids = VetRequest.objects.filter(
                vet=self.request.user,
                status__in=['ACCEPTED', 'IN_PROGRESS', 'COMPLETED']
            ).values_list('animal_id', flat=True)
            return qs.filter(animal_id__in=accepted_ids)
        if ut == 'PASTORALIST':
            return qs.filter(animal__owner=self.request.user)
        return qs.none()

    def perform_create(self, serializer):
        ut = self.request.user.profile.user_type
        if ut in ['ADMIN', 'VET']:
            serializer.save(veterinarian=self.request.user)
        else:
            raise PermissionError("Only vets or admin can add health records.")


class HealthCertificateViewSet(viewsets.ModelViewSet):
    queryset           = HealthCertificate.objects.all()
    serializer_class   = HealthCertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut in ['ADMIN', 'VET']:
            return HealthCertificate.objects.all()
        if ut == 'PASTORALIST':
            return HealthCertificate.objects.filter(animal__owner=self.request.user)
        return HealthCertificate.objects.none()

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


# ─── VetRequest ───────────────────────────────────────────────────────────────
class VetRequestViewSet(viewsets.ModelViewSet):
    queryset           = VetRequest.objects.all()
    serializer_class   = VetRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut == 'ADMIN':       return VetRequest.objects.all()
        if ut == 'PASTORALIST': return VetRequest.objects.filter(pastoralist=self.request.user)
        if ut == 'VET':         return VetRequest.objects.all()
        return VetRequest.objects.none()

    def perform_create(self, serializer):
        if self.request.user.profile.user_type != 'PASTORALIST':
            raise PermissionError("Only pastoralists can request vet visits.")
        vr = serializer.save(pastoralist=self.request.user)
        for vet in User.objects.filter(profile__user_type='VET'):
            create_notification(
                vet,
                f'New Vet Request — {vr.animal.tag_id} 🐄',
                f'{self.request.user.username} needs a vet for {vr.animal.tag_id} '
                f'({vr.animal.species}). Urgency: {vr.urgency}. Symptoms: {vr.symptoms[:100]}',
                'VET_REQUEST', related_vet_id=vr.id, send_sms_msg=True,
            )

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        if request.user.profile.user_type != 'VET':
            return Response({'error': 'Only vets can accept vet requests'}, status=403)
        vr = self.get_object()
        if vr.status != 'PENDING':
            return Response({'error': f'Cannot accept a request with status {vr.status}'}, status=400)

        fee             = request.data.get('consultation_fee')
        vr.vet          = request.user
        vr.status       = 'ACCEPTED'
        vr.accepted_at  = timezone.now()
        vr.consultation_fee = fee
        vr.save()

        create_notification(
            vr.pastoralist, 'Vet Accepted Your Request 💉',
            f'Dr. {request.user.username} has accepted your vet request for {vr.animal.tag_id}. '
            f'They are on their way. Fee: KES {fee or "TBD"}.',
            'VET_ACCEPTED', related_vet_id=vr.id, send_sms_msg=True,
        )
        return Response({
            'message': 'Request accepted', 'status': vr.status,
            'vet': request.user.username,
            'vet_phone': request.user.profile.phone_number,
            'consultation_fee': fee,
        })

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        vr = self.get_object()
        if vr.pastoralist != request.user:
            return Response({'error': 'Only the requesting pastoralist can mark complete'}, status=403)
        if vr.status not in ['ACCEPTED', 'IN_PROGRESS']:
            return Response({'error': f'Cannot complete a request with status {vr.status}'}, status=400)
        vr.status       = 'COMPLETED'
        vr.completed_at = timezone.now()
        vr.save()
        create_notification(
            vr.vet, 'Visit Marked Complete ✅',
            f'{request.user.username} confirmed your visit to {vr.animal.tag_id} is complete. '
            f'Payment of KES {vr.consultation_fee} is due.',
            'CONFIRMATION', related_vet_id=vr.id,
        )
        return Response({'message': 'Marked as complete', 'status': vr.status})

    @action(detail=True, methods=['post'], url_path='update-location')
    def update_location(self, request, pk=None):
        if request.user.profile.user_type != 'VET':
            return Response({'error': 'Only vets can update location'}, status=403)
        vr  = self.get_object()
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        if lat is None or lng is None:
            return Response({'error': 'lat and lng required'}, status=400)
        vr.vet_current_location = Point(float(lng), float(lat), srid=4326)
        vr.save(update_fields=['vet_current_location'])
        return Response({'message': 'Location updated'})

    @action(detail=True, methods=['get'], url_path='vet-location')
    def vet_location(self, request, pk=None):
        vr = self.get_object()
        if vr.pastoralist != request.user and vr.vet != request.user \
           and request.user.profile.user_type != 'ADMIN':
            return Response({'error': 'Not authorised'}, status=403)
        if not vr.vet:
            return Response({'error': 'No vet assigned yet'}, status=404)
        if vr.vet_current_location:
            loc = vr.vet_current_location
            return Response({
                'lat': loc.y, 'lng': loc.x,
                'vet_name':  vr.vet.username,
                'vet_phone': vr.vet.profile.phone_number,
            })
        return Response({'error': 'Vet location not available yet'}, status=404)

    @action(detail=True, methods=['get'], url_path='pastoralist-location')
    def pastoralist_location(self, request, pk=None):
        vr = self.get_object()
        if vr.vet != request.user and request.user.profile.user_type != 'ADMIN':
            return Response({'error': 'Not authorised'}, status=403)
        if vr.pastoralist_location:
            loc = vr.pastoralist_location
            return Response({
                'lat':           loc.y,
                'lng':           loc.x,
                'name':          vr.pastoralist.username,
                'phone':         vr.pastoralist.profile.phone_number,
                'location_name': vr.pastoralist_location_name or '',
            })
        return Response({'error': 'Pastoralist location not available'}, status=404)

    @action(detail=True, methods=['post'], url_path='initiate-payment')
    def initiate_payment(self, request, pk=None):
        vr = self.get_object()
        if vr.pastoralist != request.user:
            return Response({'error': 'Not authorised'}, status=403)
        if vr.status != 'COMPLETED':
            return Response({'error': 'Visit must be completed before payment'}, status=400)
        if not vr.consultation_fee:
            return Response({'error': 'Consultation fee not set by vet'}, status=400)

        callback_url = getattr(settings, 'MPESA_CALLBACK_URL',
                               request.build_absolute_uri('/api/mpesa/callback/'))
        result = stk_push(
            phone_number=request.user.profile.phone_number,
            amount=vr.consultation_fee,
            account_ref=f'VET-{vr.id}',
            description=f'Vet visit — {vr.animal.tag_id}',
            callback_url=callback_url,
        )
        if result.get('ResponseCode') == '0':
            tx = Transaction.objects.create(
                vet_request=vr, buyer=request.user, seller=vr.vet,
                amount=vr.consultation_fee, transaction_type='VET',
                mpesa_checkout_request_id=result.get('CheckoutRequestID', ''),
                destination_name=f'Vet visit — {vr.animal.tag_id}',
            )
            vr.mpesa_checkout_request_id = result.get('CheckoutRequestID', '')
            vr.save(update_fields=['mpesa_checkout_request_id'])
            return Response({
                'message': 'STK push sent to your phone',
                'checkout_request_id': result.get('CheckoutRequestID'),
                'transaction_id': tx.id,
            })
        return Response({'error': 'STK push failed', 'detail': result}, status=400)

    @action(detail=False, methods=['get'], url_path='my-stats')
    def my_stats(self, request):
        if request.user.profile.user_type != 'VET':
            return Response({'error': 'Vets only'}, status=403)
        qs         = VetRequest.objects.filter(vet=request.user)
        this_month = timezone.now().date().replace(day=1)
        return Response({
            'pending':         VetRequest.objects.filter(status='PENDING').count(),
            'accepted':        qs.filter(status__in=['ACCEPTED', 'IN_PROGRESS']).count(),
            'completed':       qs.filter(status='COMPLETED').count(),
            'completed_month': qs.filter(status='COMPLETED',
                                         completed_at__date__gte=this_month).count(),
            'animals_treated': qs.filter(status='COMPLETED').values('animal').distinct().count(),
            'certs_issued':    HealthCertificate.objects.filter(issued_by=request.user).count(),
        })


# ─── Vehicle ──────────────────────────────────────────────────────────────────
class VehicleViewSet(viewsets.ModelViewSet):
    queryset           = Vehicle.objects.all()
    serializer_class   = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut == 'ADMIN':       return Vehicle.objects.all()
        if ut == 'TRANSPORTER': return Vehicle.objects.filter(owner=self.request.user)
        return Vehicle.objects.none()

    def perform_create(self, serializer):
        if self.request.user.profile.user_type != 'TRANSPORTER':
            raise PermissionError("Only transporters can add vehicles.")
        serializer.save(owner=self.request.user)


# ─── TransportRequest ─────────────────────────────────────────────────────────
class TransportRequestViewSet(viewsets.ModelViewSet):
    queryset           = TransportRequest.objects.all()
    serializer_class   = TransportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut == 'ADMIN':       return TransportRequest.objects.all()
        if ut == 'PASTORALIST': return TransportRequest.objects.filter(requester=self.request.user)
        if ut == 'TRANSPORTER': return TransportRequest.objects.all()
        return TransportRequest.objects.none()

    def perform_create(self, serializer):
        if self.request.user.profile.user_type != 'PASTORALIST':
            raise PermissionError("Only pastoralists can request transport.")
        serializer.save(requester=self.request.user)

    def perform_update(self, serializer):
        old      = self.get_object()
        instance = serializer.save()
        if instance.status == 'COMPLETED' and old.status != 'COMPLETED':
            create_notification(
                instance.requester, 'Trip Completed — Payment Due 💳',
                f'Your trip to {instance.destination_name} is complete. '
                f'Pay KES {instance.trip_cost} via M-Pesa.',
                'PAYMENT', related_transport_id=instance.id, send_sms_msg=True,
            )

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        if request.user.profile.user_type != 'TRANSPORTER':
            return Response({'error': 'Only transporters can accept requests'}, status=403)
        tr = self.get_object()
        if tr.status != 'PENDING':
            return Response({'error': f'Cannot accept a request with status {tr.status}'}, status=400)

        # ── Distance-based price ──────────────────────────────────────────────
        distance_km = 0.0
        trip_cost   = 0.0
        try:
            origin_lat, origin_lng = tr.origin.y, tr.origin.x
            dest_coords = MARKET_COORDS.get(tr.destination_name)
            if dest_coords:
                dest_lat, dest_lng = dest_coords
                distance_km = max(5.0, round(
                    haversine_km(origin_lat, origin_lng, dest_lat, dest_lng), 1
                ))
                trip_cost = round(distance_km * KES_PER_KM_PER_ANIMAL * tr.animal_count, 2)
            else:
                trip_cost = round(50.0 * tr.animal_count, 2)
        except Exception:
            trip_cost = round(50.0 * tr.animal_count, 2)

        tr.accepted_by = request.user
        tr.status      = 'ASSIGNED'
        tr.trip_cost   = trip_cost
        tr.save()

        # Lookup vehicle details for notification (optional — vehicle may not exist)
        vehicle_info = ''
        try:
            v = request.user.vehicles.first()
            if v:
                vehicle_info = f' Vehicle: {v.registration_number} ({v.get_vehicle_type_display()}).'
        except Exception:
            pass

        create_notification(
            tr.requester, 'Driver Accepted Your Request 🚛',
            f'{request.user.username} accepted your transport request for '
            f'{tr.animal_count} animals to {tr.destination_name}. '
            f'Distance: ~{distance_km:.0f} km. Trip cost: KES {trip_cost:,.0f}.{vehicle_info} '
            f'Track their live location in the app.',
            'CONFIRMATION', related_transport_id=tr.id, send_sms_msg=True,
        )
        return Response({
            'message':     'Request accepted',
            'status':      tr.status,
            'accepted_by': request.user.username,
            'phone':       request.user.profile.phone_number,
            'distance_km': distance_km,
            'trip_cost':   trip_cost,
        })

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        tr = self.get_object()
        if tr.requester != request.user:
            return Response({'error': 'Only the requesting pastoralist can mark complete'}, status=403)
        if tr.status not in ['ASSIGNED', 'IN_TRANSIT']:
            return Response({'error': f'Cannot complete a request with status {tr.status}'}, status=400)
        tr.status = 'COMPLETED'
        tr.save()
        if tr.accepted_by:
            create_notification(
                tr.accepted_by, 'Delivery Confirmed Complete ✅',
                f'{request.user.username} confirmed delivery of {tr.animal_count} animals '
                f'to {tr.destination_name}. Payment of KES {tr.trip_cost} will be initiated.',
                'CONFIRMATION', related_transport_id=tr.id,
            )
        create_notification(
            request.user, 'Trip Complete — Payment Due 💳',
            f'Your trip to {tr.destination_name} is marked complete. '
            f'Pay KES {tr.trip_cost} to the driver via M-Pesa.',
            'PAYMENT', related_transport_id=tr.id,
        )
        return Response({'message': 'Marked as complete', 'status': tr.status,
                         'trip_cost': tr.trip_cost})

    # ✅ FIX: saves directly to TransportRequest.driver_current_location
    @action(detail=True, methods=['post'], url_path='update-location')
    def update_location(self, request, pk=None):
        if request.user.profile.user_type != 'TRANSPORTER':
            return Response({'error': 'Only transporters can update location'}, status=403)
        tr = self.get_object()
        if tr.accepted_by != request.user:
            return Response({'error': 'You did not accept this request'}, status=403)

        lat = request.data.get('lat')
        lng = request.data.get('lng')
        if lat is None or lng is None:
            return Response({'error': 'lat and lng required'}, status=400)

        # ✅ KEY FIX: store on the request itself — no Vehicle dependency
        tr.driver_current_location = Point(float(lng), float(lat), srid=4326)
        tr.save(update_fields=['driver_current_location'])
        return Response({'message': 'Location updated', 'lat': lat, 'lng': lng})

    # ✅ FIX: reads from TransportRequest.driver_current_location
    @action(detail=True, methods=['get'], url_path='driver-location')
    def driver_location(self, request, pk=None):
        tr = self.get_object()
        # Both the pastoralist and the driver can poll this
        if tr.requester != request.user and tr.accepted_by != request.user \
           and request.user.profile.user_type != 'ADMIN':
            return Response({'error': 'Not authorised'}, status=403)
        if not tr.accepted_by:
            return Response({'error': 'No driver assigned yet'}, status=404)

        # ✅ KEY FIX: read from request field, not from vehicle
        if tr.driver_current_location:
            loc = tr.driver_current_location
            # Try to enrich with vehicle info if available
            vehicle_reg = ''
            try:
                v = tr.accepted_by.vehicles.first()
                if v:
                    vehicle_reg = v.registration_number
            except Exception:
                pass
            return Response({
                'lat':                  loc.y,
                'lng':                  loc.x,
                'driver_name':          tr.accepted_by.username,
                'driver_phone':         tr.accepted_by.profile.phone_number,
                'vehicle_registration': vehicle_reg,
            })
        return Response({'error': 'Driver location not available yet — waiting for driver GPS'}, status=404)

    @action(detail=True, methods=['post'], url_path='initiate-payment')
    def initiate_payment(self, request, pk=None):
        tr = self.get_object()
        if tr.requester != request.user:
            return Response({'error': 'Not authorised'}, status=403)
        if not tr.trip_cost:
            return Response({'error': 'Trip cost not set yet'}, status=400)

        callback_url = getattr(settings, 'MPESA_CALLBACK_URL',
                               request.build_absolute_uri('/api/mpesa/callback/'))
        result = stk_push(
            phone_number=request.user.profile.phone_number,
            amount=tr.trip_cost,
            account_ref=f'TRANSPORT-{tr.id}',
            description=f'AgriPulse transport to {tr.destination_name}',
            callback_url=callback_url,
        )
        if result.get('ResponseCode') == '0':
            if tr.accepted_by:
                Transaction.objects.create(
                    transport_request=tr, buyer=request.user,
                    seller=tr.accepted_by, amount=tr.trip_cost,
                    transaction_type='TRANSPORT',
                    mpesa_checkout_request_id=result.get('CheckoutRequestID', ''),
                    destination_name=tr.destination_name,
                )
            return Response({
                'message':             'STK push sent to your phone',
                'checkout_request_id': result.get('CheckoutRequestID'),
            })
        return Response({'error': 'STK push failed', 'detail': result}, status=400)


class PoolingGroupViewSet(viewsets.ModelViewSet):
    queryset           = PoolingGroup.objects.all()
    serializer_class   = PoolingGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut in ['ADMIN', 'TRANSPORTER']: return PoolingGroup.objects.all()
        if ut == 'PASTORALIST':
            return PoolingGroup.objects.filter(
                requests__requester=self.request.user
            ).distinct()
        return PoolingGroup.objects.none()


class TripViewSet(viewsets.ModelViewSet):
    queryset           = Trip.objects.all()
    serializer_class   = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut in ['ADMIN', 'TRANSPORTER']: return Trip.objects.all()
        if ut == 'PASTORALIST':
            return Trip.objects.filter(
                pooling_groups__requests__requester=self.request.user
            ).distinct()
        return Trip.objects.none()


class TripManifestViewSet(viewsets.ModelViewSet):
    queryset           = TripManifest.objects.all()
    serializer_class   = TripManifestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut in ['ADMIN', 'TRANSPORTER']: return TripManifest.objects.all()
        if ut == 'PASTORALIST':
            return TripManifest.objects.filter(request__requester=self.request.user)
        return TripManifest.objects.none()


class TripAnimalViewSet(viewsets.ModelViewSet):
    queryset           = TripAnimal.objects.all()
    serializer_class   = TripAnimalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut in ['ADMIN', 'TRANSPORTER']: return TripAnimal.objects.all()
        if ut == 'PASTORALIST':
            return TripAnimal.objects.filter(
                trip_manifest__request__requester=self.request.user
            )
        return TripAnimal.objects.none()


class MarketListingViewSet(viewsets.ModelViewSet):
    queryset           = MarketListing.objects.all()
    serializer_class   = MarketListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ut = self.request.user.profile.user_type
        if ut == 'ADMIN':       return MarketListing.objects.all()
        if ut == 'PASTORALIST': return MarketListing.objects.filter(seller=self.request.user)
        return MarketListing.objects.none()

    @action(detail=False, methods=['get'])
    def public(self, request):
        return Response(self.get_serializer(
            MarketListing.objects.filter(status='ACTIVE'), many=True
        ).data)

    @action(detail=True, methods=['get'], url_path='seller-location')
    def seller_location(self, request, pk=None):
        listing = self.get_object()
        try:
            profile = listing.seller.profile
            loc     = profile.location
            if loc:
                return Response({
                    'lat':           loc.y,
                    'lng':           loc.x,
                    'seller_name':   listing.seller.username,
                    'seller_phone':  profile.phone_number,
                    'location_name': f"{profile.county} {profile.sub_county}".strip(),
                })
        except Exception:
            pass
        return Response({'error': 'Seller location not set'}, status=404)

    def perform_create(self, serializer):
        if self.request.user.profile.user_type != 'PASTORALIST':
            raise PermissionError("Only pastoralists can list animals for sale.")
        serializer.save(seller=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset           = Transaction.objects.all()
    serializer_class   = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        ut   = self.request.user.profile.user_type
        user = self.request.user
 
        if ut == 'ADMIN':
            # Admin sees everything
            return Transaction.objects.all().order_by('-transaction_date')
 
        if ut == 'PASTORALIST':
            # Pastoralist is the BUYER when paying vets and drivers
            # Pastoralist is the SELLER when their livestock is purchased
            return Transaction.objects.filter(
                Q(buyer=user) | Q(seller=user)
            ).distinct().order_by('-transaction_date')
 
        if ut == 'BUYER':
            # Buyer only pays — always the buyer in marketplace transactions
            return Transaction.objects.filter(
                buyer=user
            ).order_by('-transaction_date')
 
        if ut == 'VET':
            # Vet receives payment — they are the seller in VET transactions
            return Transaction.objects.filter(
                seller=user,
                transaction_type='VET'
            ).order_by('-transaction_date')
 
        if ut == 'TRANSPORTER':
            # Transporter receives payment — seller in TRANSPORT transactions
            return Transaction.objects.filter(
                seller=user,
                transaction_type='TRANSPORT'
            ).order_by('-transaction_date')
 
        return Transaction.objects.none()

class PriceDataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = PriceData.objects.all().order_by('-date')
    serializer_class   = PriceDataSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotificationViewSet(viewsets.ModelViewSet):
    queryset           = Notification.objects.all()
    serializer_class   = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({'message': 'All marked as read'})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'unread': Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()})


class OfflineActionViewSet(viewsets.ModelViewSet):
    queryset           = OfflineAction.objects.all()
    serializer_class   = OfflineActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OfflineAction.objects.filter(user=self.request.user)


# ─── M-Pesa marketplace STK push ─────────────────────────────────────────────
class MpesaMarketplaceSTKView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        listing_id = request.data.get('listing_id')
        try:
            listing = MarketListing.objects.get(id=listing_id, status='ACTIVE')
        except MarketListing.DoesNotExist:
            return Response({'error': 'Listing not found or not active'}, status=404)

        callback_url = getattr(settings, 'MPESA_CALLBACK_URL',
                               request.build_absolute_uri('/api/mpesa/callback/'))
        result = stk_push(
            phone_number=request.user.profile.phone_number,
            amount=listing.asking_price,
            account_ref=f'LISTING-{listing_id}',
            description=f'Purchase {listing.animal.tag_id}',
            callback_url=callback_url,
        )
        if result.get('ResponseCode') == '0':
            tx = Transaction.objects.create(
                listing=listing, buyer=request.user, seller=listing.seller,
                amount=listing.asking_price, transaction_type='MARKETPLACE',
                mpesa_checkout_request_id=result.get('CheckoutRequestID', ''),
            )
            create_notification(
                listing.seller, 'New Purchase Initiated 💰',
                f'{request.user.username} is buying {listing.animal.tag_id} '
                f'for KES {listing.asking_price}.',
                'INFO', related_listing_id=listing_id,
            )
            return Response({
                'message':             'STK push sent',
                'checkout_request_id': result.get('CheckoutRequestID'),
                'transaction_id':      tx.id,
            })
        return Response({'error': 'STK push failed', 'detail': result}, status=400)


# ─── Daraja callback ──────────────────────────────────────────────────────────
class MpesaCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            cb          = request.data['Body']['stkCallback']
            checkout_id = cb['CheckoutRequestID']
            result_code = cb['ResultCode']
            tx = Transaction.objects.filter(
                mpesa_checkout_request_id=checkout_id
            ).first()

            if tx and result_code == 0:
                receipt = next(
                    (item['Value']
                     for item in cb.get('CallbackMetadata', {}).get('Item', [])
                     if item['Name'] == 'MpesaReceiptNumber'),
                    ''
                )
                tx.mpesa_receipt = receipt
                tx.is_completed  = True
                tx.save()

                if tx.listing:
                    tx.listing.status = 'SOLD'
                    tx.listing.save()
                    create_notification(tx.buyer, 'Payment Successful ✅',
                        f'KES {tx.amount} received. Receipt: {receipt}', 'PAYMENT')
                    create_notification(tx.seller, 'Payment Received 💳',
                        f'KES {tx.amount} for {tx.listing.animal.tag_id}. Receipt: {receipt}',
                        'PAYMENT')

                if tx.transport_request:
                    tx.transport_request.payment_status = 'PAID'
                    tx.transport_request.mpesa_receipt  = receipt
                    tx.transport_request.save()
                    create_notification(tx.buyer, 'Transport Payment Confirmed ✅',
                        f'KES {tx.amount} paid. Receipt: {receipt}', 'PAYMENT')
                    create_notification(tx.seller, 'Transport Payment Received 💳',
                        f'KES {tx.amount} received. Receipt: {receipt}', 'PAYMENT')

                if tx.vet_request:
                    vr = tx.vet_request
                    vr.payment_status = 'PAID'
                    vr.mpesa_receipt  = receipt
                    vr.save()
                    create_notification(tx.buyer, 'Vet Payment Successful ✅',
                        f'KES {tx.amount} paid to Dr. {vr.vet.username}. Receipt: {receipt}',
                        'PAYMENT')
                    create_notification(vr.vet, 'Vet Payment Received 💳',
                        f'KES {tx.amount} for visit to {vr.animal.tag_id}. Receipt: {receipt}',
                        'PAYMENT')
        except Exception:
            pass

        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only.
    Admin sees all logs.
    Any other authenticated user sees only their own logs.
    """
    serializer_class   = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def get_queryset(self):
        user = self.request.user
        ut   = user.profile.user_type
 
        qs = ActivityLog.objects.select_related('user').all()
 
        if ut != 'ADMIN':
            qs = qs.filter(user=user)
 
        # Optional query-param filters
        role      = self.request.query_params.get('role')
        username  = self.request.query_params.get('username')
        date_from = self.request.query_params.get('date_from')
        date_to   = self.request.query_params.get('date_to')
        method    = self.request.query_params.get('method')
        search    = self.request.query_params.get('search')
 
        if role:      qs = qs.filter(role=role.upper())
        if username:  qs = qs.filter(user__username__icontains=username)
        if date_from: qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:   qs = qs.filter(timestamp__date__lte=date_to)
        if method:    qs = qs.filter(method=method.upper())
        if search:    qs = qs.filter(action__icontains=search)
 
        return qs.order_by('-timestamp')[:500]   # cap at 500 rows per request
 