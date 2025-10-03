from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    USER_TYPES = (
        ('operator', 'Operator'),
        ('shift_supervisor', 'Shift Supervisor'),
        ('quality_supervisor', 'Quality Supervisor'),
    )
    company_id = models.CharField(max_length=100, blank=True, null=True)    
    skill_matrix_level = models.CharField(max_length=200, blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    
    @property
    def get_user_type(self):
        """Returns the user type, including admin if superuser"""
        if self.is_superuser:
            return 'admin'
        return self.user_type


class Shift(models.Model):
    # Updated shift choices to match your requirement
    SHIFT_CHOICES = [
        ('S1', 'S1 - 6:30 AM to 6:30 PM'),
        ('A', 'A - 6:30 AM to 3:00 PM'),
        ('G', 'G - 8:30 AM to 5:00 PM'),
        ('B', 'B - 3:00 PM to 11:30 PM'),
        ('C', 'C - 11:30 PM to 6:30 AM'),
        ('S2', 'S2 - 6:30 PM to 6:30 AM'),
    ]
    
    date = models.DateField(default=timezone.now)
    shift_type = models.CharField(max_length=10, choices=SHIFT_CHOICES)
    operator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='operated_shifts')
    shift_supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervised_shifts')
    quality_supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quality_supervised_shifts')

    def __str__(self):
        return f"{self.date} - {self.get_shift_type_display()}"


    # Removed unique_together constraint to allow multiple checksheets



