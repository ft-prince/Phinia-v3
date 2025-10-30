from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone

from .models import (
    ParameterGroupEntry,ParameterGroupConfig, User, Shift, ChecklistBase,  
     Verification, Concern, 
    ChecksheetContentConfig, DailyVerificationStatus, 
    ErrorPreventionCheck, ErrorPreventionMechanism, 
    ErrorPreventionMechanismStatus, ErrorPreventionCheckHistory,
    ErrorPreventionMechanismHistory,
    # FTQ-related models
    FTQRecord, OperationNumber, DefectCategory, DefectType,
    TimeBasedDefectEntry, DefectRecord, CustomDefectType,
)


# ============ USER ADMIN ============

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('company_id', 'skill_matrix_level', 'user_type')}),
    )
    list_display = ['username', 'email', 'company_id', 'user_type', 'is_staff']
    list_filter = ['user_type', 'is_staff', 'is_active']

admin.site.register(User, CustomUserAdmin)






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
    list_display = ('id', 'date', 'shift_display', 'status_badge', 'created_by', 'notification_status', 'created_at')
    list_filter = ('status', 'date', 'shift__shift_type')
    search_fields = ('created_by__username',)
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['mark_completed']
    
    def shift_display(self, obj):
        return obj.shift.get_shift_type_display() if obj.shift else 'N/A'
    shift_display.short_description = 'Shift'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'in_progress': '#007bff',
            'completed': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def notification_status(self, obj):
        statuses = []
        if hasattr(obj, 'operator_notified') and obj.operator_notified:
            statuses.append('👷 Op')
        if hasattr(obj, 'supervisor_notified') and obj.supervisor_notified:
            statuses.append('👨‍💼 Sup')
        if hasattr(obj, 'quality_notified') and obj.quality_notified:
            statuses.append('🔍 QC')
        
        if statuses:
            return format_html('<small>{}</small>', ' '.join(statuses))
        return format_html('<span style="color: #6c757d;">None</span>')
    notification_status.short_description = 'Notifications'
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'✅ Marked {updated} verifications as completed')
    mark_completed.short_description = "✅ Mark as completed"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('shift', 'created_by')


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('date', 'shift_type', 'operator', 'shift_supervisor', 'quality_supervisor', 'verification_count')
    list_filter = ('date', 'shift_type')
    search_fields = ('operator__username', 'shift_supervisor__username', 'quality_supervisor__username')
    date_hierarchy = 'date'
    
    def verification_count(self, obj):
        count = obj.verification_statuses.count()
        if count > 0:
            return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', count)
        return format_html('<span style="color: #6c757d;">0</span>')
    verification_count.short_description = 'Verifications'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('operator', 'shift_supervisor', 'quality_supervisor')


# ============ CHECKLIST ADMINS ============


class VerificationInline(admin.TabularInline):
    model = Verification
    extra = 0
    readonly_fields = ('verified_at',)


class ConcernInline(admin.TabularInline):
    model = Concern
    extra = 0
    readonly_fields = ('created_at',)

# ============ CHECKLIST ADMINS ============

# ============ PARAMETER GROUP CONFIGURATION ADMIN ============

@admin.register(ParameterGroupConfig)
class ParameterGroupConfigAdmin(admin.ModelAdmin):
    """Configuration for parameter group timing"""
    list_display = [
        'model_name',
        'parameter_group_display',
        'frequency_minutes',
        'frequency_display',
        'display_order',
        'is_active',
        'created_at'
    ]
    list_filter = ['model_name', 'parameter_group', 'is_active']
    list_editable = ['frequency_minutes', 'display_order', 'is_active']
    search_fields = ['model_name', 'parameter_group']
    ordering = ['model_name', 'display_order', 'frequency_minutes']
    
    actions = ['duplicate_to_all_models', 'set_default_timings', 'activate_selected', 'deactivate_selected']
    
    fieldsets = (
        ('Model & Parameter Group', {
            'fields': ('model_name', 'parameter_group'),
            'description': '⏰ Configure when each parameter group becomes available for operators'
        }),
        ('Timing Configuration', {
            'fields': ('frequency_minutes', 'display_order'),
            'description': 'Set minutes after checklist creation when this parameter group appears'
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )
    
    def parameter_group_display(self, obj):
        """Display parameter group with icon"""
        icons = {
            'uv_vacuum': '🔧',
            'uv_flow': '💧',
            'umbrella_valve': '☂️',
            'uv_clip': '📎',
            'workstation': '🧹',
            'bin_contamination': '🗑️',
        }
        icon = icons.get(obj.parameter_group, '📋')
        return format_html('{} {}', icon, obj.get_parameter_group_display())
    parameter_group_display.short_description = 'Parameter Group'
    
    def frequency_display(self, obj):
        """Display frequency in readable format"""
        if obj.frequency_minutes == 0:
            return format_html('<span style="color: #28a745; font-weight: bold;">Immediate</span>')
        elif obj.frequency_minutes < 60:
            return format_html('<span style="color: #dc3545; font-weight: bold;">After {} min</span>', obj.frequency_minutes)
        else:
            hours = round(obj.frequency_minutes / 60, 1)
            return format_html('<span style="color: #007bff; font-weight: bold;">After {} hours</span>', hours)
    frequency_display.short_description = 'Availability'
    
    def duplicate_to_all_models(self, request, queryset):
        """Duplicate selected configurations to all models"""
        count = 0
        for obj in queryset:
            for model_choice in [('P703', 'P703'), ('U704', 'U704'), ('FD', 'FD'), ('SA', 'SA'), ('Gnome', 'Gnome')]:
                model_name = model_choice[0]
                if model_name != obj.model_name:
                    config, created = ParameterGroupConfig.objects.get_or_create(
                        model_name=model_name,
                        parameter_group=obj.parameter_group,
                        defaults={
                            'frequency_minutes': obj.frequency_minutes,
                            'display_order': obj.display_order,
                            'is_active': obj.is_active,
                        }
                    )
                    if created:
                        count += 1
                    else:
                        config.frequency_minutes = obj.frequency_minutes
                        config.display_order = obj.display_order
                        config.is_active = obj.is_active
                        config.save()
                        count += 1
        
        self.message_user(request, f'Successfully duplicated {queryset.count()} configurations to {count} models')
    duplicate_to_all_models.short_description = "🔄 Duplicate to all models"
    
    def set_default_timings(self, request, queryset):
        """Set default timing configurations"""
        default_timings = {
            'uv_vacuum': 0,      # Immediate
            'uv_flow': 30,       # After 30 minutes
            'umbrella_valve': 60,  # After 1 hour
            'uv_clip': 90,       # After 1.5 hours
            'workstation': 120,  # After 2 hours
            'bin_contamination': 150,  # After 2.5 hours
        }
        
        updated_count = 0
        for obj in queryset:
            if obj.parameter_group in default_timings:
                obj.frequency_minutes = default_timings[obj.parameter_group]
                obj.save()
                updated_count += 1
        
        self.message_user(request, f'Updated {updated_count} configurations with recommended default timings')
    set_default_timings.short_description = "⚙️ Set recommended default timings"
    
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'✅ Activated {queryset.count()} configurations')
    activate_selected.short_description = "✅ Activate selected"
    
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'❌ Deactivated {queryset.count()} configurations')
    deactivate_selected.short_description = "❌ Deactivate selected"


