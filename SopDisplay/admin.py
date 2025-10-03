from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Product, ProductMedia, Station

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ['file', 'file_preview', 'duration']
    readonly_fields = ['file_preview']

    def file_preview(self, obj):
        if obj.file:
            file_url = obj.file.url
            file_name = obj.file.name.lower()
            if file_name.endswith('.pdf'):
                return format_html('<a href="{}" target="_blank">View PDF</a>', file_url)
            elif file_name.endswith(('.mp4', '.mov')):
                return format_html('<video width="100" height="100" controls><source src="{}" type="video/mp4"></video>', file_url)
            else:
                return format_html('<a href="{}">View File</a>', file_url)
        return "No file"
    file_preview.short_description = 'File Preview'
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'duration':
            field.label = 'Duration (in seconds)'
        return field
    

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('code', 'name')
    inlines = [ProductMediaInline]

    def station_list(self, obj):
        return ", ".join([station.name for station in obj.stations.all()])
    station_list.short_description = 'Stations'

@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = ['product', 'file', 'file_preview', 'duration']
    list_filter = ['product']
    search_fields = ['product__code', 'product__name', 'file']
    readonly_fields = ['file_preview']

    def file_preview(self, obj):
        if obj.file:
            file_url = obj.file.url
            file_name = obj.file.name.lower()
            if file_name.endswith('.pdf'):
                return format_html('<a href="{}" target="_blank">View PDF</a>', file_url)
            elif file_name.endswith(('.mp4', '.mov')):
                return format_html('<video width="100" height="100" controls><source src="{}" type="video/mp4"></video>', file_url)
            elif file_name.endswith(('.xlsx', '.xls')):
                return format_html('<a href="{}" target="_blank">View Excel</a>', file_url)
            else:
                return format_html('<a href="{}">View File</a>', file_url)
        return "No file"
    def duration_with_unit(self, obj):
        return f"{obj.duration} (seconds)" if obj.duration is not None else "-"
    duration_with_unit.short_description = 'Duration in seconds'

class StationAdminForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = ['name','screen_name', 'products', 'selected_media']
        widgets = {
            'selected_media': forms.CheckboxSelectMultiple,  # Allow selecting multiple media files
        }

    def __init__(self, *args, **kwargs):
        super(StationAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # If the station instance exists, filter selected_media by products linked to this station
            self.fields['selected_media'].queryset = ProductMedia.objects.filter(product__in=self.instance.products.all())
        else:
            # If no station instance, show no media files initially
            self.fields['selected_media'].queryset = ProductMedia.objects.none()

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    form = StationAdminForm
    list_display = ('name', 'product_count', 'media_count')
    filter_horizontal = ('products', 'selected_media')  # Allow selecting multiple products and media

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Number of Products'

    def media_count(self, obj):
        return obj.selected_media.count()
    media_count.short_description = 'Number of Selected Media'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('product_count', 'media_count')
        return self.readonly_fields

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        station = self.get_object(request, object_id)
        if station:
            # Display all media associated with the products linked to this station
            product_media = ProductMedia.objects.filter(product__in=station.products.all())
            extra_context['product_media'] = product_media
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
