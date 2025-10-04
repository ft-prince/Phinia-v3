from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count

from .models import (
    User, Shift, ChecklistBase, SubgroupEntry, SubgroupVerification, 
    SubgroupEditHistory, Verification, Concern, SubgroupFrequencyConfig, 
    ChecksheetContentConfig, DailyVerificationStatus, 
    ErrorPreventionCheck, ErrorPreventionMechanism, 
    ErrorPreventionMechanismStatus, ErrorPreventionCheckHistory,
    ErrorPreventionMechanismHistory
)


# ============ USER ADMIN ============

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('company_id', 'skill_matrix_level', 'user_type')}),
    )
    list_display = ['username', 'email', 'company_id', 'user_type', 'is_staff']
    list_filter = ['user_type', 'is_staff', 'is_active']

admin.site.register(User, CustomUserAdmin)


# ============ CONFIGURATION ADMINS ============

@admin.register(SubgroupFrequencyConfig)
class SubgroupFrequencyConfigAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'frequency_hours', 'max_subgroups', 'is_active']
    list_filter = ['is_active', 'frequency_hours']
    list_editable = ['frequency_hours', 'max_subgroups', 'is_active']
    
    fieldsets = (
        ('Model Configuration', {
            'fields': ('model_name', 'is_active')
        }),
        ('Frequency Settings', {
            'fields': ('frequency_hours', 'max_subgroups'),
            'description': 'Configure measurement frequency and maximum subgroups per shift'
        }),
    )


@admin.register(ChecksheetContentConfig)
class ChecksheetContentConfigAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'parameter_name', 'measurement_type', 'order', 'is_active']
    list_filter = ['model_name', 'measurement_type', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['parameter_name', 'parameter_name_hindi']
    actions = ['duplicate_to_all_models']
    
    def duplicate_to_all_models(self, request, queryset):
        """Duplicate selected parameters to all models"""
        count = 0
        for obj in queryset:
            for model_choice in ChecklistBase.MODEL_CHOICES:
                model_name = model_choice[0]
                if model_name != obj.model_name:
                    ChecksheetContentConfig.objects.get_or_create(
                        model_name=model_name,
                        parameter_name=obj.parameter_name,
                        defaults={
                            'parameter_name_hindi': obj.parameter_name_hindi,
                            'measurement_type': obj.measurement_type,
                            'min_value': obj.min_value,
                            'max_value': obj.max_value,
                            'unit': obj.unit,
                            'order': obj.order,
                            'is_active': obj.is_active,
                            'requires_comment_if_nok': obj.requires_comment_if_nok
                        }
                    )
                    count += 1
        self.message_user(request, f'Successfully duplicated {queryset.count()} parameters to {count} models')
    duplicate_to_all_models.short_description = "Duplicate to all models"


# ============ DAILY VERIFICATION & SHIFT ADMINS ============

@admin.register(DailyVerificationStatus)
class DailyVerificationStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'shift_display', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'date', 'shift__shift_type')
    search_fields = ('created_by__username',)
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
    
    def shift_display(self, obj):
        return obj.shift.get_shift_type_display() if obj.shift else 'N/A'
    shift_display.short_description = 'Shift'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('shift', 'created_by')


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('date', 'shift_type', 'operator', 'shift_supervisor', 'quality_supervisor')
    list_filter = ('date', 'shift_type')
    search_fields = ('operator__username', 'shift_supervisor__username', 'quality_supervisor__username')
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('operator', 'shift_supervisor', 'quality_supervisor')


# ============ CHECKLIST ADMINS ============

class SubgroupEntryInline(admin.TabularInline):
    model = SubgroupEntry
    extra = 0
    max_num = 6
    readonly_fields = ('timestamp',)


class VerificationInline(admin.TabularInline):
    model = Verification
    extra = 0
    readonly_fields = ('verified_at',)