class DailyVerificationStatus(models.Model):
    """Central status tracking for daily verification/inspection sheets"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    )
    
    date = models.DateField(default=timezone.now)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='verification_statuses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_verifications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add notification flags
    operator_notified = models.BooleanField(default=False)
    supervisor_notified = models.BooleanField(default=False)
    quality_notified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.date} - {self.shift.get_shift_type_display()} - {self.status}"
    
    # Optional helper properties for consistency
    @property
    def has_checklist(self):
        """Check if this verification has a checklist"""
        return self.checklists.exists()
    
    @property
    def has_ep_check(self):
        """Check if this verification has an EP check"""
        return self.error_prevention_checks.exists()
    
    @property
    def has_dtpm_checklist(self):
        """Check if this verification has a DTPM checklist"""
        return self.dtpm_checklists.exists()
    
    @property
    def workflow_completion_status(self):
        """Get overall workflow completion status"""
        checklist_done = self.has_checklist
        ep_check_done = self.has_ep_check
        dtpm_done = self.has_dtpm_checklist
        
        completed_items = sum([checklist_done, ep_check_done, dtpm_done])
        total_items = 3
        
        return {
            'checklist': checklist_done,
            'ep_check': ep_check_done,
            'dtpm': dtpm_done,
            'completion_percentage': (completed_items / total_items) * 100,
            'is_complete': completed_items == total_items
        }
    
    @property
    def current_model_from_checklist(self):
        """Get the current model from the associated checklist"""
        checklist = self.checklists.first()
        return checklist.selected_model if checklist else None


class ChecklistBase(models.Model):
    """Base checklist information filled once per shift"""
    MODEL_CHOICES = (
        ('P703', 'P703'),
        ('U704', 'U704'),
        ('FD', 'FD'),
        ('SA', 'SA'),
        ('Gnome', 'Gnome'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('quality_approved', 'Quality Approved'),
        ('rejected', 'Rejected'),
    )

    OK_NG_CHOICES = [('OK', 'OK'), ('NOK', 'NOK')]
    YES_NO_CHOICES = [('Yes', 'Yes'), ('NOK', 'NOK')]

    TOP_TOOL_CHOICES = [
        ('FMA-03-35-T05', 'FMA-03-35-T05 (P703/U704/SA/FD/Gnome)'),
    ]

    BOTTOM_TOOL_CHOICES = [
        ('FMA-03-35-T06', 'FMA-03-35-T06 (P703/U704/SA/FD)'),
        ('FMA-03-35-T08', 'FMA-03-35-T08 (Gnome)'),
    ]

    UV_ASSY_STAGE_CHOICES = [
        ('FMA-03-35-T07', 'FMA-03-35-T07 (P703/U704/SA/FD)'),
        ('FMA-03-35-T09', 'FMA-03-35-T09 (Gnome)'),
    ]

    RETAINER_PART_CHOICES = [
        ('42001878', '42001878 (P703/U704/SA/FD)'),
        ('42050758', '42050758 (Gnome)'),
    ]

    UV_CLIP_PART_CHOICES = [
        ('42000829', '42000829 (P703/U704/SA/FD)'),
        ('42000829', '42000829 (Gnome)'),  # Same number for both
    ]

    UMBRELLA_PART_CHOICES = [
        ('25094588', '25094588 (P703/U704/SA/FD/Gnome)'),
    ]
    SHIFTS = [
    ('S1', 'S1 - 6:30 AM to 6:30 PM'),
    ('A', 'A - 6:30 AM to 3:00 PM'),
    ('G', 'G - 8:30 AM to 5:00 PM'),
    ('B', 'B - 3:00 PM to 11:30 PM'),
    ('C', 'C - 11:30 PM to 6:30 AM'),
    ('S2', 'S2 - 6:30 PM to 6:30 AM'),
]


    # Link to DailyVerificationStatus instead of directly to Shift
    verification_status = models.ForeignKey(DailyVerificationStatus, on_delete=models.CASCADE, related_name='checklists',null=True,blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # Program selection and basic measurements
    selected_model = models.CharField(
        max_length=10, 
        choices=MODEL_CHOICES,
        verbose_name="Program selection on HMI (HMI से Program select करना है)"
    )
    
    line_pressure = models.FloatField(
        help_text="Recommended Range: 4.5 - 5.5 bar"
    )
    
    oring_condition = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="O-ring condition (UV Flow check sealing area) (O-ring सील की स्थिति सही होनी चाहिए)"
    )
    
    uv_flow_input_pressure = models.FloatField(
        help_text="Recommended Range: 11-15 kPa",
        verbose_name="UV Flow input Test Pressure (13+/- 2 KPa)"
    )
    
    # Verifications
    master_verification_lvdt = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Master Verification for LVDT"
    )
    
    good_bad_master_verification = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Good and Bad master verification (refer EPVS)"
    )
    
    test_pressure_vacuum = models.FloatField(
        help_text="Recommended Range: 0.25 - 0.3 MPa",
        verbose_name="Test Pressure for Vacuum generation"
    )
    
    tool_alignment = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Tool Alignment (Top & Bottom) (Tool Alignment) सही होना चाहिए"
    )
    
    # Tool IDs and Part Numbers
    top_tool_id = models.CharField(
        max_length=100,
        choices=TOP_TOOL_CHOICES,
        verbose_name="Top Tool ID",
        null=True,blank=True
    )
    top_tool_id_status=models.CharField(max_length=50, choices=OK_NG_CHOICES, null=True,blank=True)
    
    bottom_tool_id = models.CharField(
        max_length=100,
        choices=BOTTOM_TOOL_CHOICES,
        verbose_name="Bottom Tool ID",
        null=True,blank=True
    )
    bottom_tool_id_status=models.CharField(max_length=50, choices=OK_NG_CHOICES, null=True,blank=True)
    
    uv_assy_stage_id = models.CharField(
        max_length=100,
        choices=UV_ASSY_STAGE_CHOICES,
        verbose_name="UV Assy Stage 1 ID",
        null=True,blank=True
    )
    uv_assy_stage_id_status=models.CharField(max_length=50, choices=OK_NG_CHOICES, null=True,blank=True)
    
    retainer_part_no = models.CharField(
        max_length=100,
        choices=RETAINER_PART_CHOICES,
        verbose_name="Retainer Part no",
        null=True,blank=True
    )
    retainer_part_no_status=models.CharField(max_length=50, choices=OK_NG_CHOICES, null=True,blank=True)
    
    uv_clip_part_no = models.CharField(
        max_length=100,
        choices=UV_CLIP_PART_CHOICES,
        verbose_name="UV Clip Part No",
        null=True,blank=True
    )
    uv_clip_part_no_status=models.CharField(max_length=50, choices=OK_NG_CHOICES, null=True,blank=True)
    
    umbrella_part_no = models.CharField(
        max_length=100,
        choices=UMBRELLA_PART_CHOICES,
        verbose_name="Umbrella Part No",
        null=True,blank=True
    )
    umbrella_part_no_status=models.CharField(max_length=50, choices=OK_NG_CHOICES, null=True,blank=True)
    
    # Additional checks
    retainer_id_lubrication = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Retainer ID lubrication"
    )
    new_shift=models.CharField(max_length=100, choices=SHIFTS, null=True,blank=True)

    # Add a shift field that will be automatically set from new_shift
    shift = models.CharField(max_length=100, choices=SHIFTS, null=True, blank=True, editable=False)
    
    error_proofing_verification = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="All Error proofing / Error detection verification done"
    )
    
    
    frequency_config = models.ForeignKey(
        'SubgroupFrequencyConfig', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Measurement frequency for this model"
    )


    def save(self, *args, **kwargs):
        """Custom save method to set shift from new_shift"""
        if self.new_shift:
            self.shift = self.new_shift
        super().save(*args, **kwargs)

    def __str__(self):
        shift_display = self.get_shift_display() if self.shift else "No Shift"
        return f"Checklist - {shift_display} - {self.selected_model} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']



class SubgroupFrequencyConfig(models.Model):
    """Configuration for subgroup measurement frequency"""
    model_name = models.CharField(max_length=10, choices=ChecklistBase.MODEL_CHOICES, unique=True)
    frequency_hours = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Hours between measurements (1-12)"
    )
    max_subgroups = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        help_text="Maximum number of subgroups per shift"
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.model_name} - Every {self.frequency_hours} hours ({self.max_subgroups} max)"
    
    class Meta:
        verbose_name = "Subgroup Frequency Configuration"
        verbose_name_plural = "Subgroup Frequency Configurations"

# models.py - Updated with single workstation cleanliness reading

class SubgroupEntry(models.Model):
    """Repeated measurements taken every 2 hours - now with 5 readings each (except workstation cleanliness)"""
    VERIFICATION_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('supervisor_verified', 'Supervisor Verified'),
        ('quality_verified', 'Quality Verified'),
        ('rejected', 'Rejected'),
    )    

    OK_NG_CHOICES = [('OK', 'OK'), ('NOK', 'NOK')]
    YES_NO_CHOICES = [('Yes', 'Yes'), ('NOK', 'NOK')]

    checklist = models.ForeignKey(ChecklistBase, on_delete=models.CASCADE, related_name='subgroup_entries')
    subgroup_number = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending',
        blank=True
    )
    # NEW: Add maintenance/ME activity tracking
    is_after_maintenance = models.BooleanField(default=False, verbose_name="Added after maintenance/ME activity")
    maintenance_comment = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Maintenance activity comment",
        help_text="Describe the maintenance/ME activity performed"
    )
    effectiveness_comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Effectiveness comment",
        help_text="Comment on effectiveness of maintenance activity"
    )

    # UV Vacuum Test - 5 readings
    uv_vacuum_test_1 = models.FloatField(
        help_text="Reading 1: Recommended Range: -35 to -43 kPa",
        verbose_name="UV Vacuum Test Reading 1",
        blank=True,null=True
    )
    uv_vacuum_test_2 = models.FloatField(
        help_text="Reading 2: Recommended Range: -35 to -43 kPa",
        verbose_name="UV Vacuum Test Reading 2",
         blank=True,null=True
    )
    uv_vacuum_test_3 = models.FloatField(
        help_text="Reading 3: Recommended Range: -35 to -43 kPa",
        verbose_name="UV Vacuum Test Reading 3",
         blank=True,null=True
    )
    uv_vacuum_test_4 = models.FloatField(
        help_text="Reading 4: Recommended Range: -35 to -43 kPa",
        verbose_name="UV Vacuum Test Reading 4",
         blank=True,null=True
    )
    uv_vacuum_test_5 = models.FloatField(
        help_text="Reading 5: Recommended Range: -35 to -43 kPa",
        verbose_name="UV Vacuum Test Reading 5",
         blank=True,null=True
    )
    
    # UV Flow Value - 5 readings
    uv_flow_value_1 = models.FloatField(
        help_text="Reading 1: Recommended Range: 30-40 LPM",
        verbose_name="UV Flow Value Reading 1",
         blank=True,null=True
    )
    uv_flow_value_2 = models.FloatField(
        help_text="Reading 2: Recommended Range: 30-40 LPM",
        verbose_name="UV Flow Value Reading 2",
         blank=True,null=True
    )
    uv_flow_value_3 = models.FloatField(
        help_text="Reading 3: Recommended Range: 30-40 LPM",
        verbose_name="UV Flow Value Reading 3",
         blank=True,null=True
    )
    uv_flow_value_4 = models.FloatField(
        help_text="Reading 4: Recommended Range: 30-40 LPM",
        verbose_name="UV Flow Value Reading 4",
         blank=True,null=True
    )
    uv_flow_value_5 = models.FloatField(
        help_text="Reading 5: Recommended Range: 30-40 LPM",
        verbose_name="UV Flow Value Reading 5"
        , blank=True,null=True
        
    )
    
    # Umbrella Valve Assembly - 5 readings
    umbrella_valve_assembly_1 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Umbrella Valve Assembly Reading 1",
         blank=True,null=True
    )
    umbrella_valve_assembly_2 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Umbrella Valve Assembly Reading 2"
        , blank=True,null=True
    )
    umbrella_valve_assembly_3 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Umbrella Valve Assembly Reading 3",
         blank=True,null=True
    )
    umbrella_valve_assembly_4 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Umbrella Valve Assembly Reading 4", blank=True,null=True
    )
    umbrella_valve_assembly_5 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="Umbrella Valve Assembly Reading 5", blank=True,null=True
    )
    
    # UV Clip Pressing - 5 readings
    uv_clip_pressing_1 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="UV Clip Pressing Reading 1", blank=True,null=True
    )
    uv_clip_pressing_2 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="UV Clip Pressing Reading 2", blank=True,null=True
    )
    uv_clip_pressing_3 = models.CharField(
        max_length=3,
        choices=OK_NG_CHOICES,
        verbose_name="UV Clip Pressing Reading 3", blank=True,null=True
    )
    uv_clip_pressing_4 = models.CharField(
        max_length=5,
        choices=OK_NG_CHOICES,
        verbose_name="UV Clip Pressing Reading 4", blank=True,null=True
    )
    uv_clip_pressing_5 = models.CharField(
        max_length=5,
        choices=OK_NG_CHOICES,
        verbose_name="UV Clip Pressing Reading 5", blank=True,null=True
    )
    
    # Workstation Clean - CHANGED TO SINGLE READING
    workstation_clean = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="Workstation Clean",
        blank=True,null=True
    )
    
    # Bin Contamination Check - 5 readings
    bin_contamination_check_1 = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="Bin Contamination Check Reading 1", blank=True,null=True
    )
    bin_contamination_check_2 = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="Bin Contamination Check Reading 2", blank=True,null=True
    )
    bin_contamination_check_3 = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="Bin Contamination Check Reading 3", blank=True,null=True
    )
    bin_contamination_check_4 = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="Bin Contamination Check Reading 4", blank=True,null=True
    )
    bin_contamination_check_5 = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="Bin Contamination Check Reading 5", blank=True,null=True
    )
    # NEW: Flag for NOK entries requiring approval
    has_nok_entries = models.BooleanField(default=False, editable=False)
    nok_supervisor_approved = models.BooleanField(default=False)
    nok_quality_approved = models.BooleanField(default=False)
    nok_supervisor_approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='nok_supervisor_approvals'
    )
    nok_quality_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nok_quality_approvals'
    )
    nok_approval_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['subgroup_number']

    def save(self, *args, **kwargs):
        # Track changes if this is an update (not initial creation)
        if self.pk:  # Only for existing records
            try:
                old_instance = SubgroupEntry.objects.get(pk=self.pk)
                
                # Updated fields to track for changes (now 21 fields total)
                tracked_fields = [
                    'uv_vacuum_test_1', 'uv_vacuum_test_2', 'uv_vacuum_test_3', 'uv_vacuum_test_4', 'uv_vacuum_test_5',
                    'uv_flow_value_1', 'uv_flow_value_2', 'uv_flow_value_3', 'uv_flow_value_4', 'uv_flow_value_5',
                    'umbrella_valve_assembly_1', 'umbrella_valve_assembly_2', 'umbrella_valve_assembly_3', 'umbrella_valve_assembly_4', 'umbrella_valve_assembly_5',
                    'uv_clip_pressing_1', 'uv_clip_pressing_2', 'uv_clip_pressing_3', 'uv_clip_pressing_4', 'uv_clip_pressing_5',
                    'workstation_clean',  # Now single field
                    'bin_contamination_check_1', 'bin_contamination_check_2', 'bin_contamination_check_3', 'bin_contamination_check_4', 'bin_contamination_check_5'
                ]
                
                # Get the user who made the change (from thread-local storage or pass as parameter)
                current_user = getattr(self, '_editing_user', None)
                
                if current_user:
                    for field in tracked_fields:
                        old_value = getattr(old_instance, field)
                        new_value = getattr(self, field)
                        
                        if old_value != new_value:
                            SubgroupEditHistory.objects.create(
                                subgroup=self,
                                edited_by=current_user,
                                field_name=field,
                                old_value=str(old_value) if old_value is not None else None,
                                new_value=str(new_value) if new_value is not None else None
                            )
            except SubgroupEntry.DoesNotExist:
                # This shouldn't happen, but handle gracefully
                pass
        
        # Always call the parent save method
        super().save(*args, **kwargs)        
        
    def _check_for_nok_entries(self):
        """Check if any field has NOK or No value"""
        nok_fields = [
            self.umbrella_valve_assembly_1, self.umbrella_valve_assembly_2,
            self.umbrella_valve_assembly_3, self.umbrella_valve_assembly_4,
            self.umbrella_valve_assembly_5,
            self.uv_clip_pressing_1, self.uv_clip_pressing_2,
            self.uv_clip_pressing_3, self.uv_clip_pressing_4,
            self.uv_clip_pressing_5,
        ]
        
        no_fields = [
            self.workstation_clean,
            self.bin_contamination_check_1, self.bin_contamination_check_2,
            self.bin_contamination_check_3, self.bin_contamination_check_4,
            self.bin_contamination_check_5,
        ]
        
        # Check for out-of-range values
        out_of_range = False
        uv_vacuum_readings = [
            self.uv_vacuum_test_1, self.uv_vacuum_test_2, self.uv_vacuum_test_3,
            self.uv_vacuum_test_4, self.uv_vacuum_test_5
        ]
        uv_flow_readings = [
            self.uv_flow_value_1, self.uv_flow_value_2, self.uv_flow_value_3,
            self.uv_flow_value_4, self.uv_flow_value_5
        ]
        
        for val in uv_vacuum_readings:
            if val is not None and not (-43 <= val <= -35):
                out_of_range = True
                break
                
        for val in uv_flow_readings:
            if val is not None and not (30 <= val <= 40):
                out_of_range = True
                break
        
        return (
            'NOK' in nok_fields or 
            'No' in no_fields or 
            out_of_range
        )
        
    @property
    def requires_nok_approval(self):
        """Check if this entry has NOK values and needs approval"""
        return self.has_nok_entries and not (self.nok_supervisor_approved and self.nok_quality_approved)

    # Helper methods to get average values
    @property
    def uv_vacuum_average(self):
        """Calculate average of UV vacuum test readings"""
        readings = [self.uv_vacuum_test_1, self.uv_vacuum_test_2, self.uv_vacuum_test_3, 
                   self.uv_vacuum_test_4, self.uv_vacuum_test_5]
        # Filter out None values
        valid_readings = [r for r in readings if r is not None]
        if not valid_readings:
            return 0
        return sum(valid_readings) / len(valid_readings)
    
    @property
    def uv_flow_average(self):
        """Calculate average of UV flow value readings"""
        readings = [self.uv_flow_value_1, self.uv_flow_value_2, self.uv_flow_value_3, 
                   self.uv_flow_value_4, self.uv_flow_value_5]
        # Filter out None values
        valid_readings = [r for r in readings if r is not None]
        if not valid_readings:
            return 0
        return sum(valid_readings) / len(valid_readings)
    
    @property
    def umbrella_valve_ok_count(self):
        readings = [self.umbrella_valve_assembly_1, self.umbrella_valve_assembly_2, 
                   self.umbrella_valve_assembly_3, self.umbrella_valve_assembly_4, 
                   self.umbrella_valve_assembly_5]
        valid_readings = [r for r in readings if r is not None]
        return valid_readings.count('OK')
    
    @property
    def uv_clip_ok_count(self):
        """Count how many UV clip readings are OK"""
        readings = [self.uv_clip_pressing_1, self.uv_clip_pressing_2, 
                   self.uv_clip_pressing_3, self.uv_clip_pressing_4, 
                   self.uv_clip_pressing_5]
        # Filter out None values and count 'OK'
        valid_readings = [r for r in readings if r is not None]
        return valid_readings.count('OK')
    
    @property
    def workstation_status(self):
        """Get workstation cleanliness status (single value)"""
        return self.workstation_clean
    
    @property
    def bin_contamination_yes_count(self):
        """Count how many bin contamination readings are Yes"""
        readings = [self.bin_contamination_check_1, self.bin_contamination_check_2, 
                   self.bin_contamination_check_3, self.bin_contamination_check_4, 
                   self.bin_contamination_check_5]
        # Filter out None values and count 'Yes'
        valid_readings = [r for r in readings if r is not None]
        return valid_readings.count('Yes')
    
    # Additional helper properties for validation
    @property
    def total_readings_count(self):
        """Count total number of readings entered (non-None values) - now 21 total"""
        all_readings = [
            self.uv_vacuum_test_1, self.uv_vacuum_test_2, self.uv_vacuum_test_3, self.uv_vacuum_test_4, self.uv_vacuum_test_5,
            self.uv_flow_value_1, self.uv_flow_value_2, self.uv_flow_value_3, self.uv_flow_value_4, self.uv_flow_value_5,
            self.umbrella_valve_assembly_1, self.umbrella_valve_assembly_2, self.umbrella_valve_assembly_3, self.umbrella_valve_assembly_4, self.umbrella_valve_assembly_5,
            self.uv_clip_pressing_1, self.uv_clip_pressing_2, self.uv_clip_pressing_3, self.uv_clip_pressing_4, self.uv_clip_pressing_5,
            self.workstation_clean,  # Single field
            self.bin_contamination_check_1, self.bin_contamination_check_2, self.bin_contamination_check_3, self.bin_contamination_check_4, self.bin_contamination_check_5
        ]
        return sum(1 for reading in all_readings if reading is not None)
    
    @property
    def is_complete(self):
        """Check if all 21 readings are filled"""
        return self.total_readings_count == 21
    
    @property
    def completion_percentage(self):
        """Get completion percentage (0-100) - now based on 21 total readings"""
        return (self.total_readings_count / 21) * 100
    
    # Keep existing properties (unchanged)
    @property
    def has_been_edited(self):
        """Check if this subgroup has been edited"""
        return self.edit_history.exists()
    
    @property
    def last_edited_at(self):
        """Get the last edit timestamp"""
        last_edit = self.edit_history.first()
        return last_edit.edited_at if last_edit else None
    
    @property
    def edited_by(self):
        """Get who last edited this subgroup"""
        last_edit = self.edit_history.first()
        return last_edit.edited_by if last_edit else None
    
    @property
    def current_status(self):
        """Get current verification status based on verifications"""
        latest = self.get_latest_verification()
        if not latest:
            return 'pending'
            
        if latest.verifier_type == 'supervisor':
            if latest.status == 'rejected':
                return 'rejected'
            return 'supervisor_verified'
            
        if latest.verifier_type == 'quality':
            if latest.status == 'rejected':
                return 'rejected'
            return 'quality_verified'
            
        return 'pending'

    def get_latest_verification(self):
        """Helper method to get latest verification"""
        return self.verifications.order_by('-verified_at').first()   
    
class SubgroupVerification(models.Model):
    """Verification records for each subgroup entry"""
    VERIFIER_TYPES = (
        ('supervisor', 'Shift Supervisor'),
        ('quality', 'Quality Supervisor'),
    )
    
    subgroup = models.ForeignKey(SubgroupEntry, on_delete=models.CASCADE, related_name='verifications')
    verified_by = models.ForeignKey(User, on_delete=models.CASCADE)
    verifier_type = models.CharField(max_length=20, choices=VERIFIER_TYPES)
    verified_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=SubgroupEntry.VERIFICATION_STATUS_CHOICES
    )
    comments = models.TextField(blank=True)

    class Meta:
        # Removed unique_together constraint
        ordering = ['verified_at']

class SubgroupEditHistory(models.Model):
    subgroup = models.ForeignKey(SubgroupEntry, on_delete=models.CASCADE, related_name='edit_history')
    edited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    edited_at = models.DateTimeField(auto_now_add=True)
    field_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=200, null=True, blank=True)
    new_value = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        ordering = ['-edited_at']
        
    def __str__(self):
        return f"{self.subgroup} - {self.field_name} changed by {self.edited_by}"

    def get_field_display_name(self):
        """Return human-readable field names"""
        field_names = {
            'uv_vacuum_test': 'UV Vacuum Test',
            'uv_flow_value': 'UV Flow Value', 
            'umbrella_valve_assembly': 'Umbrella Valve Assembly',
            'uv_clip_pressing': 'UV Clip Pressing',
            'workstation_clean': 'Work Station Cleanliness',
            'bin_contamination_check': 'Bin Contamination Check'
        }
        return field_names.get(self.field_name, self.field_name)

class Verification(models.Model):
    """Final verification for the entire checklist"""
    checklist = models.ForeignKey(ChecklistBase, on_delete=models.CASCADE, related_name='verifications')
    team_leader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_leader_verifications')
    shift_supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shift_supervisor_verifications')
    quality_supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quality_supervisor_verifications')
    verified_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)


class Concern(models.Model):
    """Concerns and actions taken"""
    checklist = models.ForeignKey(ChecklistBase, on_delete=models.CASCADE)
    subgroup = models.ForeignKey(SubgroupEntry, on_delete=models.CASCADE, null=True, blank=True)
    concern_identified = models.TextField()
    cause_if_known = models.TextField(blank=True)
    action_taken = models.TextField()
    manufacturing_approval = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='manufacturing_approvals', 
        null=True
    )
    quality_approval = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='quality_approvals', 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)





class DefectCategory(models.Model):
    """Categories of defects, such as 'Incorrect parts', 'Damage', etc."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Defect Categories"



