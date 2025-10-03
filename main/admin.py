from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    User, Shift, ChecklistBase, SubgroupEntry,SubgroupVerification,SubgroupEditHistory, Verification, Concern, SubgroupFrequencyConfig, ChecksheetContentConfig,
    DailyVerificationStatus, DTPMChecklistFMA03New, DTPMCheckResultNew, 
    DTPMIssueNew, ErrorPreventionCheck, ErrorPreventionMechanismStatus
)


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('company_id', 'skill_matrix_level', 'user_type')}),
    )
    list_display = ['username', 'email', 'company_id', 'user_type', 'is_staff']
    list_filter = ['user_type', 'is_staff', 'is_active']

admin.site.register(User, CustomUserAdmin)


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


# admin.py - Enhanced admin for ChecksheetContentConfig
@admin.register(ChecksheetContentConfig)
class ChecksheetContentConfigAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'parameter_name', 'measurement_type', 'order', 'is_active']
    list_filter = ['model_name', 'measurement_type', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['parameter_name', 'parameter_name_hindi']
    actions = ['duplicate_to_all_models', 'duplicate_to_selected_model']
    
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
    
    def duplicate_to_selected_model(self, request, queryset):
        """Duplicate to a specific model - would show intermediate page"""
        # This would redirect to an intermediate page where user selects target model
        selected = queryset.values_list('id', flat=True)
        return redirect(f'/admin/duplicate-params/?ids={",".join(map(str, selected))}')
    duplicate_to_selected_model.short_description = "Duplicate to specific model"


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
    readonly_fields = ('created_at', 'shift')  # shift is auto-populated
    
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
            'fields': ('oring_condition', 'master_verification_lvdt', 'good_bad_master_verification',
                      'tool_alignment')
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
    list_display = ['checklist', 'subgroup_number', 'timestamp', 'is_after_maintenance', 'has_nok_entries', 'requires_nok_approval']
    list_filter = ['is_after_maintenance', 'has_nok_entries', 'nok_supervisor_approved', 'nok_quality_approved']
    search_fields = ('checklist__id',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    
    def get_first_measurement(self, obj):
        # Get the first measurement field that exists on your SubgroupEntry model
        # Replace this with the actual field name from your model
        return getattr(obj, 'uv_vacuum_test', 'N/A') if hasattr(obj, 'uv_vacuum_test') else 'N/A'
    get_first_measurement.short_description = 'UV Vacuum Test'
    
    def get_second_measurement(self, obj):
        # Get the second measurement field that exists on your SubgroupEntry model
        # Replace this with the actual field name from your model
        return getattr(obj, 'uv_flow_value', 'N/A') if hasattr(obj, 'uv_flow_value') else 'N/A'
    get_second_measurement.short_description = 'UV Flow Value'


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


# Error Prevention Check Admin
class ErrorPreventionMechanismStatusInline(admin.TabularInline):
    model = ErrorPreventionMechanismStatus
    extra = 0
    readonly_fields = ('ep_mechanism_id',)
    fields = ('ep_mechanism_id', 'is_working', 'status', 'is_not_applicable', 'alternative_method', 'comments')


@admin.register(ErrorPreventionCheck)
class ErrorPreventionCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'current_model', 'shift_display', 'operator', 'status', 'verification_status_link')
    list_filter = ('status', 'current_model', 'shift', 'date')
    search_fields = ('operator__username', 'current_model')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'current_model', 'shift')  # Auto-populated fields
    inlines = [ErrorPreventionMechanismStatusInline]
    
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
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('operator', 'supervisor', 'quality_supervisor', 'verification_status')