class ConcernInline(admin.TabularInline):
    model = Concern
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(ChecklistBase)
class ChecklistBaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'selected_model', 'shift_display', 'verification_status_link', 'created_at')
    list_filter = ('status', 'selected_model', 'shift')
    search_fields = ('id', 'selected_model')
    date_hierarchy = 'created_at'
    inlines = [SubgroupEntryInline, VerificationInline, ConcernInline]
    readonly_fields = ('created_at', 'shift')
    
    def shift_display(self, obj):
        shift_choices = dict(ChecklistBase.SHIFTS)
        return shift_choices.get(obj.shift, obj.shift) if obj.shift else 'N/A'
    shift_display.short_description = 'Shift'
    
    def verification_status_link(self, obj):
        if obj.verification_status:
            try:
                url = reverse('admin:main_dailyverificationstatus_change', args=[obj.verification_status.id])
                return format_html('<a href="{}">{}</a>', url, f"Verification #{obj.verification_status.id}")
            except:
                return f"Verification #{obj.verification_status.id}"
        return 'N/A'
    verification_status_link.short_description = 'Verification Status'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('verification_status', 'status', 'selected_model', 'new_shift', 'shift')
        }),
        ('One-time Measurements', {
            'fields': ('line_pressure', 'uv_flow_input_pressure', 'test_pressure_vacuum')
        }),
        ('Status Checks', {
            'fields': ('oring_condition', 'master_verification_lvdt', 'good_bad_master_verification', 'tool_alignment')
        }),
        ('Tool Information', {
            'fields': ('top_tool_id', 'top_tool_id_status', 'bottom_tool_id', 'bottom_tool_id_status',
                      'uv_assy_stage_id', 'uv_assy_stage_id_status', 'retainer_part_no', 'retainer_part_no_status',
                      'uv_clip_part_no', 'uv_clip_part_no_status', 'umbrella_part_no', 'umbrella_part_no_status',
                      'retainer_id_lubrication', 'error_proofing_verification')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('verification_status')


@admin.register(SubgroupEntry)
class SubgroupEntryAdmin(admin.ModelAdmin):
    list_display = ['checklist', 'subgroup_number', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ('checklist__id',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ('checklist', 'team_leader', 'shift_supervisor', 'quality_supervisor', 'verified_at')
    list_filter = ('verified_at',)
    search_fields = ('team_leader__username', 'shift_supervisor__username', 'quality_supervisor__username')
    date_hierarchy = 'verified_at'
    readonly_fields = ('verified_at',)


@admin.register(Concern)
class ConcernAdmin(admin.ModelAdmin):
    list_display = ('checklist', 'concern_identified', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('concern_identified', 'cause_if_known', 'action_taken')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


# ============ ERROR PREVENTION - MASTER MECHANISM ADMIN ============

@admin.register(ErrorPreventionMechanism)
class ErrorPreventionMechanismAdmin(admin.ModelAdmin):
    """Admin interface for managing EP mechanisms - FULL ADMIN CONTROL"""
    
    list_display = (
        'mechanism_id', 
        'description_short', 
        'applicable_models', 
        'is_currently_working',  # Changed from working_status_display to make it editable
        'default_alternative_method',
        'display_order',
        'is_active',
        'usage_count'
    )
    
    list_filter = ('is_currently_working', 'is_active', 'applicable_models')
    search_fields = ('mechanism_id', 'description', 'applicable_models')
    ordering = ('display_order', 'mechanism_id')
    list_editable = ('is_currently_working', 'display_order', 'is_active')
    
    fieldsets = (
        ('Mechanism Identification', {
            'fields': ('mechanism_id', 'description', 'applicable_models')
        }),
        ('Working Status (Admin Control)', {
            'fields': ('is_currently_working', 'default_alternative_method'),
            'description': 'Control whether this mechanism is working. When OFF, operators cannot edit status field.'
        }),
        ('Display Settings', {
            'fields': ('display_order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_working', 'mark_as_not_working', 'activate', 'deactivate']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'
    
    def working_status_display(self, obj):
        if obj.is_currently_working:
            return format_html('<span style="color: green; font-weight: bold;">✓ WORKING</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">✗ NOT WORKING</span>')
    working_status_display.short_description = 'Working Status'
    
    def usage_count(self, obj):
        count = obj.daily_statuses.count()
        return format_html('<span style="background-color: #e0e0e0; padding: 3px 8px; border-radius: 3px;">{}</span>', count)
    usage_count.short_description = 'Usage Count'
    
    def mark_as_working(self, request, queryset):
        updated = queryset.update(is_currently_working=True)
        self.message_user(request, f'{updated} mechanism(s) marked as WORKING')
    mark_as_working.short_description = 'Mark as WORKING'
    
    def mark_as_not_working(self, request, queryset):
        updated = queryset.update(is_currently_working=False)
        self.message_user(request, f'{updated} mechanism(s) marked as NOT WORKING')
    mark_as_not_working.short_description = 'Mark as NOT WORKING'
    
    def activate(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} mechanism(s) activated')
    activate.short_description = 'Activate mechanisms'
    
    def deactivate(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} mechanism(s) deactivated')
    deactivate.short_description = 'Deactivate mechanisms'


# ============ ERROR PREVENTION CHECK ADMIN ============

class ErrorPreventionMechanismStatusInline(admin.TabularInline):
    model = ErrorPreventionMechanismStatus
    extra = 1  # Allow adding new rows
    can_delete = True  # Allow deletion
    
    fields = (
        'mechanism',
        'is_working_display',
        'status', 
        'is_not_applicable', 
        'alternative_method_display',
        'comments',
        'last_edited_info'
    )
    
    readonly_fields = ('is_working_display', 'alternative_method_display', 'last_edited_info')
    
    def is_working_display(self, obj):
        if obj and obj.mechanism:
            if obj.mechanism.is_currently_working:
                return format_html('<span style="color: green;">✓ Working</span>')
            else:
                return format_html('<span style="color: red;">✗ Not Working</span>')
        return 'N/A'
    is_working_display.short_description = 'Working'
    
    def alternative_method_display(self, obj):
        if obj and not obj.is_working:
            return format_html(
                '<span style="background-color: #fff3cd; padding: 2px 5px; border-radius: 3px;">{}</span>',
                obj.alternative_method
            )
        return '-'
    alternative_method_display.short_description = 'Alternative Method'
    
    def last_edited_info(self, obj):
        if obj and obj.last_edited_at and obj.last_edited_by:
            return format_html(
                '<small>{} by {}</small>',
                obj.last_edited_at.strftime('%Y-%m-%d %H:%M'),
                obj.last_edited_by.username
            )
        return '-'
    last_edited_info.short_description = 'Last Edited'


@admin.register(ErrorPreventionCheck)
class ErrorPreventionCheckAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'date', 'current_model', 'shift_display', 'operator',
        'status_badge', 'mechanism_summary', 'verification_status_link'
    )
    
    list_filter = ('status', 'current_model', 'shift', 'date')
    search_fields = ('operator__username', 'current_model', 'comments')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'current_model', 'shift', 'mechanism_summary_detailed')
    inlines = [ErrorPreventionMechanismStatusInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('date', 'verification_status', 'current_model', 'shift')
        }),
        ('Personnel', {
            'fields': ('operator', 'supervisor', 'quality_supervisor')
        }),
        ('Status', {
            'fields': ('status', 'comments')
        }),
        ('Mechanism Summary', {
            'fields': ('mechanism_summary_detailed',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def shift_display(self, obj):
        shift_choices = dict(obj.SHIFTS)
        return shift_choices.get(obj.shift, obj.shift) if obj.shift else 'N/A'
    shift_display.short_description = 'Shift'
    
    def status_badge(self, obj):
        colors = {'pending': '#ffc107', 'supervisor_approved': '#17a2b8', 'quality_approved': '#28a745', 'rejected': '#dc3545'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def mechanism_summary(self, obj):
        return format_html(
            'OK: <span style="color: green; font-weight: bold;">{}</span> | '
            'NG: <span style="color: red; font-weight: bold;">{}</span> | '
            'N/A: <span style="color: orange; font-weight: bold;">{}</span>',
            obj.ok_count, obj.ng_count, obj.na_count
        )
    mechanism_summary.short_description = 'Mechanisms'
    
    def mechanism_summary_detailed(self, obj):
        html = '<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">'
        html += f'<p><strong>Total:</strong> {obj.total_mechanisms}</p>'
        html += f'<p><strong>OK:</strong> <span style="color: green;">{obj.ok_count}</span></p>'
        html += f'<p><strong>NG:</strong> <span style="color: red;">{obj.ng_count}</span></p>'
        html += f'<p><strong>N/A:</strong> <span style="color: orange;">{obj.na_count}</span></p>'
        html += '</div>'
        return format_html(html)
    mechanism_summary_detailed.short_description = 'Mechanism Summary'
    
    def verification_status_link(self, obj):
        if obj.verification_status:
            try:
                url = reverse('admin:main_dailyverificationstatus_change', args=[obj.verification_status.id])
                return format_html('<a href="{}">{}</a>', url, f"Verification #{obj.verification_status.id}")
            except:
                return f"Verification #{obj.verification_status.id}"
        return 'N/A'
    verification_status_link.short_description = 'Verification'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'operator', 'supervisor', 'quality_supervisor', 'verification_status'
        ).prefetch_related('mechanism_statuses')


@admin.register(ErrorPreventionMechanismStatus)
class ErrorPreventionMechanismStatusAdmin(admin.ModelAdmin):
    """Fully editable mechanism status admin"""
    
    list_display = (
        'ep_check_link', 
        'mechanism_display', 
        'working_indicator',
        'status',  # Make sure this is here for list_editable
        'is_not_applicable',  # Make sure this is here for list_editable
        'alternative_method_short', 
        'last_edit_info'
    )
    
    list_filter = ('status', 'is_working', 'is_not_applicable', 'mechanism__is_currently_working', 'ep_check__date')
    search_fields = ('mechanism__mechanism_id', 'mechanism__description', 'comments')
    list_editable = ('status', 'is_not_applicable')
    
    fieldsets = (
        ('EP Check', {'fields': ('ep_check',)}),
        ('Mechanism', {'fields': ('mechanism', 'ep_mechanism_id')}),
        ('Working Status (From Master)', {
            'fields': ('is_working', 'alternative_method'),
            'description': 'Controlled by master mechanism'
        }),
        ('Operator Input', {'fields': ('status', 'is_not_applicable', 'comments')}),
        ('Edit Tracking', {'fields': ('last_edited_by', 'last_edited_at')})
    )
    
    readonly_fields = ('ep_mechanism_id', 'is_working', 'alternative_method')
    
    def ep_check_link(self, obj):
        if obj.ep_check:
            try:
                url = reverse('admin:main_errorpreventioncheck_change', args=[obj.ep_check.id])
                return format_html('<a href="{}">{} - {}</a>', url, obj.ep_check.date, obj.ep_check.current_model)
            except:
                return f"{obj.ep_check.date} - {obj.ep_check.current_model}"
        return 'N/A'
    ep_check_link.short_description = 'EP Check'
    
    def mechanism_display(self, obj):
        return obj.mechanism.mechanism_id if obj.mechanism else obj.ep_mechanism_id or 'N/A'
    mechanism_display.short_description = 'Mechanism'
    
    def working_indicator(self, obj):
        return format_html('<span style="color: green;">✓</span>' if obj.is_working else '<span style="color: red;">✗</span>')
    working_indicator.short_description = 'Working'
    
    # Remove status_badge since we're using the raw status field for editing
    
    def alternative_method_short(self, obj):
        if not obj.is_working:
            method = obj.alternative_method[:30] + '...' if len(obj.alternative_method) > 30 else obj.alternative_method
            return format_html('<span style="background-color: #fff3cd; padding: 2px 5px; border-radius: 3px;">{}</span>', method)
        return '-'
    alternative_method_short.short_description = 'Alt. Method'
    
    def last_edit_info(self, obj):
        if obj.last_edited_at:
            return format_html('<small>{}<br>by {}</small>', 
                obj.last_edited_at.strftime('%Y-%m-%d %H:%M'),
                obj.last_edited_by.username if obj.last_edited_by else 'Unknown')
        return '-'
    last_edit_info.short_description = 'Last Edit'


# ============ HISTORY ADMINS ============

@admin.register(ErrorPreventionCheckHistory)
class ErrorPreventionCheckHistoryAdmin(admin.ModelAdmin):
    list_display = ('ep_check', 'action', 'changed_by', 'timestamp', 'change_summary')
    list_filter = ('action', 'timestamp')
    search_fields = ('ep_check__id', 'changed_by__username')
    date_hierarchy = 'timestamp'
    readonly_fields = ('ep_check', 'changed_by', 'action', 'field_name', 'old_value', 'new_value', 'timestamp')
    
    def change_summary(self, obj):
        if obj.field_name:
            return format_html('<strong>{}:</strong> {} → {}', obj.field_name, 
                obj.old_value[:20] if obj.old_value else '-', 
                obj.new_value[:20] if obj.new_value else '-')
        return obj.description or '-'
    change_summary.short_description = 'Change'
    
    def has_add_permission(self, request):
        return False


@admin.register(ErrorPreventionMechanismHistory)
class ErrorPreventionMechanismHistoryAdmin(admin.ModelAdmin):
    list_display = ('mechanism_status_link', 'field_name', 'old_value_short', 'new_value_short', 'changed_by', 'timestamp')
    list_filter = ('field_name', 'timestamp')
    search_fields = ('mechanism_status__mechanism__mechanism_id',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('mechanism_status', 'changed_by', 'field_name', 'old_value', 'new_value', 'timestamp')
    
    def mechanism_status_link(self, obj):
        if obj.mechanism_status:
            try:
                url = reverse('admin:main_errorpreventionmechanismstatus_change', args=[obj.mechanism_status.id])
                return format_html('<a href="{}">{}</a>', url, 
                    obj.mechanism_status.mechanism.mechanism_id if obj.mechanism_status.mechanism else 'Unknown')
            except:
                return str(obj.mechanism_status)
        return 'N/A'
    mechanism_status_link.short_description = 'Mechanism'
    
    def old_value_short(self, obj):
        return obj.old_value[:30] + '...' if obj.old_value and len(obj.old_value) > 30 else obj.old_value or '-'
    old_value_short.short_description = 'Old Value'
    
    def new_value_short(self, obj):
        return obj.new_value[:30] + '...' if obj.new_value and len(obj.new_value) > 30 else obj.new_value or '-'
    new_value_short.short_description = 'New Value'
    
    def has_add_permission(self, request):
        return False


# ============ DTPM ADMINS ============

# Add this to the bottom of your admin.py file, replacing the existing DTPM admin code

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import DTPMCheckpoint, DTPMChecklistFMA03New, DTPMCheckResultNew, DTPMIssueNew, DTPMVerificationHistory


@admin.register(DTPMCheckpoint)
class DTPMCheckpointAdmin(admin.ModelAdmin):
    """Admin interface for managing DTPM checkpoints"""
    
    list_display = [
        'checkpoint_number', 
        'title_preview', 
        'image_preview', 
        'is_active', 
        'order',
        'updated_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['checkpoint_number', 'title_english', 'title_hindi']
    ordering = ['order', 'checkpoint_number']
    list_editable = ['is_active', 'order']
    
    fieldsets = (
        ('Checkpoint Information', {
            'fields': ('checkpoint_number', 'order', 'is_active')
        }),
        ('Titles', {
            'fields': ('title_english', 'title_hindi')
        }),
        ('Details', {
            'fields': ('description', 'reference_image')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def title_preview(self, obj):
        """Show truncated title with tooltip"""
        max_length = 60
        title = obj.title_english
        if len(title) > max_length:
            return format_html(
                '<span title="{}">{}</span>',
                title,
                title[:max_length] + '...'
            )
        return title
    title_preview.short_description = 'Title (English)'
    
    def image_preview(self, obj):
        """Show thumbnail of reference image"""
        if obj.reference_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.reference_image.url
            )
        return format_html('<span style="color: #999;">No image</span>')
    image_preview.short_description = 'Image'


class DTPMCheckResultInline(admin.TabularInline):
    """Inline editor for check results"""
    model = DTPMCheckResultNew
    extra = 0
    can_delete = False
    fields = ['checkpoint_display', 'status', 'comments']
    readonly_fields = ['checkpoint_display']
    
    def checkpoint_display(self, obj):
        """Display checkpoint number and title"""
        if obj and obj.checkpoint:
            return f"#{obj.checkpoint.checkpoint_number} - {obj.checkpoint.title_english}"
        elif obj and obj.id:
            return "⚠️ Missing checkpoint reference"
        return "N/A"
    checkpoint_display.short_description = 'Checkpoint'


@admin.register(DTPMChecklistFMA03New)
class DTPMChecklistFMA03NewAdmin(admin.ModelAdmin):
    """Enhanced admin for DTPM checklists"""
    
    list_display = [
        'id', 
        'date', 
        'shift_display', 
        'operator', 
        'current_model', 
        'status_badge', 
        'completion_status',
        'verification_status_link'
    ]
    list_filter = ['status', 'date', 'shift', 'current_model']
    search_fields = ['operator__username', 'current_model', 'notes']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at', 'current_model', 'checklist_shift']
    inlines = [DTPMCheckResultInline]
    actions = ['regenerate_check_results']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('date', 'shift', 'verification_status', 'operator', 'supervisor')
        }),
        ('Auto-Populated Fields', {
            'fields': ('current_model', 'checklist_shift'),
            'classes': ('collapse',)
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Supervisor Verification', {
            'fields': ('supervisor_approved_at', 'supervisor_approved_by', 'rejected_at', 'rejected_by'),
            'classes': ('collapse',)
        }),
        ('Quality Verification', {
            'fields': ('quality_certified_at', 'quality_certified_by', 'quality_comments', 'quality_rejected_at', 'quality_rejected_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def shift_display(self, obj):
        return obj.shift.get_shift_type_display() if obj.shift else 'N/A'
    shift_display.short_description = 'Shift'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107', 
            'supervisor_approved': '#17a2b8',
            'quality_certified': '#28a745', 
            'rejected': '#dc3545',
            'quality_rejected': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'), 
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def completion_status(self, obj):
        """Show completion percentage - FIXED"""
        total_checkpoints = obj.check_results.count()
        if total_checkpoints == 0:
            return format_html('<span style="color: #999;">No checkpoints</span>')
        
        ok_count = obj.check_results.filter(status='OK').count()
        percentage = int((ok_count / total_checkpoints) * 100)
        
        color = '#28a745' if percentage == 100 else '#ffc107' if percentage >= 70 else '#dc3545'
        
        return format_html(
            '<div style="background: #f0f0f0; border-radius: 10px; overflow: hidden; width: 100px;">'
            '<div style="background: {}; color: white; text-align: center; padding: 2px; width: {}%;">{}</div>'
            '</div>',
            color, percentage, str(percentage) + '%'
        )
    completion_status.short_description = 'Completion'
    
    def verification_status_link(self, obj):
        if obj.verification_status:
            try:
                url = reverse('admin:main_dailyverificationstatus_change', args=[obj.verification_status.id])
                return format_html('<a href="{}">{}</a>', url, f"Verification #{obj.verification_status.id}")
            except:
                return f"Verification #{obj.verification_status.id}"
        return format_html('<span style="color: #999;">N/A</span>')
    verification_status_link.short_description = 'Verification'
    
    def regenerate_check_results(self, request, queryset):
        """Regenerate check results for selected checklists"""
        from django.db import transaction
        
        total_added = 0
        for checklist in queryset:
            with transaction.atomic():
                active_checkpoints = DTPMCheckpoint.objects.filter(is_active=True)
                existing_checkpoint_ids = checklist.check_results.values_list('checkpoint_id', flat=True)
                
                for checkpoint in active_checkpoints:
                    if checkpoint.id not in existing_checkpoint_ids:
                        DTPMCheckResultNew.objects.create(
                            checklist=checklist,
                            checkpoint=checkpoint,
                            status='NG'
                        )
                        total_added += 1
        
        self.message_user(request, f'Added {total_added} missing check results')
    regenerate_check_results.short_description = 'Regenerate missing check results'


@admin.register(DTPMCheckResultNew)
class DTPMCheckResultNewAdmin(admin.ModelAdmin):
    """Admin for individual check results - FIXED"""
    
    list_display = [
        'id',
        'checklist_link', 
        'checkpoint_info', 
        'status_badge', 
        'has_comments',
        'updated_at'
    ]
    list_filter = ['status', 'checklist__date']
    search_fields = ['checkpoint__title_english', 'comments', 'checklist__id']
    list_editable = []
    
    fieldsets = (
        ('Check Information', {
            'fields': ('checklist', 'checkpoint', 'status')
        }),
        ('Details', {
            'fields': ('comments',)
        }),
        ('Timestamps', {
            'fields': ('checked_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['checked_at', 'updated_at']
    
    def checklist_link(self, obj):
        if obj.checklist:
            try:
                url = reverse('admin:main_dtpmchecklistfma03new_change', args=[obj.checklist.id])
                return format_html(
                    '<a href="{}">{} - {}</a>', 
                    url, 
                    obj.checklist.date,
                    obj.checklist.shift.get_shift_type_display() if obj.checklist.shift else 'N/A'
                )
            except:
                return f"{obj.checklist.date}"
        return 'N/A'
    checklist_link.short_description = 'Checklist'
    
    def checkpoint_info(self, obj):
        """FIXED - Handle None checkpoint"""
        if obj.checkpoint:
            img_html = ''
            if obj.checkpoint.reference_image:
                img_html = format_html(
                    '<img src="{}" width="30" height="30" style="object-fit: cover; border-radius: 3px; margin-right: 5px; vertical-align: middle;" />',
                    obj.checkpoint.reference_image.url
                )
            title = obj.checkpoint.title_english[:50] + '...' if len(obj.checkpoint.title_english) > 50 else obj.checkpoint.title_english
            return format_html(
                '{}<strong>#{}</strong> {}',
                img_html,
                obj.checkpoint.checkpoint_number,
                title
            )
        return format_html('<span style="color: red;">⚠️ Missing Checkpoint Reference</span>')
    checkpoint_info.short_description = 'Checkpoint'
    
    def status_badge(self, obj):
        colors = {'OK': '#28a745', 'NG': '#dc3545', '': '#6c757d'}
        status_text = obj.status if obj.status else 'Not Set'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'), 
            status_text
        )
    status_badge.short_description = 'Status'
    
    def has_comments(self, obj):
        if obj.comments:
            return format_html('<i class="fas fa-comment" style="color: #17a2b8;" title="{}"></i>', obj.comments[:100])
        return format_html('<span style="color: #999;">—</span>')
    has_comments.short_description = 'Comments'


@admin.register(DTPMIssueNew)
class DTPMIssueNewAdmin(admin.ModelAdmin):
    """Admin for DTPM issues"""
    
    list_display = [
        'id',
        'checklist_info', 
        'checkpoint_info',
        'priority_badge', 
        'status_badge', 
        'reported_by', 
        'assigned_to',
        'created_at'
    ]
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['description', 'reported_by__username', 'action_taken']
    readonly_fields = ['check_result', 'reported_by', 'created_at']
    
    fieldsets = (
        ('Issue Information', {
            'fields': ('check_result', 'description', 'priority')
        }),
        ('Assignment', {
            'fields': ('status', 'reported_by', 'assigned_to')
        }),
        ('Resolution', {
            'fields': ('action_taken', 'resolution_date', 'resolved_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def checklist_info(self, obj):
        if obj.check_result and obj.check_result.checklist:
            checklist = obj.check_result.checklist
            try:
                url = reverse('admin:main_dtpmchecklistfma03new_change', args=[checklist.id])
                return format_html(
                    '<a href="{}">{} - {}</a>', 
                    url, 
                    checklist.date,
                    checklist.shift.get_shift_type_display() if checklist.shift else 'N/A'
                )
            except:
                return f"{checklist.date}"
        return 'N/A'
    checklist_info.short_description = 'Checklist'
    
    def checkpoint_info(self, obj):
        if obj.check_result and obj.check_result.checkpoint:
            cp = obj.check_result.checkpoint
            return f"#{cp.checkpoint_number} - {cp.title_english[:40]}..."
        return 'N/A'
    checkpoint_info.short_description = 'Checkpoint'
    
    def priority_badge(self, obj):
        colors = {'low': '#28a745', 'medium': '#ffc107', 'high': '#fd7e14', 'critical': '#dc3545'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.priority, '#6c757d'), 
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def status_badge(self, obj):
        colors = {'open': '#dc3545', 'in_progress': '#ffc107', 'resolved': '#28a745'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'), 
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(DTPMVerificationHistory)
class DTPMVerificationHistoryAdmin(admin.ModelAdmin):
    """Admin for verification history"""
    
    list_display = [
        'id',
        'checklist_link',
        'verification_type_badge',
        'verified_by',
        'verified_at',
        'has_comments'
    ]
    list_filter = ['verification_type', 'verified_at']
    search_fields = ['verified_by__username', 'comments']
    readonly_fields = ['verified_at']
    date_hierarchy = 'verified_at'
    
    def checklist_link(self, obj):
        if obj.checklist:
            try:
                url = reverse('admin:main_dtpmchecklistfma03new_change', args=[obj.checklist.id])
                shift_display = obj.checklist.shift.get_shift_type_display() if obj.checklist.shift else 'N/A'
                return format_html('<a href="{}">{} - {}</a>', url, obj.checklist.date, shift_display)
            except:
                return f"{obj.checklist.date}"
        return 'N/A'
    checklist_link.short_description = 'Checklist'
    
    def verification_type_badge(self, obj):
        colors = {
            'supervisor_approve': '#17a2b8',
            'supervisor_reject': '#dc3545',
            'quality_certify': '#28a745',
            'quality_reject': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.verification_type, '#6c757d'),
            obj.get_verification_type_display()
        )
    verification_type_badge.short_description = 'Action'
    
    def has_comments(self, obj):
        if obj.comments:
            return format_html('<i class="fas fa-comment" style="color: #17a2b8;" title="{}"></i>', obj.comments[:100])
        return format_html('<span style="color: #999;">—</span>')
    has_comments.short_description = 'Comments'

# ============ CUSTOMIZE ADMIN SITE ============

admin.site.site_header = 'Checklist System Administration'
admin.site.site_title = 'Checklist System Admin'
admin.site.index_title = 'Checklist Management'