# Model for configurable checksheet content
class ChecksheetContentConfig(models.Model):
    """Configurable content for different models"""
    model_name = models.CharField(max_length=10, choices=ChecklistBase.MODEL_CHOICES)
    parameter_name = models.CharField(max_length=200, verbose_name="Parameter Name")
    parameter_name_hindi = models.CharField(max_length=200, verbose_name="Parameter Name (Hindi)", blank=True)
    measurement_type = models.CharField(
        max_length=20,
        choices=[
            ('numeric', 'Numeric'),
            ('ok_nok', 'OK/NOK'),
            ('yes_no', 'Yes/No'),
        ]
    )
    min_value = models.FloatField(null=True, blank=True, verbose_name="Minimum Value")
    max_value = models.FloatField(null=True, blank=True, verbose_name="Maximum Value")
    unit = models.CharField(max_length=20, blank=True, verbose_name="Unit (e.g., kPa, LPM)")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    requires_comment_if_nok = models.BooleanField(default=True, verbose_name="Require comment if NOK/No")
    
    class Meta:
        ordering = ['model_name', 'order']
        unique_together = ['model_name', 'parameter_name']
    
    def __str__(self):
        return f"{self.model_name} - {self.parameter_name}"


# Signal to create frequency config for new models
@receiver(post_save, sender=ChecklistBase)
def create_frequency_config(sender, instance, created, **kwargs):
    if created and instance.selected_model:
        SubgroupFrequencyConfig.objects.get_or_create(
            model_name=instance.selected_model,
            defaults={
                'frequency_hours': 2,
                'max_subgroups': 6
            }
        )




 