# ============ CHECKLIST ADMINS ============

class ParameterGroupEntryInline(admin.TabularInline):
    """Parameter group entries inline"""
    model = ParameterGroupEntry
    extra = 0
    readonly_fields = ('timestamp', 'is_completed', 'verification_summary')
    fields = (
        'parameter_group', 'timestamp', 'is_completed', 
        'is_after_maintenance', 'verification_summary'
    )
    verbose_name = "Parameter Group Entry"
    verbose_name_plural = "Parameter Group Entries"
    
    def verification_summary(self, obj):
        """Show verification status inline"""
        if not obj.pk:
            return "Save first"
        
        badges = []
        
        # Supervisor verification
        supervisor_verif = obj.verifications.filter(verification_type='supervisor').first()
        if supervisor_verif:
            if supervisor_verif.status == 'approved':
                badges.append('✅ Supervisor')
            else:
                badges.append('❌ Supervisor')
        else:
            badges.append('⏳ Supervisor')
        
        # Quality verification
        quality_verif = obj.verifications.filter(verification_type='quality').first()
        if quality_verif:
            if quality_verif.status == 'approved':
                badges.append('✅ Quality')
            else:
                badges.append('❌ Quality')
        else:
            badges.append('⏳ Quality')
        
        return format_html(' | '.join(badges))
    
    verification_summary.short_description = 'Verification Status'


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
    list_display = (
        'id', 'status_badge', 'selected_model', 'shift_display', 
        'verification_status_link', 'parameter_entries_summary', 
        'completion_progress', 'created_at'
    )
    list_filter = ('status', 'selected_model', 'shift')
    search_fields = ('id', 'selected_model')
    date_hierarchy = 'created_at'
    inlines = [
        ParameterGroupEntryInline,
        VerificationInline, 
        ConcernInline
    ]
    readonly_fields = ('created_at', 'shift', 'parameter_stats')
    
    actions = ['reset_to_pending']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'supervisor_approved': '#ffc107',
            'quality_approved': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def shift_display(self, obj):
        shift_choices = dict(ChecklistBase.SHIFTS)
        return shift_choices.get(obj.shift, obj.shift) if obj.shift else 'N/A'
    shift_display.short_description = 'Shift'
    
    def verification_status_link(self, obj):
        if obj.verification_status:
            try:
                url = reverse('admin:main_dailyverificationstatus_change', args=[obj.verification_status.id])
                return format_html('<a href="{}">📋 Verification #{}</a>', url, obj.verification_status.id)
            except:
                return f"Verification #{obj.verification_status.id}"
        return format_html('<span style="color: #6c757d;">No verification</span>')
    verification_status_link.short_description = 'Verification Status'
    
    def parameter_entries_summary(self, obj):
        """Summary of parameter group entries"""
        try:
            total = obj.parameter_entries.count()
            completed = obj.parameter_entries.filter(is_completed=True).count()
            
            # Count by verification status
            supervisor_approved = 0
            quality_approved = 0
            
            for entry in obj.parameter_entries.all():
                if entry.verifications.filter(verification_type='supervisor', status='approved').exists():
                    supervisor_approved += 1
                if entry.verifications.filter(verification_type='quality', status='approved').exists():
                    quality_approved += 1
            
            if total == 0:
                return format_html('<span style="color: #6c757d;">No entries</span>')
            
            return format_html(
                '<div style="font-size: 11px;">'
                '<strong>Total:</strong> {} | '
                '<strong>Complete:</strong> {} | '
                '<span style="color: #ffc107;">👨‍💼 {}</span> | '
                '<span style="color: #28a745;">🔍 {}</span>'
                '</div>',
                total, completed, supervisor_approved, quality_approved
            )
        except:
            return format_html('<span style="color: #6c757d;">0</span>')
    parameter_entries_summary.short_description = 'Parameter Entries'
    
    def completion_progress(self, obj):
        """Visual progress bar for parameter completion"""
        try:
            total = obj.parameter_entries.count()
            if total == 0:
                return format_html('<span style="color: #999;">No data</span>')
            
            completed = obj.parameter_entries.filter(is_completed=True).count()
            percentage = int((completed / total) * 100)
            
            color = '#28a745' if percentage == 100 else '#ffc107' if percentage >= 50 else '#dc3545'
            
            return format_html(
                '<div style="background: #f0f0f0; border-radius: 10px; overflow: hidden; width: 100px; height: 20px;">'
                '<div style="background: {}; color: white; text-align: center; font-size: 11px; line-height: 20px; width: {}%;">'
                '{}%'
                '</div>'
                '</div>',
                color, percentage, percentage
            )
        except:
            return format_html('<span style="color: #999;">N/A</span>')
    completion_progress.short_description = 'Progress'
    
    def parameter_stats(self, obj):
        """Detailed parameter statistics"""
        if not obj.pk:
            return "Save checklist first"
        
        try:
            entries = obj.parameter_entries.all()
            
            # FIXED: Get choices from the model field directly
            parameter_choices = dict(ParameterGroupEntry._meta.get_field('parameter_group').choices)
            
            # Group by parameter type
            by_group = {}
            for entry in entries:
                group = entry.parameter_group
                if group not in by_group:
                    by_group[group] = {
                        'total': 0,
                        'completed': 0,
                        'supervisor_approved': 0,
                        'quality_approved': 0
                    }
                
                by_group[group]['total'] += 1
                if entry.is_completed:
                    by_group[group]['completed'] += 1
                
                if entry.verifications.filter(verification_type='supervisor', status='approved').exists():
                    by_group[group]['supervisor_approved'] += 1
                
                if entry.verifications.filter(verification_type='quality', status='approved').exists():
                    by_group[group]['quality_approved'] += 1
            
            html = '<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">'
            html += '<h3 style="margin-top: 0;">📊 Parameter Group Statistics</h3>'
            
            if not by_group:
                html += '<p style="color: #6c757d;">No parameter entries yet</p>'
            else:
                html += '<table style="width: 100%; border-collapse: collapse;">'
                html += '<thead><tr style="background-color: #e9ecef;">'
                html += '<th style="padding: 8px; text-align: left;">Parameter Group</th>'
                html += '<th style="padding: 8px; text-align: center;">Total</th>'
                html += '<th style="padding: 8px; text-align: center;">Completed</th>'
                html += '<th style="padding: 8px; text-align: center;">👨‍💼 Supervisor</th>'
                html += '<th style="padding: 8px; text-align: center;">🔍 Quality</th>'
                html += '</tr></thead><tbody>'
                
                for group, stats in by_group.items():
                    # FIXED: Use the choices dict we created above
                    group_name = parameter_choices.get(group, group)
                    html += '<tr style="border-bottom: 1px solid #dee2e6;">'
                    html += f'<td style="padding: 8px;"><strong>{group_name}</strong></td>'
                    html += f'<td style="padding: 8px; text-align: center;">{stats["total"]}</td>'
                    html += f'<td style="padding: 8px; text-align: center;">{stats["completed"]}</td>'
                    html += f'<td style="padding: 8px; text-align: center;">{stats["supervisor_approved"]}</td>'
                    html += f'<td style="padding: 8px; text-align: center;">{stats["quality_approved"]}</td>'
                    html += '</tr>'
                
                html += '</tbody></table>'
            
            html += '</div>'
            
            return format_html(html)
        except Exception as e:
            return format_html(f'<span style="color: #dc3545;">Error: {str(e)}</span>')
    
    parameter_stats.short_description = 'Detailed Statistics'
    
    def reset_to_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'🔄 Reset {updated} checklists to pending status')
    reset_to_pending.short_description = "🔄 Reset to pending"
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('verification_status', 'status', 'selected_model', 'new_shift', 'shift'),
            'description': '📋 Quality Checklist with Parameter Groups'
        }),
        ('One-time Measurements', {
            'fields': ('line_pressure', 'uv_flow_input_pressure', 'test_pressure_vacuum')
        }),
        ('Status Checks', {
            'fields': ('oring_condition',)
        }),
        ('Parameter Statistics', {
            'fields': ('parameter_stats',),
            'classes': ('collapse',)
        }),
        ('Tool Information', {
            'fields': ('top_tool_id', 'top_tool_id_status', 'bottom_tool_id', 'bottom_tool_id_status',
                      'uv_assy_stage_id', 'uv_assy_stage_id_status', 'retainer_part_no', 'retainer_part_no_status',
                      'uv_clip_part_no', 'uv_clip_part_no_status', 'umbrella_part_no', 'umbrella_part_no_status',
                      'retainer_id_lubrication'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('verification_status').prefetch_related('parameter_entries')


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


# ============ CUSTOMIZE ADMIN SITE ============

admin.site.site_header = '🔧 Quality Control System Administration'
admin.site.site_title = 'Quality Control System'
admin.site.index_title = '📋 Quality Management Dashboard - Legacy & NEW Category Timing System'

# Change the default empty text
admin.site.empty_value_display = '—'

# Update verbose names for better organization in admin
ChecklistBase._meta.verbose_name = 'DPVIS - Quality Checklist'
ChecklistBase._meta.verbose_name_plural = 'DPVIS - Quality Checklists'


DailyVerificationStatus._meta.verbose_name = 'DPVIS - Daily Verification Status'
DailyVerificationStatus._meta.verbose_name_plural = 'DPVIS - Daily Verification Statuses'

Verification._meta.verbose_name = 'DPVIS - Final Verification'
Verification._meta.verbose_name_plural = 'DPVIS - Final Verifications'

Concern._meta.verbose_name = 'DPVIS - Quality Concern'
Concern._meta.verbose_name_plural = 'DPVIS - Quality Concerns'

Shift._meta.verbose_name = 'DPVIS - Work Shift'
Shift._meta.verbose_name_plural = 'DPVIS - Work Shifts'

ChecksheetContentConfig._meta.verbose_name = 'DPVIS Checksheet - Content Configuration'
ChecksheetContentConfig._meta.verbose_name_plural = ' DPVIS Checksheet - Content Configurations'

# Update FTQ model verbose names
try:
    FTQRecord._meta.verbose_name = 'FTQ - Quality Record'
    FTQRecord._meta.verbose_name_plural = 'FTQ - Quality Records'
    
    OperationNumber._meta.verbose_name = 'FTQ - Operation Number'
    OperationNumber._meta.verbose_name_plural = 'FTQ - Operation Numbers'
    
    DefectCategory._meta.verbose_name = 'FTQ - Defect Category'
    DefectCategory._meta.verbose_name_plural = 'FTQ - Defect Categories'
    
    DefectType._meta.verbose_name = 'FTQ - Defect Type'
    DefectType._meta.verbose_name_plural = 'FTQ - Defect Types'
    
    TimeBasedDefectEntry._meta.verbose_name = 'FTQ - Time-based Defect Entry'
    TimeBasedDefectEntry._meta.verbose_name_plural = 'FTQ - Time-based Defect Entries'
    
    DefectRecord._meta.verbose_name = 'FTQ - Defect Record'
    DefectRecord._meta.verbose_name_plural = 'FTQ - Defect Records'
    
    CustomDefectType._meta.verbose_name = 'FTQ - Custom Defect Type'
    CustomDefectType._meta.verbose_name_plural = 'FTQ - Custom Defect Types'
except:
    pass  # FTQ models might not be available

# Update Error Prevention model verbose names
try:
    ErrorPreventionCheck._meta.verbose_name = 'EPVS - Error Prevention Check'
    ErrorPreventionCheck._meta.verbose_name_plural = 'EPVS - Error Prevention Checks'
    
    ErrorPreventionMechanism._meta.verbose_name = 'EPVS - Error Prevention Mechanism'
    ErrorPreventionMechanism._meta.verbose_name_plural = 'EPVS - Error Prevention Mechanisms'
    
    ErrorPreventionMechanismStatus._meta.verbose_name = 'EPVS - Mechanism Status'
    ErrorPreventionMechanismStatus._meta.verbose_name_plural = 'EPVS - Mechanism Statuses'
    
    ErrorPreventionCheckHistory._meta.verbose_name = 'EPVS - Check History'
    ErrorPreventionCheckHistory._meta.verbose_name_plural = 'EPVS - Check Histories'
    
    ErrorPreventionMechanismHistory._meta.verbose_name = 'EPVS - Mechanism History'
    ErrorPreventionMechanismHistory._meta.verbose_name_plural = 'EPVS - Mechanism Histories'
except:
    pass  # EPVS models might not be available


ParameterGroupConfig._meta.verbose_name = 'DPVIS SUB Group Configuration'
ParameterGroupConfig._meta.verbose_name_plural = 'DPVIS SUB Group Configurations'



# ============ ERROR PREVENTION - MASTER MECHANISM ADMIN ============

@admin.register(ErrorPreventionMechanism)
class ErrorPreventionMechanismAdmin(admin.ModelAdmin):
    """Admin interface for managing EP mechanisms - FULL ADMIN CONTROL"""
    
    list_display = (
        'mechanism_id', 
        'description_short', 
        'applicable_models', 
        'verification_method_short',  # Changed to show shortened version
        'is_currently_working',
        'default_alternative_method',
        'display_order',
        'is_active',
        'usage_count'
    )
    
    list_filter = ('is_currently_working', 'is_active', 'applicable_models')
    search_fields = ('mechanism_id', 'description', 'applicable_models', 'verification_method')
    ordering = ('display_order', 'mechanism_id')
    list_editable = ('is_currently_working', 'display_order', 'is_active')
    
    fieldsets = (
        ('Mechanism Identification', {
            'fields': ('mechanism_id', 'description', 'applicable_models')
        }),
        ('Verification Method', {  # NEW SECTION - Add this
            'fields': ('verification_method', 'verification_method_hindi'),
            'description': 'Define how this mechanism should be verified (English and Hindi)'
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
    
    def verification_method_short(self, obj):  # NEW METHOD
        """Display shortened verification method"""
        method = obj.verification_method[:40] + '...' if len(obj.verification_method) > 40 else obj.verification_method
        return format_html('<span title="{}">{}</span>', obj.verification_method, method)
    verification_method_short.short_description = 'Verification Method'
    
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


# ============ FTQ ADMIN SECTION ============

class TimeBasedDefectEntryInline(admin.TabularInline):
    """Inline editor for time-based defect entries"""
    model = TimeBasedDefectEntry
    extra = 1
    fields = ['defect_type', 'defect_type_custom', 'recorded_at', 'count', 'notes']
    readonly_fields = []
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "defect_type":
            # Only show active defect types
            kwargs["queryset"] = DefectType.objects.filter(
                category__is_active=True
            ).select_related('operation_number', 'category')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CustomDefectTypeInline(admin.TabularInline):
    """Inline editor for custom defect types"""
    model = CustomDefectType
    extra = 0
    fields = ['name', 'operation_number', 'added_by']
    readonly_fields = ['added_by', 'created_at']
    can_delete = False


@admin.register(FTQRecord)
class FTQRecordAdmin(admin.ModelAdmin):
    """Admin interface for FTQ Records"""
    
    list_display = [
        'id',
        'date',
        'shift_display',
        'model_name',
        'operator_name',
        'total_inspected',
        'total_defects_display',
        'ftq_percentage_display',
        'verification_badge',
        'verification_status_link'
    ]
    
    list_filter = [
        'date',
        'shift_type',
        'model_name',
        'created_by',
        'verified_by'
    ]
    
    search_fields = [
        'created_by__username',
        'verified_by__username',
        'model_name'
    ]
    
    date_hierarchy = 'date'
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'total_defects_display',
        'ftq_percentage_display',
        'defect_summary'
    ]
    
    inlines = [TimeBasedDefectEntryInline, CustomDefectTypeInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('date', 'shift_type', 'model_name', 'julian_date', 'verification_status')
        }),
        ('Production Data', {
            'fields': ('total_inspected', 'production_per_shift')
        }),
        ('Quality Metrics', {
            'fields': ('total_defects_display', 'ftq_percentage_display', 'defect_summary'),
            'classes': ('collapse',)
        }),
        ('Personnel', {
            'fields': ('created_by', 'verified_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_verified', 'export_to_excel']
    
    def shift_display(self, obj):
        """Display shift with full name"""
        shift_dict = dict(FTQRecord.SHIFTS)
        return shift_dict.get(obj.shift_type, obj.shift_type) if obj.shift_type else 'N/A'
    shift_display.short_description = 'Shift'
    
    def operator_name(self, obj):
        """Display operator username"""
        return obj.created_by.username if obj.created_by else 'N/A'
    operator_name.short_description = 'Operator'
    
    def total_defects_display(self, obj):
        """Display total defects with color coding"""
        total = obj.total_defects
        color = '#28a745' if total == 0 else '#ffc107' if total < 5 else '#dc3545'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, total
        )
    total_defects_display.short_description = 'Total Defects'
    
    def ftq_percentage_display(self, obj):
        """Display FTQ percentage with color coding and progress bar"""
        percentage = obj.ftq_percentage
        
        if percentage >= 98:
            color = '#28a745'  # Green
        elif percentage >= 95:
            color = '#ffc107'  # Yellow
        else:
            color = '#dc3545'  # Red
        
        # Format the percentage BEFORE passing to format_html
        percentage_formatted = f"{percentage:.2f}"
        
        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="background: #f0f0f0; border-radius: 10px; overflow: hidden; width: 100px; height: 20px;">'
            '<div style="background: {}; width: {}%; height: 100%;"></div>'
            '</div>'
            '<span style="font-weight: bold; color: {};">{} %</span>'
            '</div>',
            color, percentage, color, percentage_formatted
        )
    ftq_percentage_display.short_description = 'FTQ %'

    
    def verification_badge(self, obj):
        """Display verification status badge"""
        if obj.verified_by:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">'
                '<i class="fas fa-check"></i> Verified by {}'
                '</span>',
                obj.verified_by.username
            )
        return format_html(
            '<span style="background-color: #ffc107; color: white; padding: 3px 10px; border-radius: 3px;">'
            '<i class="fas fa-clock"></i> Pending'
            '</span>'
        )
    verification_badge.short_description = 'Verification'
    
    def verification_status_link(self, obj):
        """Link to verification status"""
        if obj.verification_status:
            try:
                url = reverse('admin:main_dailyverificationstatus_change', args=[obj.verification_status.id])
                return format_html('<a href="{}">{}</a>', url, f"Verification #{obj.verification_status.id}")
            except:
                return f"Verification #{obj.verification_status.id}"
        return format_html('<span style="color: #999;">N/A</span>')
    verification_status_link.short_description = 'Verification Status'
    
    def defect_summary(self, obj):
        """Display detailed defect summary"""
        time_based = obj.time_based_defects.all()
        
        if not time_based.exists():
            return format_html('<p style="color: #999;">No defects recorded</p>')
        
        html = '<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">'
        html += '<h4 style="margin-top: 0;">Defect Breakdown by Time</h4>'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e9ecef;"><th style="padding: 5px; text-align: left;">Time</th><th style="padding: 5px; text-align: left;">Defect Type</th><th style="padding: 5px; text-align: right;">Count</th></tr>'
        
        for entry in time_based:
            defect_name = entry.defect_type.name if entry.defect_type else entry.defect_type_custom.name if entry.defect_type_custom else 'Unknown'
            html += f'<tr><td style="padding: 5px;">{entry.recorded_at.strftime("%H:%M")}</td><td style="padding: 5px;">{defect_name}</td><td style="padding: 5px; text-align: right; font-weight: bold;">{entry.count}</td></tr>'
        
        html += '</table>'
        html += f'<p style="margin-top: 10px; font-weight: bold;">Total Defects: {obj.total_defects}</p>'
        html += '</div>'
        
        return format_html(html)
    defect_summary.short_description = 'Defect Summary'
    
    def mark_as_verified(self, request, queryset):
        """Mark selected records as verified"""
        updated = queryset.update(verified_by=request.user)
        self.message_user(request, f'{updated} FTQ record(s) marked as verified')
    mark_as_verified.short_description = 'Mark as verified by me'
    
    def export_to_excel(self, request, queryset):
        """Export selected records to Excel"""
        # This would require openpyxl or similar library
        self.message_user(request, 'Excel export feature - implement as needed')
    export_to_excel.short_description = 'Export to Excel'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by',
            'verified_by',
            'verification_status'
        ).prefetch_related('time_based_defects')


@admin.register(OperationNumber)
class OperationNumberAdmin(admin.ModelAdmin):
    """Admin for operation numbers"""
    list_display = ['number', 'name', 'description_short', 'defect_count']
    search_fields = ['number', 'name', 'description']
    ordering = ['number']
    
    def description_short(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_short.short_description = 'Description'
    
    def defect_count(self, obj):
        count = obj.defect_types.count()
        return format_html(
            '<span style="background-color: #e0e0e0; padding: 3px 8px; border-radius: 3px;">{} types</span>',
            count
        )
    defect_count.short_description = 'Defect Types'


@admin.register(DefectCategory)
class DefectCategoryAdmin(admin.ModelAdmin):
    """Admin for defect categories"""
    list_display = ['name', 'is_active', 'defect_type_count', 'description_short']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    def defect_type_count(self, obj):
        count = obj.defect_types.count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    defect_type_count.short_description = 'Defect Types'
    
    def description_short(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_short.short_description = 'Description'


@admin.register(DefectType)
class DefectTypeAdmin(admin.ModelAdmin):
    """Admin for defect types"""
    list_display = [
        'name',
        'operation_display',
        'category',
        'is_critical_badge',
        'is_default',
        'order',
        'usage_count'
    ]
    list_filter = ['is_critical', 'is_default', 'category', 'operation_number']
    search_fields = ['name', 'description']
    list_editable = ['is_default', 'order']
    ordering = ['operation_number', 'order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'operation_number', 'category', 'description')
        }),
        ('Settings', {
            'fields': ('is_critical', 'is_default', 'order')
        })
    )
    
    def operation_display(self, obj):
        return f"{obj.operation_number.number} - {obj.operation_number.name}"
    operation_display.short_description = 'Operation'
    
    def is_critical_badge(self, obj):
        if obj.is_critical:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">'
                '<i class="fas fa-exclamation-triangle"></i> Critical'
                '</span>'
            )
        return format_html('<span style="color: #999;">—</span>')
    is_critical_badge.short_description = 'Critical'
    
    def usage_count(self, obj):
        # Count from TimeBasedDefectEntry
        count = TimeBasedDefectEntry.objects.filter(defect_type=obj).count()
        return format_html(
            '<span style="background-color: #e0e0e0; padding: 3px 8px; border-radius: 3px;">{} uses</span>',
            count
        )
    usage_count.short_description = 'Usage'


@admin.register(TimeBasedDefectEntry)
class TimeBasedDefectEntryAdmin(admin.ModelAdmin):
    """Admin for time-based defect entries"""
    list_display = [
        'ftq_record_link',
        'recorded_time',
        'defect_display',
        'count_badge',
        'notes_preview'
    ]
    list_filter = ['recorded_at', 'ftq_record__date']
    search_fields = ['defect_type__name', 'defect_type_custom__name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('FTQ Record', {
            'fields': ('ftq_record',)
        }),
        ('Defect Information', {
            'fields': ('defect_type', 'defect_type_custom', 'recorded_at', 'count')
        }),
        ('Additional Details', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def ftq_record_link(self, obj):
        if obj.ftq_record:
            try:
                url = reverse('admin:main_ftqrecord_change', args=[obj.ftq_record.id])
                return format_html(
                    '<a href="{}">{} - {}</a>',
                    url,
                    obj.ftq_record.date,
                    obj.ftq_record.model_name
                )
            except:
                return f"{obj.ftq_record.date} - {obj.ftq_record.model_name}"
        return 'N/A'
    ftq_record_link.short_description = 'FTQ Record'
    
    def recorded_time(self, obj):
        return obj.recorded_at.strftime('%H:%M')
    recorded_time.short_description = 'Time'
    
    def defect_display(self, obj):
        if obj.defect_type:
            return format_html(
                '<strong>{}</strong><br><small style="color: #666;">{}</small>',
                obj.defect_type.name,
                f"Op {obj.defect_type.operation_number.number}"
            )
        elif obj.defect_type_custom:
            return format_html(
                '<strong>{}</strong> <span style="background-color: #ffc107; color: white; padding: 2px 5px; border-radius: 3px; font-size: 10px;">CUSTOM</span>',
                obj.defect_type_custom.name
            )
        return 'Unknown'
    defect_display.short_description = 'Defect Type'
    
    def count_badge(self, obj):
        color = '#28a745' if obj.count == 0 else '#ffc107' if obj.count < 3 else '#dc3545'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; border-radius: 3px; font-weight: bold; font-size: 14px;">{}</span>',
            color, obj.count
        )
    count_badge.short_description = 'Count'
    
    def notes_preview(self, obj):
        if obj.notes:
            preview = obj.notes[:50] + '...' if len(obj.notes) > 50 else obj.notes
            return format_html('<small title="{}">{}</small>', obj.notes, preview)
        return format_html('<span style="color: #999;">—</span>')
    notes_preview.short_description = 'Notes'