@admin.register(ErrorPreventionMechanismStatus)
class ErrorPreventionMechanismStatusAdmin(admin.ModelAdmin):
    list_display = ('ep_check_link', 'ep_mechanism_id', 'status', 'is_working', 'is_not_applicable')
    list_filter = ('status', 'is_working', 'is_not_applicable', 'ep_check__date')
    search_fields = ('ep_mechanism_id', 'comments')
    
    def ep_check_link(self, obj):
        if obj.ep_check:
            try:
                url = reverse('admin:main_errorpreventioncheck_change', args=[obj.ep_check.id])
                return format_html('<a href="{}">{} - {}</a>', url, obj.ep_check.date, obj.ep_check.current_model)
            except:
                return f"{obj.ep_check.date} - {obj.ep_check.current_model}"
        return 'N/A'
    ep_check_link.short_description = 'EP Check'


# DTPM Admin Classes
class DTPMCheckResultInline(admin.TabularInline):
    model = DTPMCheckResultNew
    extra = 0
    readonly_fields = ['checkpoint_number', 'get_checkpoint_description', 'checked_at', 'updated_at']
    fields = ['checkpoint_number', 'get_checkpoint_description', 'status', 'comments']
    
    def get_checkpoint_description(self, obj):
        checkpoint_dict = dict(DTPMChecklistFMA03New.CHECKPOINT_CHOICES)
        return checkpoint_dict.get(obj.checkpoint_number, 'Unknown')
    get_checkpoint_description.short_description = 'Description'
    
    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deletion of checkpoint results



 
# Remove DTPMIssueInline since DTPMIssueNew doesn't have direct ForeignKey to DTPMChecklistFMA03New
# Issues are linked through DTPMCheckResultNew


@admin.register(DTPMChecklistFMA03New)
class DTPMChecklistFMA03NewAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'shift_display', 'operator_display', 'current_model_display', 'status_badge', 'issue_count', 'verification_status_link']
    list_filter = ['status', 'date', 'shift', 'operator', 'current_model']
    search_fields = ['operator__username', 'notes', 'current_model']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at', 'current_model', 'checklist_shift']  # Auto-populated fields
    inlines = [DTPMCheckResultInline]  # Removed DTPMIssueInline
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('shift', 'operator', 'supervisor', 'verification_status').annotate(
            issue_count=Count('check_results__issues', distinct=True)
        )
    
    def shift_display(self, obj):
        return obj.shift.get_shift_type_display() if obj.shift else 'N/A'
    shift_display.short_description = 'Shift'
    
    def operator_display(self, obj):
        return obj.operator.username if obj.operator else 'N/A'
    operator_display.short_description = 'Operator'
    
    def current_model_display(self, obj):
        return obj.current_model if obj.current_model else 'N/A'
    current_model_display.short_description = 'Model'
    
    def verification_status_link(self, obj):
        if obj.verification_status:
            try:
                url = reverse('admin:main_dailyverificationstatus_change', args=[obj.verification_status.id])
                return format_html('<a href="{}">{}</a>', url, f"Verification #{obj.verification_status.id}")
            except:
                return f"Verification #{obj.verification_status.id}"
        return 'N/A'
    verification_status_link.short_description = 'Verification'
    
    def status_badge(self, obj):
        status_colors = {
            'pending': '#ffc107',   # Warning yellow
            'verified': '#28a745',  # Success green
            'rejected': '#dc3545',  # Danger red
        }
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
            status_colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def issue_count(self, obj):
        count = getattr(obj, 'issue_count', 0)
        if count > 0:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 10px;">{}</span>',
                count
            )
        return '0'
    issue_count.short_description = 'Issues'


class DTPMIssueInline(admin.TabularInline):
    model = DTPMIssueNew
    extra = 0
    readonly_fields = ['reported_by', 'created_at']
    fields = ['reported_by', 'created_at', 'status', 'priority', 'description', 'action_taken']
    
    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deletion of issues