class ChecklistDynamicValue(models.Model):
    """Store values for dynamically configured checklist parameters"""
    checklist = models.ForeignKey(ChecklistBase, on_delete=models.CASCADE, related_name='dynamic_values')
    parameter = models.ForeignKey(ChecksheetContentConfig, on_delete=models.CASCADE)
    value = models.CharField(max_length=200)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['checklist', 'parameter']
    @property
    def is_out_of_range(self):
        """Check if numeric value is out of range"""
        if self.parameter.measurement_type == 'numeric' and self.parameter.min_value and self.parameter.max_value:
            try:
                num_value = float(self.value)
                return not (self.parameter.min_value <= num_value <= self.parameter.max_value)
            except (ValueError, TypeError):
                return False
        return False
    
    @property
    def is_nok(self):
        """Check if value is NOK or No"""
        return self.value in ['NOK', 'No']

    def __str__(self):
        return f"{self.checklist} - {self.parameter.parameter_name}: {self.value}"

 

class FTQRecord(models.Model):
    """First Time Quality records"""
    MODEL_CHOICES = (
        ('P703', 'P703'),
        ('U704', 'U704'),
        ('FD', 'FD'),
        ('SA', 'SA'),
        ('Gnome', 'Gnome'),
    )
    
    SHIFT_CHOICES = (
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    )
    SHIFTS = [
    ('S1', 'S1 - 6:30 AM to 6:30 PM'),
    ('A', 'A - 6:30 AM to 3:00 PM'),
    ('G', 'G - 8:30 AM to 5:00 PM'),
    ('B', 'B - 3:00 PM to 11:30 PM'),
    ('C', 'C - 11:30 PM to 6:30 AM'),
    ('S2', 'S2 - 6:30 PM to 6:30 AM'),
]

    # Link to DailyVerificationStatus instead of directly to Shift
    verification_status = models.ForeignKey(DailyVerificationStatus, on_delete=models.CASCADE, related_name='ftq_records', null=True, blank=True)
    date = models.DateField()
    shift_type = models.CharField(max_length=100, choices=SHIFTS,blank=True,null=True)
    model_name = models.CharField(max_length=10, choices=MODEL_CHOICES)
    julian_date = models.DateField(help_text="Date in Julian calendar")
    
    total_inspected = models.PositiveIntegerField(verbose_name="Production/day")
    total_defects = models.PositiveIntegerField(verbose_name="Total Reject", default=0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_ftq_records')
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='verified_ftq_records',
        null=True,
        blank=True,
        verbose_name="Supervisor"
    )
    production_per_shift = models.PositiveIntegerField(verbose_name="Production Data/Shift",blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def ftq_percentage(self):
        """Calculate FTQ percentage"""
        if self.total_inspected > 0:
            return ((self.total_inspected - self.total_defects) / self.total_inspected) * 100
        return 0
    
    @property
    def calculate_total_defects(self):
        """Calculate total defects by summing all defect records"""
        return self.defect_records.aggregate(total=models.Sum('count'))['total'] or 0
    
    def save(self, *args, **kwargs):
        """Update total_defects when saving"""
        # Only update if it's an existing record
        if self.pk:
            self.total_defects = self.calculate_total_defects
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.date} - {self.shift_type} - {self.model_name}: {self.ftq_percentage:.2f}%"
    
    class Meta:
        # Removed unique_together constraint
        pass