@admin.register(CustomDefectType)
class CustomDefectTypeAdmin(admin.ModelAdmin):
    """Admin for custom defect types"""
    list_display = [
        'name',
        'operation_display',
        'ftq_record_link',
        'added_by',
        'created_at'
    ]
    list_filter = ['operation_number', 'created_at']
    search_fields = ['name', 'added_by__username']
    readonly_fields = ['added_by', 'created_at']
    
    def operation_display(self, obj):
        return f"{obj.operation_number.number} - {obj.operation_number.name}"
    operation_display.short_description = 'Operation'
    
    def ftq_record_link(self, obj):
        if obj.ftq_record:
            try:
                url = reverse('admin:main_ftqrecord_change', args=[obj.ftq_record.id])
                return format_html('<a href="{}">{}</a>', url, f"FTQ #{obj.ftq_record.id}")
            except:
                return f"FTQ #{obj.ftq_record.id}"
        return 'N/A'
    ftq_record_link.short_description = 'FTQ Record'









#  new cheeckshet 

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import (
    User, Shift, DailyVerificationStatus, ChecklistBase,
     Checksheet, ChecksheetSection,
    ChecksheetField, ChecksheetResponse, ChecksheetFieldResponse
)


# ============ IMPROVED INLINE CLASSES ============

