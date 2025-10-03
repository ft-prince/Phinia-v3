from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('<int:station_id>/media/', views.get_station_media, name='station_media'),
    path('<int:station_id>/slider/', views.station_media_slider, name='station_media_slider'),


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)