# Signal handlers for notifications

@receiver(post_save, sender=ChecklistBase)
def notify_supervisors(sender, instance, created, **kwargs):
    """Notify supervisors when a checklist is created or updated"""
    if created:
        # Mark verification status as in progress
        verification_status = instance.verification_status
        verification_status.status = 'in_progress'
        verification_status.supervisor_notified = True
        verification_status.save()


@receiver(post_save, sender=SubgroupVerification)
def notify_quality_supervisors(sender, instance, created, **kwargs):
    """Notify quality supervisors when a subgroup is verified by supervisor"""
    if created and instance.verifier_type == 'supervisor' and instance.status == 'supervisor_verified':
        # Get the verification status through the checklist
        verification_status = instance.subgroup.checklist.verification_status
        verification_status.quality_notified = True
        verification_status.save()


@receiver(post_save, sender=Verification)
def complete_verification_status(sender, instance, created, **kwargs):
    """Mark verification status as completed when all verifications are done"""
    if created:
        verification_status = instance.checklist.verification_status
        verification_status.status = 'completed'
        verification_status.save()

class OperationNumber(models.Model):
    """Operation numbers for the manufacturing process"""
    number = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.number} - {self.name}"

class DefectCategory(models.Model):
    """Categories of defects, such as 'Incorrect parts', 'Damage', etc."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Defect Categories"

class DefectType(models.Model):
    """Define types of defects that can be tracked"""
    name = models.CharField(max_length=100)
    operation_number = models.ForeignKey(OperationNumber, on_delete=models.CASCADE, related_name='defect_types')
    category = models.ForeignKey(DefectCategory, on_delete=models.CASCADE, related_name='defect_types')
    description = models.TextField(blank=True, null=True)
    is_critical = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False, help_text="If true, this defect type will be shown by default")
    order = models.PositiveIntegerField(default=0, help_text="Order in which to display this defect type")
    
    def __str__(self):
        return f"{self.operation_number.number} - {self.name}"
    
    class Meta:
        ordering = ['operation_number', 'order', 'name']

class DefectRecord(models.Model):
    """Record specific defects found during a shift"""
    ftq_record = models.ForeignKey('FTQRecord', on_delete=models.CASCADE, related_name='defect_records')
    defect_type = models.ForeignKey('DefectType', on_delete=models.CASCADE, null=True, blank=True)
    defect_type_custom = models.ForeignKey('CustomDefectType', on_delete=models.CASCADE, null=True, blank=True)
    count = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        if self.defect_type:
            return f"{self.defect_type.name} ({self.count}) - {self.ftq_record.date}"
        elif self.defect_type_custom:
            return f"{self.defect_type_custom.name} ({self.count}) - {self.ftq_record.date}"
        return f"Defect record ({self.count}) - {self.ftq_record.date}"
        
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(defect_type__isnull=False, defect_type_custom__isnull=True) |
                    models.Q(defect_type__isnull=True, defect_type_custom__isnull=False)
                ),
                name='exactly_one_defect_type'
            )
        ]
            
class CustomDefectType(models.Model):
    """Custom defect types that can be added by operators"""
    ftq_record = models.ForeignKey('FTQRecord', on_delete=models.CASCADE, related_name='custom_defect_types')
    name = models.CharField(max_length=200)
    operation_number = models.ForeignKey('OperationNumber', on_delete=models.CASCADE, related_name='custom_defect_types')
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.operation_number.number} - {self.name} (Custom)"
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
#  Not in use  extra ### 
from django.db import models
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime, timedelta

class DTPMChecklistFMA03(models.Model):
    """Daily Tracking and Performance Monitoring Checklist for FMA03 Operation 35"""
    
    SHIFT_CHOICES = (
        ('A', 'A Shift'),
        ('B', 'B Shift'),
        ('C', 'C Shift'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    # Basic information
    date = models.DateField(blank=True,null=True)
    shift = models.ForeignKey('Shift', on_delete=models.CASCADE, related_name='dtpm_checklists',blank=True,null=True)
    
    # Header image
    header_image = models.ImageField(
        upload_to='dtpm/header_images/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text="Main header image for the DTPM sheet"
    )
    
    # Personnel
    operator = models.ForeignKey('User', on_delete=models.CASCADE, related_name='operated_dtpm_checklists')
    supervisor = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='supervised_dtpm_checklists',
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Additional notes
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['date', 'shift']
        verbose_name = "DTPM Checklist"
        verbose_name_plural = "DTPM Checklists"
    
    def __str__(self):
        return f"DTPM Checklist - {self.date} - {self.shift}"


class DTPMCheckResult(models.Model):
    """Results for each of the 7 fixed check items"""
    
    OK_NG_CHOICES = [('OK', 'OK'), ('NG', 'NG')]
    
    # Fixed check items
    CHECK_ITEMS = [
        (1, "EMERGENCY push button is Working Properly"),
        (2, "There should not be any air leakage & Lubrication unit mounting should not be loose and no oil spillage"),
        (3, "All nuts and bolts should not be loose or free"),
        (4, "Check all sensors for damage or looseness"),
        (5, "Tower lamp & Tube light should be working properly"),
        (6, "All indicators & push buttons should be working properly"),
        (7, "Check Safety curtain working properly"),
    ]
    
    # Relations
    checklist = models.ForeignKey(DTPMChecklistFMA03, on_delete=models.CASCADE, related_name='check_results')
    
    # Item identification - using a fixed list rather than a separate model
    item_number = models.PositiveSmallIntegerField(choices=CHECK_ITEMS)
    
    # Result
    result = models.CharField(max_length=2, choices=OK_NG_CHOICES)
    
    # Image for this specific check result
    image = models.ImageField(
        upload_to='dtpm/check_images/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text="Image showing the condition during check"
    )
    
    # Comments and tracking
    comments = models.TextField(blank=True, null=True)
    checked_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='dtpm_checks_performed')
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['checklist', 'item_number']
        ordering = ['checklist', 'item_number']
    
    def __str__(self):
        return f"{self.checklist} - Item #{self.item_number}: {self.get_item_number_display()} - {self.result}"


class DTPMIssue(models.Model):
    """Issues identified during DTPM checks"""
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    )
    
    # Relations
    check_result = models.ForeignKey(DTPMCheckResult, on_delete=models.CASCADE, related_name='issues')
    
    # Issue details
    description = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='medium'
    )
    
    # Issue status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    reported_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='reported_dtpm_issues')
    assigned_to = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='assigned_dtpm_issues',
        null=True,
        blank=True
    )
    
    # Resolution
    action_taken = models.TextField(blank=True, null=True)
    resolution_date = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='resolved_dtpm_issues',
        null=True,
        blank=True
    )
    
    # Additional image for issue
    issue_image = models.ImageField(
        upload_to='dtpm/issue_images/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    
    # Resolution image
    resolution_image = models.ImageField(
        upload_to='dtpm/resolution_images/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Issue: Item #{self.check_result.item_number} - {self.status}"


# Signal to automatically create the 7 check results when a new checklist is created
@receiver(post_save, sender=DTPMChecklistFMA03)
def create_check_results(sender, instance, created, **kwargs):
    """Create the 7 standard check results when a new checklist is created"""
    if created:
        # Create a check result for each of the 7 fixed items
        for item_number, _ in DTPMCheckResult.CHECK_ITEMS:
            DTPMCheckResult.objects.create(
                checklist=instance,
                item_number=item_number,
                result='',  # Empty result by default
                checked_by=instance.operator  # Default to the operator who created the checklist
            )
            
            
            
            
            
            
            
            
            
            
            
#  new code for another sheet
            
            
from django.db import models

class ErrorPreventionCheck(models.Model):
    """Daily Error Prevention Checks tracking EP mechanism status across shifts"""

    # Status choices
    OK_NG_CHOICES = [('OK', 'OK'), ('NG', 'NG')]
    
    # EP Mechanism ID choices - these are the 10 checkpoints
    EP_MECHANISM_CHOICES = [
        ('FMA-03-35-M01_T6', 'FMA-03-35-M01(T6) / FMA-03-35-M09(Gnome)'),
        ('FMA-03-35-M02', 'FMA-03-35-M02 (T6/Gnome)'),
        ('FMA-03-35-M03', 'FMA-03-35-M03 (T6) / FMA-03-35-M10 (Gnome)'),
        ('FMA-03-35-M04', 'FMA-03-35-M04 (T6) / FMA-03-35-M11 (Gnome)'),
        ('FMA-03-35-M05', 'FMA-03-35-M05 (T6) / FMA-03-35-M12 (Gnome)'),
        ('FMA-03-35-M06', 'FMA-03-35-M06 (T6/Gnome)'),
        ('FMA-03-35-M07', 'FMA-03-35-M07 (T6/Gnome)'),
        ('FMA-03-35-M08', 'FMA-03-35-M08 (T6) / FMA-03-35-M13(Gnome)'),
    ]

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('quality_approved', 'Quality Approved'),
        ('rejected', 'Rejected'),
    )

    # Link to verification status instead of directly to shift
    verification_status = models.ForeignKey(
        'DailyVerificationStatus', 
        on_delete=models.CASCADE, 
        related_name='error_prevention_checks',
        blank=True,
        null=True
    )
    
    date = models.DateField()
    
    # Personnel
    operator = models.ForeignKey('User', on_delete=models.CASCADE, related_name='ep_operator_checks')
    supervisor = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='ep_supervisor_checks',
        blank=True,
        null=True
    )
    quality_supervisor = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='ep_quality_checks',
        blank=True,
        null=True
    )
    
    # Overall status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True, null=True)
    
    # Current running model - will be auto-populated from ChecklistBase
    current_model = models.CharField(
        max_length=10, 
        choices=[('P703', 'P703'),
        ('U704', 'U704'),
        ('FD', 'FD'),
        ('SA', 'SA'),
        ('Gnome', 'Gnome'),],
        verbose_name="Current Running Model",
        blank=True,
        null=True
    )
    
    # Shift - will be auto-populated from ChecklistBase
    shift = models.CharField(
        max_length=10,
        choices=ChecklistBase.SHIFTS,
        verbose_name="Shift",
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Auto-populate model and shift from related ChecklistBase and track changes"""
        # Store original values for history tracking
        original_instance = None
        if self.pk:
            original_instance = ErrorPreventionCheck.objects.get(pk=self.pk)
        
        # Auto-populate model and shift from checklist
        if self.verification_status:
            checklist = self.verification_status.checklists.first()
            if checklist:
                if not self.current_model:
                    self.current_model = checklist.selected_model
                if not self.shift:
                    self.shift = checklist.shift
        
        super().save(*args, **kwargs)
        
        # Create history entry if this is an update
        if original_instance:
            from .history_utils import track_ep_check_changes
            track_ep_check_changes(original_instance, self, kwargs.get('user'))
    
    @property
    def get_model_from_checklist(self):
        """Get model from associated ChecklistBase"""
        if self.verification_status:
            checklist = self.verification_status.checklists.first()
            return checklist.selected_model if checklist else None
        return None
    
    @property
    def get_shift_from_checklist(self):
        """Get shift from associated ChecklistBase"""
        if self.verification_status:
            checklist = self.verification_status.checklists.first()
            return checklist.shift if checklist else None
        return None
    
    @property
    def latest_changes(self):
        """Get the most recent 5 changes"""
        return self.history.all()[:5]
    
    @property
    def has_changes_today(self):
        """Check if there were any changes today"""
        today = timezone.now().date()
        return self.history.filter(timestamp__date=today).exists()
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Error Prevention Check"
        verbose_name_plural = "Error Prevention Checks"
    
    def __str__(self):
        shift_display = self.shift or "No Shift"
        if self.verification_status and self.verification_status.shift:
            shift_display = self.verification_status.shift.get_shift_type_display()
        return f"EP Check - {self.date} - {shift_display}"