class ChecksheetFieldInline(admin.TabularInline):
    """Inline for adding fields directly within a section"""
    model = ChecksheetField
    extra = 0
    classes = ['collapse']
    
    fields = [
        'order', 
        'label', 
        'label_hindi', 
        'field_type', 
        'choices',
        'min_value', 
        'max_value', 
        'unit',
        'is_required',
        'has_status_field',
        'requires_comment_if_nok',
        'auto_fill_based_on_model',
        'is_active'
    ]
    
    ordering = ['order']
    
    # Make it easier to read
    verbose_name = "Field"
    verbose_name_plural = "Fields (Add/Edit fields for this section)"


class ChecksheetSectionInline(admin.StackedInline):
    """Inline for adding sections directly within a checksheet"""
    model = ChecksheetSection
    extra = 0
    classes = ['collapse']
    
    fields = [
        'order', 
        'name', 
        'name_hindi', 
        'description', 
        'is_active',
        'field_count_display'
    ]
    
    readonly_fields = ['field_count_display']
    show_change_link = True
    ordering = ['order']
    
    verbose_name = "Section"
    verbose_name_plural = "Sections (Click section name to add fields)"
    
    def field_count_display(self, obj):
        if obj.pk:
            count = obj.fields.count()
            color = 'green' if count > 0 else 'orange'
            # Create a link to edit fields
            url = reverse('admin:main_checksheetsection_change', args=[obj.pk])
            return format_html(
                '<a href="{}" style="color: {}; font-weight: bold;">{} fields - Click to manage</a>',
                url, color, count
            )
        return format_html('<span style="color: gray;">Save section first to add fields</span>')
    
    field_count_display.short_description = 'Fields'