@admin.register(DTPMCheckResultNew)
class DTPMCheckResultNewAdmin(admin.ModelAdmin):
    list_display = ['id', 'checklist_link', 'checkpoint_number', 'get_checkpoint_description', 'status_badge', 'has_issues', 'updated_at']
    list_filter = ['status', 'checklist__date', 'checklist__status']
    search_fields = ['comments', 'checklist__operator__username']
    readonly_fields = ['checklist', 'checkpoint_number', 'checked_at', 'updated_at']
    inlines = [DTPMIssueInline]  # Issues are linked to CheckResult, not directly to Checklist
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('checklist', 'checklist__operator').annotate(
            has_issues_count=Count('issues', distinct=True)
        )
    
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
                return f"{obj.checklist.date} - {obj.checklist.shift.get_shift_type_display() if obj.checklist.shift else 'N/A'}"
        return 'N/A'
    checklist_link.short_description = 'Checklist'
    
    def get_checkpoint_description(self, obj):
        checkpoint_dict = dict(DTPMChecklistFMA03New.CHECKPOINT_CHOICES)
        return checkpoint_dict.get(obj.checkpoint_number, 'Unknown')
    get_checkpoint_description.short_description = 'Description'
    
    def status_badge(self, obj):
        status_colors = {
            'OK': '#28a745',  # Success green
            'NG': '#dc3545',  # Danger red
            '': '#6c757d',    # Secondary gray
        }
        
        if not obj.status:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 10px;">Not Set</span>'
            )
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
            status_colors.get(obj.status, '#6c757d'),
            obj.status
        )
    status_badge.short_description = 'Status'
    
    def has_issues(self, obj):
        count = getattr(obj, 'has_issues_count', 0)
        if count > 0:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 10px;">{}</span>',
                count
            )
        return format_html(
            '<span style="color: #28a745;">✓</span>'
        )
    has_issues.short_description = 'Issues'


@admin.register(DTPMIssueNew)
class DTPMIssueNewAdmin(admin.ModelAdmin):
    list_display = ['id', 'checklist_info', 'checkpoint_info', 'priority_badge', 'status_badge', 'reported_by_display', 'created_at']
    list_filter = ['status', 'priority', 'reported_by', 'check_result__checklist__date']
    search_fields = ['description', 'action_taken', 'reported_by__username', 'resolved_by__username']
    readonly_fields = ['check_result', 'reported_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Issue Information', {
            'fields': ('check_result', 'reported_by', 'created_at', 'description', 'priority')
        }),
        ('Resolution', {
            'fields': ('status', 'action_taken', 'assigned_to', 'resolved_by', 'resolution_date')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'check_result', 
            'check_result__checklist',
            'reported_by',
            'resolved_by',
            'assigned_to'
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
                return f"{checklist.date} - {checklist.shift.get_shift_type_display() if checklist.shift else 'N/A'}"
        return 'N/A'
    checklist_info.short_description = 'Checklist'
    
    def checkpoint_info(self, obj):
        if obj.check_result:
            checkpoint_dict = dict(DTPMChecklistFMA03New.CHECKPOINT_CHOICES)
            return format_html(
                'CP#{}: {}',
                obj.check_result.checkpoint_number,
                checkpoint_dict.get(obj.check_result.checkpoint_number, 'Unknown')
            )
        return 'N/A'
    checkpoint_info.short_description = 'Checkpoint'
    
    def reported_by_display(self, obj):
        return obj.reported_by.username if obj.reported_by else 'N/A'
    reported_by_display.short_description = 'Reported By'
    
    def priority_badge(self, obj):
        priority_colors = {
            'low': '#28a745',      # Success green
            'medium': '#ffc107',   # Warning yellow
            'high': '#fd7e14',     # Orange
            'critical': '#dc3545', # Danger red
        }
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
            priority_colors.get(obj.priority, '#6c757d'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def status_badge(self, obj):
        status_colors = {
            'open': '#dc3545',         # Danger red
            'in_progress': '#ffc107',  # Warning yellow
            'resolved': '#28a745',     # Success green
        }
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
            status_colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# Customize admin site
admin.site.site_header = 'Checklist System Administration'
admin.site.site_title = 'Checklist System Admin'
admin.site.index_title = 'Checklist Management'