class ErrorPreventionMechanismStatus(models.Model):
    """Status for each EP mechanism in a daily check"""
    
    OK_NG_CHOICES = [('OK', 'OK'), ('NG', 'NG')]
    
    # Relations
    ep_check = models.ForeignKey(
        ErrorPreventionCheck, 
        on_delete=models.CASCADE, 
        related_name='mechanism_statuses'
    )
    
    # EP Mechanism details
    ep_mechanism_id = models.CharField(
        max_length=50, 
        choices=ErrorPreventionCheck.EP_MECHANISM_CHOICES,
        verbose_name="EP Mechanism ID"
    )
    
    # Status fields
    is_working = models.BooleanField(default=True, verbose_name="Working")
    alternative_method = models.CharField(
        max_length=100, 
        default="100% Inspection By Operator",
        verbose_name="Alternative Method"
    )
    status = models.CharField(
        max_length=2, 
        choices=OK_NG_CHOICES, 
        verbose_name="Status"
    )
    is_not_applicable = models.BooleanField(default=False, verbose_name="N/A")
    
    # Comments
    comments = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        """Track changes when mechanism status is updated"""
        # Extract user from kwargs for history tracking
        user = kwargs.pop('user', None)
        
        # Store original values for history tracking (only for existing records)
        original_instance = None
        is_new_record = not self.pk
        
        if self.pk:  # Only track changes for existing records, not new ones
            original_instance = ErrorPreventionMechanismStatus.objects.get(pk=self.pk)
        
        super().save(*args, **kwargs)
        
        # Create history entries for changes only if:
        # 1. User is provided
        # 2. This is not a new record (original_instance exists)
        # 3. There are actual changes
        if original_instance and user and not is_new_record:
            from .history_utils import track_mechanism_changes
            track_mechanism_changes(original_instance, self, user)
    
    @property
    def status_display_with_history(self):
        """Get status with change indicator"""
        recent_changes = self.history.filter(field_name='status')[:1]
        if recent_changes:
            latest_change = recent_changes[0]
            if latest_change.old_value != latest_change.new_value:
                return f"{self.status} (was {latest_change.old_value})"
        return self.status
    
    class Meta:
        ordering = ['ep_mechanism_id']
    
    def __str__(self):
        return f"{self.ep_mechanism_id} - {self.ep_check.date} - {self.status}"    
    