# ============ ENHANCED CHECKSHEET ADMIN ============

@admin.register(Checksheet)
class ChecksheetAdmin(admin.ModelAdmin):
    """Main checksheet management interface"""
    
    list_display = [
        'name_with_status',
        'name_hindi', 
        'section_count_display',
        'field_count_display', 
        'applicable_models',
        'created_at',
        'action_buttons'
    ]
    
    list_filter = ['is_active', 'created_at', 'applicable_models']
    search_fields = ['name', 'name_hindi', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'stats_display']
    inlines = [ChecksheetSectionInline]
    
    fieldsets = (
        ('📋 Basic Information', {
            'fields': ('name', 'name_hindi', 'description', 'is_active'),
            'description': 'Enter the checksheet name and description'
        }),
        ('⚙️ Configuration', {
            'fields': ('applicable_models',),
            'description': 'Comma-separated model names (e.g., P703,U704) or leave blank for all'
        }),
        ('📊 Statistics', {
            'fields': ('stats_display',),
            'classes': ('collapse',)
        }),
        ('ℹ️ Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def name_with_status(self, obj):
        """Display name prefixed with 'New CHECKSHEET' and show active/inactive badge"""
        if obj.is_active:
            badge = (
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; margin-left: 8px;">ACTIVE</span>'
            )
        else:
            badge = (
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; margin-left: 8px;">INACTIVE</span>'
            )
        
        return format_html(
            obj.name,
            format_html(badge)
        )
    
    name_with_status.short_description = 'Checksheet Name'
    name_with_status.admin_order_field = 'name'
    
    def section_count_display(self, obj):
        """Display section count with color"""
        count = obj.section_count
        if count == 0:
            color = '#dc3545'  # Red
            icon = '⚠️'
        elif count < 3:
            color = '#ffc107'  # Orange
            icon = '📄'
        else:
            color = '#28a745'  # Green
            icon = '✅'
        
        url = reverse('admin:main_checksheet_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="color: {}; font-weight: bold; text-decoration: none;">{} {} sections</a>',
            url, color, icon, count
        )
    
    section_count_display.short_description = 'Sections'
    
    def field_count_display(self, obj):
        """Display total field count with color"""
        count = obj.field_count
        if count == 0:
            color = '#dc3545'  # Red
            icon = '⚠️'
        elif count < 10:
            color = '#ffc107'  # Orange
            icon = '📝'
        else:
            color = '#28a745'  # Green
            icon = '✅'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} fields</span>',
            color, icon, count
        )
    
    field_count_display.short_description = 'Total Fields'
    
    def stats_display(self, obj):
        """Display detailed statistics"""
        if not obj.pk:
            return "Save checksheet first to view statistics"
        
        sections = obj.sections.all()
        total_fields = obj.field_count
        required_fields = ChecksheetField.objects.filter(
            section__checksheet=obj, 
            is_required=True
        ).count()
        optional_fields = total_fields - required_fields
        
        html = f"""
        <div style="padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h3 style="margin-top: 0;">📊 Checksheet Statistics</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Total Sections:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{sections.count()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Total Fields:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{total_fields}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Required Fields:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{required_fields}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Optional Fields:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{optional_fields}</td>
                </tr>
            </table>
            <br>
            <h4>Sections Breakdown:</h4>
            <ul style="margin: 0; padding-left: 20px;">
        """
        
        for section in sections:
            html += f"<li><strong>{section.name}</strong>: {section.fields.count()} fields</li>"
        
        html += "</ul></div>"
        
        return format_html(html)
    
    stats_display.short_description = 'Detailed Statistics'
    
    def action_buttons(self, obj):
        """Add quick action buttons"""
        if not obj.pk:
            return ""
        
        view_url = reverse('admin:main_checksheet_change', args=[obj.pk])
        
        buttons = f"""
        <a href="{view_url}" style="
            background-color: #007bff; 
            color: white; 
            padding: 5px 10px; 
            border-radius: 3px; 
            text-decoration: none;
            font-size: 12px;
            display: inline-block;
            margin: 2px;
        ">✏️ Edit</a>
        """
        
        return format_html(buttons)
    
    action_buttons.short_description = 'Actions'
    
    class Media:
        css = {
            'all': ('admin/css/custom_checksheet.css',)
        }


