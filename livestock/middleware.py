"""
livestock/middleware.py

Drop this file into your livestock/ app folder.
It automatically logs every authenticated API request to the ActivityLog table.
No changes to any existing view are needed.
"""

import json
import re
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin




ACTION_MAP = [
    # Auth
    (r'POST',   r'/api/token/$',                  'Signed in'),
    (r'POST',   r'/api/register/$',               'Registered a new account'),

    # Livestock
    (r'GET',    r'/api/livestock/$',              'Viewed livestock list'),
    (r'POST',   r'/api/livestock/$',              'Registered a new animal'),
    (r'GET',    r'/api/livestock/(\d+)/$',        'Viewed animal #{id}'),
    (r'PATCH',  r'/api/livestock/(\d+)/$',        'Updated animal #{id}'),
    (r'DELETE', r'/api/livestock/(\d+)/$',        'Deleted animal #{id}'),

    # Health records
    (r'GET',    r'/api/health-records/$',         'Viewed health records'),
    (r'POST',   r'/api/health-records/$',         'Added a health record'),
    (r'GET',    r'/api/health-certificates/$',    'Viewed health certificates'),
    (r'POST',   r'/api/health-certificates/$',    'Issued a health certificate'),

    # Vet requests
    (r'GET',    r'/api/vet-requests/$',           'Viewed vet requests'),
    (r'POST',   r'/api/vet-requests/$',           'Submitted a new vet visit request'),
    (r'POST',   r'/api/vet-requests/(\d+)/accept/$',          'Accepted vet request #{id}'),
    (r'POST',   r'/api/vet-requests/(\d+)/mark-complete/$',   'Marked vet visit #{id} complete'),
    (r'POST',   r'/api/vet-requests/(\d+)/initiate-payment/$','Initiated M-Pesa payment for vet visit #{id}'),
    (r'POST',   r'/api/vet-requests/(\d+)/update-location/$', 'Updated vet GPS location for request #{id}'),

    # Transport
    (r'GET',    r'/api/transport-requests/$',     'Viewed transport requests'),
    (r'POST',   r'/api/transport-requests/$',     'Submitted a new transport request'),
    (r'POST',   r'/api/transport-requests/(\d+)/accept/$',          'Accepted transport request #{id}'),
    (r'POST',   r'/api/transport-requests/(\d+)/mark-complete/$',   'Marked transport #{id} as delivered'),
    (r'POST',   r'/api/transport-requests/(\d+)/initiate-payment/$','Initiated M-Pesa payment for transport #{id}'),
    (r'POST',   r'/api/transport-requests/(\d+)/update-location/$', 'Updated driver GPS for request #{id}'),

    # Marketplace
    (r'GET',    r'/api/market-listings/public/$', 'Browsed marketplace listings'),
    (r'POST',   r'/api/market-listings/$',        'Created a new marketplace listing'),
    (r'DELETE', r'/api/market-listings/(\d+)/$',  'Removed listing #{id}'),

    # Vehicles
    (r'GET',    r'/api/vehicles/$',               'Viewed vehicle details'),
    (r'POST',   r'/api/vehicles/$',               'Registered a vehicle'),
    (r'PATCH',  r'/api/vehicles/(\d+)/$',         'Updated vehicle #{id}'),

    # Payments
    (r'POST',   r'/api/mpesa/stk/$',              'Initiated M-Pesa marketplace payment'),
    (r'POST',   r'/api/mpesa/callback/$',         'M-Pesa payment callback received'),

    # Transactions
    (r'GET',    r'/api/transactions/$',           'Viewed transaction history'),

    # Notifications
    (r'GET',    r'/api/notifications/$',          'Viewed notifications'),
    (r'POST',   r'/api/notifications/mark-all-read/$', 'Marked all notifications as read'),

    # Profile
    (r'GET',    r'/api/profiles/me/$',            'Viewed own profile'),
    (r'PATCH',  r'/api/profiles/(\d+)/$',         'Updated profile'),

    # Price data
    (r'GET',    r'/api/price-data/$',             'Viewed market prices'),
]

# Endpoints to skip logging (too noisy / internal polling)
SKIP_PATTERNS = [
    r'/api/vet-requests/\d+/vet-location/$',
    r'/api/vet-requests/\d+/pastoralist-location/$',
    r'/api/transport-requests/\d+/driver-location/$',
    r'/api/notifications/unread-count/$',
    r'/api/vet-requests/\d+/update-location/$',
    r'/api/transport-requests/\d+/update-location/$',
    r'/admin/',
    r'/static/',
    r'/media/',
]


def _get_description(method, path):
    """Return human-readable description for a given METHOD + path."""
    for meth_pattern, url_pattern, description in ACTION_MAP:
        if method != meth_pattern:
            continue
        m = re.match(url_pattern, path)
        if m:
            resource_id = m.group(1) if m.lastindex else ''
            return description.replace('{id}', resource_id)
    return f'{method} {path}'


def _should_skip(path):
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, path):
            return True
    return False


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


class ActivityLogMiddleware(MiddlewareMixin):
    """
    Logs every authenticated API request to ActivityLog.
    Runs after the response is generated so we can capture the status code.
    """

    def process_response(self, request, response):
        try:
            path = request.path

            # Skip non-API and noisy polling endpoints
            if not path.startswith('/api/'):
                return response
            if _should_skip(path):
                return response

            # Only log authenticated users
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                return response

            method      = request.method
            status_code = response.status_code
            description = _get_description(method, path)
            ip_address  = _get_client_ip(request)
            user_agent  = request.META.get('HTTP_USER_AGENT', '')[:200]

            # Try to get role
            try:
                role = user.profile.user_type
            except Exception:
                role = 'UNKNOWN'

            # Lazy import to avoid circular dependency
            from livestock.models import ActivityLog
            ActivityLog.objects.create(
                user        = user,
                role        = role,
                action      = description,
                method      = method,
                endpoint    = path[:200],
                status_code = status_code,
                ip_address  = ip_address,
                user_agent  = user_agent,
            )
        except Exception:
            # Never let logging crash the app
            pass

        return response