class ErrorPreventionCheckHistory(models.Model):
    """Track changes made to EP checks"""
    
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('status_changed', 'Status Changed'),
        ('supervisor_verified', 'Supervisor Verified'),
        ('quality_verified', 'Quality Verified'),
        ('rejected', 'Rejected'),
    ]
    
    ep_check = models.ForeignKey(
        'ErrorPreventionCheck', 
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    # Who made the change
    changed_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='ep_check_changes'
    )
    
    # What type of change
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Field-specific changes
    field_name = models.CharField(max_length=100, blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    
    # General change description
    description = models.TextField(blank=True, null=True)
    
    # Additional data (JSON field for complex changes)
    additional_data = models.JSONField(default=dict, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "EP Check History"
        verbose_name_plural = "EP Check Histories"
    
    def __str__(self):
        return f"{self.ep_check} - {self.action} by {self.changed_by.username} at {self.timestamp}"

class ErrorPreventionMechanismHistory(models.Model):
    """Track changes made to individual mechanism statuses"""
    
    mechanism_status = models.ForeignKey(
        'ErrorPreventionMechanismStatus',
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    # Who made the change
    changed_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='mechanism_changes'
    )
    
    # What changed
    field_name = models.CharField(max_length=50)  # 'status', 'is_working', 'comments', etc.
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Mechanism Status History"
        verbose_name_plural = "Mechanism Status Histories"
    
    def __str__(self):
        return f"{self.mechanism_status.ep_mechanism_id} - {self.field_name} changed by {self.changed_by.username}"

# Utility function to create history entries
def create_ep_check_history(ep_check, user, action, field_name=None, old_value=None, new_value=None, description=None):
    """Helper function to create history entries"""
    return ErrorPreventionCheckHistory.objects.create(
        ep_check=ep_check,
        changed_by=user,
        action=action,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        description=description
    )

def create_mechanism_history(mechanism_status, user, field_name, old_value, new_value):
    """Helper function to create mechanism history entries"""
    return ErrorPreventionMechanismHistory.objects.create(
        mechanism_status=mechanism_status,
        changed_by=user,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None
    )    
    
    
    
# new codee dtpm new one 
from django.db import models
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

class DTPMChecklistFMA03New(models.Model):
    """Daily Tracking and Performance Monitoring Checklist for FMA03 Operation 35"""
    
    # Status choices
    OK_NG_CHOICES = [('OK', 'OK'), ('NG', 'NG')]
    
    # Checkpoint choices - these are the 7 fixed checkpoints
    CHECKPOINT_CHOICES = [
        (1, "EMERGENCY push button is Working Properly"),
        (2, "There should not be any air leakage & Lubrication unit mounting should not be loose and no oil spillage"),
        (3, "All nuts and bolts should not be loose or free"),
        (4, "Check all sensors for damage or looseness"),
        (5, "Tower lamp & Tube light should be working properly"),
        (6, "All indicators & push buttons should be working properly"),
        (7, "Check Safety curtain working properly"),
    ]
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    # Basic information
    date = models.DateField()
    shift = models.ForeignKey('Shift', on_delete=models.CASCADE, related_name='dtpm_checklists_new')
    
    # Link to verification status for consistency with other forms
    verification_status = models.ForeignKey(
        'DailyVerificationStatus', 
        on_delete=models.CASCADE, 
        related_name='dtpm_checklists',
        blank=True,
        null=True
    )
    
    # Personnel
    operator = models.ForeignKey('User', on_delete=models.CASCADE, related_name='operated_dtpm_checklists_new')
    supervisor = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='supervised_dtpm_checklists_new',
        null=True,
        blank=True
    )
    
    # Overall status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Additional notes
    notes = models.TextField(blank=True, null=True)
    
    # Auto-populated fields from ChecklistBase
    current_model = models.CharField(
        max_length=10, 
        choices=[('P703', 'P703'),
        ('U704', 'U704'),
        ('FD', 'FD'),
        ('SA', 'SA'),
        ('Gnome', 'Gnome'),],
        verbose_name="Current Running Model",
        blank=True,
        null=True
    )
    
    # Shift from checklist - will be auto-populated from ChecklistBase
    checklist_shift = models.CharField(
        max_length=10,
        choices=ChecklistBase.SHIFTS,
        verbose_name="Shift from Checklist",
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for two-stage verification
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    supervisor_approved_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, 
                                              related_name='dtpm_supervisor_approvals')
    
    quality_certified_at = models.DateTimeField(null=True, blank=True)
    quality_certified_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='dtpm_quality_certifications')
    quality_comments = models.TextField(blank=True, null=True)
    
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='dtpm_rejections')
    
    quality_rejected_at = models.DateTimeField(null=True, blank=True)
    quality_rejected_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='dtpm_quality_rejections')

    def save(self, *args, **kwargs):
        """Auto-populate model and shift from related ChecklistBase"""
        if self.verification_status:
            # Get the checklist from the same verification status
            checklist = self.verification_status.checklists.first()
            if checklist:
                # Auto-populate model and shift from checklist
                if not self.current_model:
                    self.current_model = checklist.selected_model
                if not self.checklist_shift:
                    self.checklist_shift = checklist.shift
        
        super().save(*args, **kwargs)
    
    @property
    def get_model_from_checklist(self):
        """Get model from associated ChecklistBase"""
        if self.verification_status:
            checklist = self.verification_status.checklists.first()
            return checklist.selected_model if checklist else None
        return None
    
    @property
    def get_shift_from_checklist(self):
        """Get shift from associated ChecklistBase"""
        if self.verification_status:
            checklist = self.verification_status.checklists.first()
            return checklist.shift if checklist else None
        return None

    class Meta:
        ordering = ['-date']
        unique_together = ['date', 'shift']
        verbose_name = "DTPM Checklist"
        verbose_name_plural = "DTPM Checklists"
    
    def __str__(self):
        shift_display = self.checklist_shift or "No Shift"
        if self.shift:
            shift_display = self.shift.get_shift_type_display()
        return f"DTPM Checklist - {self.date} - {shift_display}"
    
    def get_status_display_with_icon(self):
        """Return status with appropriate icon for templates"""
        status_icons = {
            'pending': '<i class="fas fa-clock text-warning"></i>',
            'supervisor_approved': '<i class="fas fa-user-check text-info"></i>',
            'quality_certified': '<i class="fas fa-certificate text-success"></i>',
            'rejected': '<i class="fas fa-times-circle text-danger"></i>',
            'quality_rejected': '<i class="fas fa-ban text-danger"></i>',
        }
        return f"{status_icons.get(self.status, '')} {self.get_status_display()}"
    
    @property
    def is_fully_completed(self):
        """Check if checklist is fully completed (quality certified)"""
        return self.status == 'quality_certified'
    
    @property
    def is_supervisor_approved(self):
        """Check if checklist is supervisor approved"""
        return self.status in ['supervisor_approved', 'quality_certified']


   
