from django.shortcuts import render
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Station, ProductMedia
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.db.models.functions import ExtractHour  # Correct import for ExtractHour

# Create your views here.


def get_station_media(request, station_id):
    station = get_object_or_404(Station, pk=station_id)
    selected_media = station.selected_media.all()
    
    media_data = []
    for m in selected_media:
        media_type = m.file.name.split('.')[-1].lower()
        media_info = {
            'id': m.id,
            'url': m.file.url,
            'type': media_type,
            'duration': m.duration,
            'product_name': m.product.name,
            'product_code': m.product.code
        }
        
        # If it's an Excel file and has a PDF version, use that instead
        if media_type in ['xlsx', 'xls'] and m.pdf_version:
            media_info['url'] = m.pdf_version.url
            media_info['type'] = 'pdf'
        
        media_data.append(media_info)
    
    return JsonResponse({'media': media_data})


def station_media_slider(request, station_id):
    station = get_object_or_404(Station, pk=station_id)
    # Use the related_name from the M2M field
    selected_media = station.selected_media.all()
    return render(request, 'station_slider.html', {'station': station, 'selected_media': selected_media})
