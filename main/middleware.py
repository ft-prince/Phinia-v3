from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.contrib import messages
from django.utils import timezone
from datetime import time

class ShiftMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.user_type == 'operator':
            current_time = timezone.localtime().time()
            is_day_shift = time(8, 0) <= current_time < time(20, 0)
            
            # Store current shift information in request
            request.current_shift = 'day' if is_day_shift else 'night'
            request.shift_start = time(8, 0) if is_day_shift else time(20, 0)
            request.shift_end = time(20, 0) if is_day_shift else time(8, 0)

        response = self.get_response(request)
        return response

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Initialize without reverse lookup
        self.open_urls = [
            '/login/',
            '/register/',
            '/admin/login/',
            '/admin/'
        ]

    def __call__(self, request):
        path = request.path_info
        
        # Check if path is in open URLs
        if not request.user.is_authenticated and path not in self.open_urls and not path.startswith('/admin/'):
            messages.warning(request, 'Please login to access this page.')
            try:
                login_url = reverse('login')
            except NoReverseMatch:
                login_url = '/login/'
            return redirect(f"{login_url}?next={path}")
            
        response = self.get_response(request)
        return response