class DTPMVerificationHistory(models.Model):
    VERIFICATION_TYPES = [
        ('supervisor_approve', 'Supervisor Approved'),
        ('supervisor_reject', 'Supervisor Rejected'),
        ('quality_certify', 'Quality Certified'),
        ('quality_reject', 'Quality Rejected'),
    ]
    
    checklist = models.ForeignKey(DTPMChecklistFMA03New, on_delete=models.CASCADE, 
                                 related_name='verification_history')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    verified_by = models.ForeignKey('User', on_delete=models.CASCADE)
    verified_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'dtpm_verification_history'
        ordering = ['-verified_at']
    
    def __str__(self):
        return f"{self.get_verification_type_display()} - {self.verified_by.username} - {self.verified_at}"



class DTPMCheckResultNew(models.Model):
    """Results for each checkpoint in a DTPM checklist"""
    
    OK_NG_CHOICES = [('OK', 'OK'), ('NG', 'NG')]
    
    # Relations
    checklist = models.ForeignKey(
        DTPMChecklistFMA03New, 
        on_delete=models.CASCADE, 
        related_name='check_results'
    )
    
    # Checkpoint details - using the fixed list from parent model
    checkpoint_number = models.PositiveSmallIntegerField(
        choices=DTPMChecklistFMA03New.CHECKPOINT_CHOICES,
        verbose_name="Checkpoint"
    )
    
    # Status - only field operators can change
    status = models.CharField(
        max_length=2, 
        choices=OK_NG_CHOICES, 
        verbose_name="Status",
        default='NG'  # Set default to NG
    )
    
    # Comments
    comments = models.TextField(blank=True, null=True)
    
    # Timestamps
    checked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['checklist', 'checkpoint_number']
        ordering = ['checkpoint_number']
    
    def __str__(self):
        return f"{self.checklist} - Checkpoint #{self.checkpoint_number}: {self.status}"


class DTPMIssueNew(models.Model):
    """Issues identified during DTPM checks"""
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    )
    
    # Relations
    check_result = models.ForeignKey(
        DTPMCheckResultNew, 
        on_delete=models.CASCADE, 
        related_name='issues'
    )
    
    # Issue details
    description = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='medium'
    )
    
    # Issue status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    reported_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='reported_dtpm_issues_new')
    assigned_to = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='assigned_dtpm_issues_new',
        null=True,
        blank=True
    )
    
    # Resolution
    action_taken = models.TextField(blank=True, null=True)
    resolution_date = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='resolved_dtpm_issues_new',
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Issue: Checkpoint #{self.check_result.checkpoint_number} - {self.status}"

# Signal to automatically create checkpoint results when a new DTPM checklist is created
@receiver(post_save, sender=DTPMChecklistFMA03New)
def create_check_results(sender, instance, created, **kwargs):
    """Create the 7 standard check results when a new checklist is created"""
    if created:
        # Create a check result for each of the 7 fixed checkpoints
        for checkpoint_number, _ in DTPMChecklistFMA03New.CHECKPOINT_CHOICES:
            DTPMCheckResultNew.objects.create(
                checklist=instance,
                checkpoint_number=checkpoint_number,
                status='NG'  # Default status
            )