# ============ ENHANCED SECTION ADMIN ============

@admin.register(ChecksheetSection)
class ChecksheetSectionAdmin(admin.ModelAdmin):
    """Section management with inline field editing"""
    
    list_display = [
        'section_name_display',
        'checksheet_link',
        'order',
        'field_count_badge',
        'is_active_badge',
        'quick_actions'
    ]
    
    list_filter = ['checksheet', 'is_active', 'checksheet__is_active']
    search_fields = ['name', 'name_hindi', 'checksheet__name', 'description']
    list_editable = ['order']
    inlines = [ChecksheetFieldInline]
    ordering = ['checksheet', 'order']
    
    fieldsets = (
        ('📋 Section Information', {
            'fields': ('checksheet', 'name', 'name_hindi', 'description'),
            'description': 'Define the section details'
        }),
        ('⚙️ Settings', {
            'fields': ('order', 'is_active'),
            'description': 'Control display order and visibility'
        }),
    )
    
    def section_name_display(self, obj):
        """Display section name with order"""
        return format_html(
            '<strong>{}.</strong> {} <span style="color: #6c757d; font-size: 12px;">({})</span>',
            obj.order,
            obj.name,
            obj.name_hindi
        )
    
    section_name_display.short_description = 'Section Name'
    section_name_display.admin_order_field = 'name'
    
    def checksheet_link(self, obj):
        """Link to parent checksheet"""
        url = reverse('admin:main_checksheet_change', args=[obj.checksheet.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">📋 {}</a>',
            url,
            obj.checksheet.name
        )
    
    checksheet_link.short_description = 'Checksheet'
    checksheet_link.admin_order_field = 'checksheet__name'
    
    def field_count_badge(self, obj):
        """Display field count as a badge"""
        count = obj.field_count
        if count == 0:
            color = '#dc3545'
            text = 'No fields'
        elif count < 5:
            color = '#ffc107'
            text = f'{count} fields'
        else:
            color = '#28a745'
            text = f'{count} fields'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, text
        )
    
    field_count_badge.short_description = 'Fields'
    
    def is_active_badge(self, obj):
        """Display active status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px;">✓ Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px;">✗ Inactive</span>'
        )
    
    is_active_badge.short_description = 'Status'
    
    def quick_actions(self, obj):
        """Quick action buttons"""
        edit_url = reverse('admin:main_checksheetsection_change', args=[obj.pk])
        
        return format_html(
            '<a href="{}" style="background-color: #007bff; color: white; padding: 4px 8px; border-radius: 3px; text-decoration: none; font-size: 11px;">✏️ Edit Fields</a>',
            edit_url
        )
    
    quick_actions.short_description = 'Actions'


# ============ ENHANCED FIELD ADMIN ============

@admin.register(ChecksheetField)
class ChecksheetFieldAdmin(admin.ModelAdmin):
    """Individual field management"""
    
    list_display = [
        'field_name_display',
        'section_link',
        'field_type_badge',
        'validation_info',
        'status_flags',
        'order',
        'is_active_badge'
    ]
    
    list_filter = [
        'section__checksheet',
        'section',
        'field_type',
        'is_required',
        'has_status_field',
        'auto_fill_based_on_model',
        'is_active'
    ]
    
    search_fields = ['label', 'label_hindi', 'section__name', 'section__checksheet__name']
    list_editable = ['order']
    ordering = ['section__checksheet', 'section__order', 'order']
    
    fieldsets = (
        ('📝 Field Information', {
            'fields': ('section', 'label', 'label_hindi', 'field_type'),
            'description': 'Basic field information'
        }),
        ('⚙️ Field Configuration', {
            'fields': (
                'is_required', 
                'choices', 
                'default_value', 
                'placeholder',
                'help_text', 
                'help_text_hindi'
            ),
            'description': 'Configure field behavior and display'
        }),
        ('✅ Validation Rules', {
            'fields': ('min_value', 'max_value', 'unit'),
            'description': 'Set validation constraints for numeric fields'
        }),
        ('🔧 Advanced Features', {
            'fields': (
                'has_status_field', 
                'requires_comment_if_nok',
                'auto_fill_based_on_model', 
                'model_value_mapping'
            ),
            'description': 'Advanced field features and auto-fill configuration',
            'classes': ('collapse',)
        }),
        ('📊 Display Settings', {
            'fields': ('order', 'is_active'),
            'description': 'Control field order and visibility'
        }),
    )
    
    def field_name_display(self, obj):
        """Display field name with order"""
        return format_html(
            '<strong>{}.</strong> {} <br><span style="color: #6c757d; font-size: 11px;">{}</span>',
            obj.order,
            obj.label,
            obj.label_hindi
        )
    
    field_name_display.short_description = 'Field Name'
    
    def section_link(self, obj):
        """Link to parent section"""
        section_url = reverse('admin:main_checksheetsection_change', args=[obj.section.pk])
        checksheet_url = reverse('admin:main_checksheet_change', args=[obj.section.checksheet.pk])
        
        return format_html(
            '<a href="{}" style="text-decoration: none;">📋 {}</a><br>'
            '<a href="{}" style="text-decoration: none; color: #6c757d; font-size: 11px;">└─ {}</a>',
            checksheet_url,
            obj.section.checksheet.name,
            section_url,
            obj.section.name
        )
    
    section_link.short_description = 'Checksheet / Section'
    
    def field_type_badge(self, obj):
        """Display field type as colored badge"""
        type_colors = {
            'text': '#6c757d',
            'number': '#007bff',
            'decimal': '#17a2b8',
            'dropdown': '#28a745',
            'ok_nok': '#ffc107',
            'yes_no': '#fd7e14',
            'date': '#e83e8c',
            'time': '#6f42c1',
            'datetime': '#20c997',
            'checkbox': '#6610f2',
            'textarea': '#6c757d'
        }
        
        color = type_colors.get(obj.field_type, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_field_type_display()
        )
    
    field_type_badge.short_description = 'Type'
    
    def validation_info(self, obj):
        """Display validation information"""
        if obj.field_type in ['number', 'decimal']:
            if obj.min_value is not None or obj.max_value is not None:
                range_text = f"{obj.min_value or '−∞'} to {obj.max_value or '+∞'}"
                if obj.unit:
                    range_text += f" {obj.unit}"
                return format_html(
                    '<span style="font-size: 11px; color: #6c757d;">Range: {}</span>',
                    range_text
                )
        elif obj.field_type == 'dropdown' and obj.choices:
            choice_count = len(obj.get_choices_list())
            return format_html(
                '<span style="font-size: 11px; color: #6c757d;">{} options</span>',
                choice_count
            )
        
        return format_html('<span style="font-size: 11px; color: #adb5bd;">—</span>')
    
    validation_info.short_description = 'Validation'
    
    def status_flags(self, obj):
        """Display feature flags"""
        flags = []
        
        if obj.is_required:
            flags.append('<span style="background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">REQUIRED</span>')
        
        if obj.has_status_field:
            flags.append('<span style="background-color: #ffc107; color: black; padding: 2px 6px; border-radius: 3px; font-size: 10px;">OK/NOK</span>')
        
        if obj.auto_fill_based_on_model:
            flags.append('<span style="background-color: #17a2b8; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">AUTO-FILL</span>')
        
        if obj.requires_comment_if_nok:
            flags.append('<span style="background-color: #6610f2; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">COMMENT</span>')
        
        if not flags:
            return format_html('<span style="font-size: 11px; color: #adb5bd;">—</span>')
        
        return format_html(' '.join(flags))
    
    status_flags.short_description = 'Features'
    
    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-size: 16px;">✓</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-size: 16px;">✗</span>'
        )
    
    is_active_badge.short_description = 'Active'


# ============ RESPONSE ADMIN ============

class ChecksheetFieldResponseInline(admin.TabularInline):
    """Inline for viewing field responses"""
    model = ChecksheetFieldResponse
    extra = 0
    can_delete = False
    
    fields = ['field_label', 'value', 'status', 'comment', 'filled_by', 'filled_at']
    readonly_fields = ['field_label', 'value', 'status', 'comment', 'filled_by', 'filled_at']
    
    def field_label(self, obj):
        return f"{obj.field.section.name} → {obj.field.label}"
    
    field_label.short_description = 'Field'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChecksheetResponse)
class ChecksheetResponseAdmin(admin.ModelAdmin):
    """Checksheet response viewing and management"""
    
    list_display = [
        'response_id',
        'checksheet_link',
        'status_badge',
        'filled_by',
        'created_at',
        'approval_status'
    ]
    
    list_filter = ['status', 'checksheet', 'created_at', 'filled_by']
    search_fields = [
        'checksheet__name',
        'filled_by__username',
        'verification_status__date'
    ]
    
    readonly_fields = [
        'checksheet',
        'verification_status',
        'filled_by',
        'created_at',
        'updated_at',
        'submitted_at',
        'supervisor_approved_by',
        'supervisor_approved_at',
        'quality_approved_by',
        'quality_approved_at',
        'response_summary'
    ]
    
    inlines = [ChecksheetFieldResponseInline]
    
    fieldsets = (
        ('📋 Response Information', {
            'fields': (
                'checksheet',
                'verification_status',
                'status',
                'filled_by',
                'created_at',
                'updated_at',
                'submitted_at'
            )
        }),
        ('📊 Response Summary', {
            'fields': ('response_summary',),
            'classes': ('collapse',)
        }),
        ('✅ Approval Information', {
            'fields': (
                'supervisor_approved_by',
                'supervisor_approved_at',
                'quality_approved_by',
                'quality_approved_at'
            ),
            'classes': ('collapse',)
        }),
        ('📝 Additional Information', {
            'fields': ('rejection_reason', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def response_id(self, obj):
        return f"#{obj.pk}"
    
    response_id.short_description = 'ID'
    
    def checksheet_link(self, obj):
        url = reverse('admin:main_checksheet_change', args=[obj.checksheet.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">📋 {}</a>',
            url,
            obj.checksheet.name
        )
    
    checksheet_link.short_description = 'Checksheet'
    
    def status_badge(self, obj):
        status_colors = {
            'draft': '#6c757d',
            'submitted': '#007bff',
            'supervisor_approved': '#ffc107',
            'quality_approved': '#28a745',
            'rejected': '#dc3545'
        }
        
        color = status_colors.get(obj.status, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def approval_status(self, obj):
        """Show approval progress"""
        html = ""
        
        if obj.supervisor_approved_by:
            html += '<span style="color: #28a745;">✓ Supervisor</span><br>'
        else:
            html += '<span style="color: #dc3545;">✗ Supervisor</span><br>'
        
        if obj.quality_approved_by:
            html += '<span style="color: #28a745;">✓ Quality</span>'
        else:
            html += '<span style="color: #dc3545;">✗ Quality</span>'
        
        return format_html(html)
    
    approval_status.short_description = 'Approvals'
    
    def response_summary(self, obj):
        """Display response summary"""
        if not obj.pk:
            return "Save response first"
        
        total = obj.field_responses.count()
        filled = obj.field_responses.exclude(value='').count()
        
        return format_html(
            '<div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">'
            '<strong>Completion:</strong> {}/{} fields filled ({}%)'
            '</div>',
            filled, total, int((filled/total*100) if total > 0 else 0)
        )
    
    response_summary.short_description = 'Summary'




# ============ ADMIN LABEL CUSTOMIZATION ============

# Rename models for better admin display

Checksheet._meta.verbose_name = "New CHECKSHEET"
Checksheet._meta.verbose_name_plural = "New CHECKSHEETS"

ChecksheetSection._meta.verbose_name = "New CHECKSHEET Section"
ChecksheetSection._meta.verbose_name_plural = "New CHECKSHEET Sections"

ChecksheetField._meta.verbose_name = "New CHECKSHEET Field"
ChecksheetField._meta.verbose_name_plural = "New CHECKSHEET Fields"

ChecksheetResponse._meta.verbose_name = "New CHECKSHEET Response"
ChecksheetResponse._meta.verbose_name_plural = "New CHECKSHEET Responses"

ChecksheetFieldResponse._meta.verbose_name = "New CHECKSHEET Field Response"
ChecksheetFieldResponse._meta.verbose_name_plural = "New CHECKSHEET Field Responses"


# ============ CUSTOMIZE ADMIN SITE ============

admin.site.site_header = '🔧 Checklist System Administration'
admin.site.site_title = 'Checklist System'
admin.site.index_title = '📋 Checksheet & Checklist Management Dashboard'

# Change the default empty text
admin.site.empty_value_display = '—'