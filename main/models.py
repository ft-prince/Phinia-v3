from django.conf import settings
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
    # master_verification_lvdt = models.CharField(
    #     max_length=3,
    #     choices=OK_NG_CHOICES,
    #     verbose_name="Master Verification for LVDT"
    # )
    
    # good_bad_master_verification = models.CharField(
    #     max_length=3,
    #     choices=OK_NG_CHOICES,
    #     verbose_name="Good and Bad master verification (refer EPVS)"
    # )
    
    
    test_pressure_vacuum = models.FloatField(
        help_text="Recommended Range: 0.25 - 0.3 MPa",
        verbose_name="Test Pressure for Vacuum generation"
    )
    
    # tool_alignment = models.CharField(
    #     max_length=3,
    #     choices=OK_NG_CHOICES,
    #     verbose_name="Tool Alignment (Top & Bottom) (Tool Alignment) सही होना चाहिए"
    # )
    
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
    
    # error_proofing_verification = models.CharField(
    #     max_length=3,
    #     choices=YES_NO_CHOICES,
    #     verbose_name="All Error proofing / Error detection verification done"
    # )
    
    
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

 
 
class SubgroupCategoryFrequencyConfig(models.Model):
    """Configuration for timing/frequency of each subgroup category"""
    CATEGORY_CHOICES = [
        ('uv_vacuum_test', 'UV Vacuum Test'),
        ('uv_flow_value', 'UV Flow Value'),
        ('umbrella_valve_assembly', 'Umbrella Valve Assembly'),
        ('uv_clip_pressing', 'UV Clip Pressing'),
        ('workstation_cleanliness', 'Workstation Cleanliness'),
        ('bin_contamination_check', 'Bin Contamination Check'),
    ]
    
    MODEL_CHOICES = (
        ('P703', 'P703'),
        ('U704', 'U704'),
        ('FD', 'FD'),
        ('SA', 'SA'),
        ('Gnome', 'Gnome'),
    )
    
    model_name = models.CharField(max_length=10, choices=MODEL_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    frequency_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Frequency in minutes (e.g., 60 = every hour, 120 = every 2 hours)"
    )
    max_readings_per_shift = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of readings for this category per shift"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['model_name', 'category']
        verbose_name = 'Subgroup Category Frequency Config'
        verbose_name_plural = 'Subgroup Category Frequency Configs'
        ordering = ['model_name', 'category']
    
    def __str__(self):
        return f"{self.model_name} - {self.get_category_display()} - Every {self.frequency_minutes}min"
    
    @property
    def frequency_hours(self):
        """Convert frequency from minutes to hours for display"""
        return self.frequency_minutes / 60


class SubgroupCategoryTiming(models.Model):
    """Track timing for each category reading"""
    checklist = models.ForeignKey(ChecklistBase, on_delete=models.CASCADE, related_name='category_timings')
    category = models.CharField(max_length=30, choices=SubgroupCategoryFrequencyConfig.CATEGORY_CHOICES)
    last_reading_time = models.DateTimeField()
    next_reading_due = models.DateTimeField()
    frequency_config = models.ForeignKey(SubgroupCategoryFrequencyConfig, on_delete=models.CASCADE)
    readings_count = models.PositiveIntegerField(default=0)
    is_overdue = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['checklist', 'category']
        ordering = ['next_reading_due']
        verbose_name = 'Subgroup Category Timing'
        verbose_name_plural = 'Subgroup Category Timings'
    
    def __str__(self):
        return f"{self.checklist} - {self.get_category_display()} - Due: {self.next_reading_due}"
    
    def update_next_due_time(self):
        """Update the next due time based on frequency config"""
        from datetime import timedelta
        self.next_reading_due = self.last_reading_time + timedelta(minutes=self.frequency_config.frequency_minutes)
        self.is_overdue = timezone.now() > self.next_reading_due
        self.save()

 

 


 
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
    
    
    # UV Vacuum Test Comments (5)
    uv_vacuum_test_1_comment = models.TextField(blank=True, null=True, verbose_name="UV Vacuum Test 1 Comment")
    uv_vacuum_test_2_comment = models.TextField(blank=True, null=True, verbose_name="UV Vacuum Test 2 Comment")
    uv_vacuum_test_3_comment = models.TextField(blank=True, null=True, verbose_name="UV Vacuum Test 3 Comment")
    uv_vacuum_test_4_comment = models.TextField(blank=True, null=True, verbose_name="UV Vacuum Test 4 Comment")
    uv_vacuum_test_5_comment = models.TextField(blank=True, null=True, verbose_name="UV Vacuum Test 5 Comment")
    
    # UV Flow Value Comments (5)
    uv_flow_value_1_comment = models.TextField(blank=True, null=True, verbose_name="UV Flow Value 1 Comment")
    uv_flow_value_2_comment = models.TextField(blank=True, null=True, verbose_name="UV Flow Value 2 Comment")
    uv_flow_value_3_comment = models.TextField(blank=True, null=True, verbose_name="UV Flow Value 3 Comment")
    uv_flow_value_4_comment = models.TextField(blank=True, null=True, verbose_name="UV Flow Value 4 Comment")
    uv_flow_value_5_comment = models.TextField(blank=True, null=True, verbose_name="UV Flow Value 5 Comment")
    
    # Umbrella Valve Assembly Comments (5)
    umbrella_valve_assembly_1_comment = models.TextField(blank=True, null=True, verbose_name="Umbrella Valve 1 Comment")
    umbrella_valve_assembly_2_comment = models.TextField(blank=True, null=True, verbose_name="Umbrella Valve 2 Comment")
    umbrella_valve_assembly_3_comment = models.TextField(blank=True, null=True, verbose_name="Umbrella Valve 3 Comment")
    umbrella_valve_assembly_4_comment = models.TextField(blank=True, null=True, verbose_name="Umbrella Valve 4 Comment")
    umbrella_valve_assembly_5_comment = models.TextField(blank=True, null=True, verbose_name="Umbrella Valve 5 Comment")
    
    # UV Clip Pressing Comments (5)
    uv_clip_pressing_1_comment = models.TextField(blank=True, null=True, verbose_name="UV Clip Pressing 1 Comment")
    uv_clip_pressing_2_comment = models.TextField(blank=True, null=True, verbose_name="UV Clip Pressing 2 Comment")
    uv_clip_pressing_3_comment = models.TextField(blank=True, null=True, verbose_name="UV Clip Pressing 3 Comment")
    uv_clip_pressing_4_comment = models.TextField(blank=True, null=True, verbose_name="UV Clip Pressing 4 Comment")
    uv_clip_pressing_5_comment = models.TextField(blank=True, null=True, verbose_name="UV Clip Pressing 5 Comment")
    
    # Workstation Clean Comment (1)
    workstation_clean_comment = models.TextField(blank=True, null=True, verbose_name="Workstation Clean Comment")
    
    # Bin Contamination Check Comments (5)
    bin_contamination_check_1_comment = models.TextField(blank=True, null=True, verbose_name="Bin Contamination 1 Comment")
    bin_contamination_check_2_comment = models.TextField(blank=True, null=True, verbose_name="Bin Contamination 2 Comment")
    bin_contamination_check_3_comment = models.TextField(blank=True, null=True, verbose_name="Bin Contamination 3 Comment")
    bin_contamination_check_4_comment = models.TextField(blank=True, null=True, verbose_name="Bin Contamination 4 Comment")
    bin_contamination_check_5_comment = models.TextField(blank=True, null=True, verbose_name="Bin Contamination 5 Comment")

    
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
    
    
    
class SubgroupEntryNew(models.Model):
    """NEW MODEL - Enhanced subgroup measurements with category-specific timing"""
    VERIFICATION_STATUS_CHOICES = (
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )

    OK_NG_CHOICES = [('OK', 'OK'), ('NOK', 'NOK')]
    YES_NO_CHOICES = [('Yes', 'Yes'), ('NOK', 'NOK')]

    checklist = models.ForeignKey(ChecklistBase, on_delete=models.CASCADE, related_name='subgroups_new')
    subgroup_number = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # NEW FIELDS: Category tracking
    category = models.CharField(
        max_length=30,
        choices=SubgroupCategoryFrequencyConfig.CATEGORY_CHOICES,
        help_text="Which category this reading belongs to"
    )
    
    frequency_config = models.ForeignKey(
        SubgroupCategoryFrequencyConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Frequency configuration used for this reading"
    )
    
    # NEW FIELDS: Maintenance tracking
    is_after_maintenance = models.BooleanField(
        default=False,
        verbose_name="Is this reading after maintenance?",
        help_text="Check if this reading was taken after maintenance"
    )
    
    maintenance_comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Maintenance Comments",
        help_text="Comments about maintenance performed"
    )
    
    effectiveness_comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Effectiveness Comments",
        help_text="Comments about the effectiveness of the process"
    )
    
    # UV Vacuum Test measurements (5 readings) with comments
    uv_vacuum_test_1 = models.FloatField(null=True, blank=True, verbose_name="UV Vacuum Test 1 (mbar)")
    uv_vacuum_test_1_comment = models.TextField(blank=True, null=True)
    uv_vacuum_test_2 = models.FloatField(null=True, blank=True, verbose_name="UV Vacuum Test 2 (mbar)")
    uv_vacuum_test_2_comment = models.TextField(blank=True, null=True)
    uv_vacuum_test_3 = models.FloatField(null=True, blank=True, verbose_name="UV Vacuum Test 3 (mbar)")
    uv_vacuum_test_3_comment = models.TextField(blank=True, null=True)
    uv_vacuum_test_4 = models.FloatField(null=True, blank=True, verbose_name="UV Vacuum Test 4 (mbar)")
    uv_vacuum_test_4_comment = models.TextField(blank=True, null=True)
    uv_vacuum_test_5 = models.FloatField(null=True, blank=True, verbose_name="UV Vacuum Test 5 (mbar)")
    uv_vacuum_test_5_comment = models.TextField(blank=True, null=True)
    
    # UV Flow Value measurements (5 readings) with comments
    uv_flow_value_1 = models.FloatField(null=True, blank=True, verbose_name="UV Flow Value 1 (%)")
    uv_flow_value_1_comment = models.TextField(blank=True, null=True)
    uv_flow_value_2 = models.FloatField(null=True, blank=True, verbose_name="UV Flow Value 2 (%)")
    uv_flow_value_2_comment = models.TextField(blank=True, null=True)
    uv_flow_value_3 = models.FloatField(null=True, blank=True, verbose_name="UV Flow Value 3 (%)")
    uv_flow_value_3_comment = models.TextField(blank=True, null=True)
    uv_flow_value_4 = models.FloatField(null=True, blank=True, verbose_name="UV Flow Value 4 (%)")
    uv_flow_value_4_comment = models.TextField(blank=True, null=True)
    uv_flow_value_5 = models.FloatField(null=True, blank=True, verbose_name="UV Flow Value 5 (%)")
    uv_flow_value_5_comment = models.TextField(blank=True, null=True)
    
    # Umbrella Valve Assembly measurements (5 readings) with comments
    umbrella_valve_assembly_1 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    umbrella_valve_assembly_1_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_2 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    umbrella_valve_assembly_2_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_3 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    umbrella_valve_assembly_3_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_4 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    umbrella_valve_assembly_4_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_5 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    umbrella_valve_assembly_5_comment = models.TextField(blank=True, null=True)
    
    # UV Clip Pressing measurements (5 readings) with comments
    uv_clip_pressing_1 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    uv_clip_pressing_1_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_2 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    uv_clip_pressing_2_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_3 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    uv_clip_pressing_3_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_4 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    uv_clip_pressing_4_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_5 = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    uv_clip_pressing_5_comment = models.TextField(blank=True, null=True)
    
    # Work Station Cleanliness (single measurement) with comment
    workstation_clean = models.CharField(max_length=3, choices=OK_NG_CHOICES, null=True, blank=True)
    workstation_clean_comment = models.TextField(blank=True, null=True)
    
    # Bin Contamination Check measurements (5 readings) with comments
    bin_contamination_check_1 = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    bin_contamination_check_1_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_2 = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    bin_contamination_check_2_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_3 = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    bin_contamination_check_3_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_4 = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    bin_contamination_check_4_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_5 = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    bin_contamination_check_5_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        category_display = f" - {self.get_category_display()}" if self.category else ""
        return f"Subgroup NEW {self.subgroup_number}{category_display} - {self.checklist.selected_model}"

    class Meta:
        ordering = ['checklist', 'timestamp', 'subgroup_number']
        verbose_name = "Subgroup Entry (New with Category Timing)"
        verbose_name_plural = "Subgroup Entries (New with Category Timing)"

    # Helper methods for category-specific functionality
    def get_category_fields(self):
        """Get fields that belong to this entry's category"""
        category_fields = {
            'uv_vacuum_test': [
                self.uv_vacuum_test_1, self.uv_vacuum_test_2, self.uv_vacuum_test_3,
                self.uv_vacuum_test_4, self.uv_vacuum_test_5
            ],
            'uv_flow_value': [
                self.uv_flow_value_1, self.uv_flow_value_2, self.uv_flow_value_3,
                self.uv_flow_value_4, self.uv_flow_value_5
            ],
            'umbrella_valve_assembly': [
                self.umbrella_valve_assembly_1, self.umbrella_valve_assembly_2,
                self.umbrella_valve_assembly_3, self.umbrella_valve_assembly_4,
                self.umbrella_valve_assembly_5
            ],
            'uv_clip_pressing': [
                self.uv_clip_pressing_1, self.uv_clip_pressing_2,
                self.uv_clip_pressing_3, self.uv_clip_pressing_4,
                self.uv_clip_pressing_5
            ],
            'workstation_cleanliness': [self.workstation_clean],
            'bin_contamination_check': [
                self.bin_contamination_check_1, self.bin_contamination_check_2,
                self.bin_contamination_check_3, self.bin_contamination_check_4,
                self.bin_contamination_check_5
            ]
        }
        
        return category_fields.get(self.category, [])
    
    @property
    def category_completion_percentage(self):
        """Get completion percentage for this category"""
        fields = self.get_category_fields()
        if not fields:
            return 0
        
        filled_fields = [f for f in fields if f is not None and f != '']
        return (len(filled_fields) / len(fields)) * 100
    
    @property
    def is_category_complete(self):
        """Check if this category is completely filled"""
        return self.category_completion_percentage == 100
    
    @property
    def uv_vacuum_average(self):
        readings = [self.uv_vacuum_test_1, self.uv_vacuum_test_2, self.uv_vacuum_test_3, 
                   self.uv_vacuum_test_4, self.uv_vacuum_test_5]
        valid_readings = [r for r in readings if r is not None]
        return sum(valid_readings) / len(valid_readings) if valid_readings else 0
    
    @property
    def uv_flow_average(self):
        readings = [self.uv_flow_value_1, self.uv_flow_value_2, self.uv_flow_value_3, 
                   self.uv_flow_value_4, self.uv_flow_value_5]
        valid_readings = [r for r in readings if r is not None]
        return sum(valid_readings) / len(valid_readings) if valid_readings else 0

    
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



# NEW MODEL: Verification for the new subgroup entries
class SubgroupVerificationNew(models.Model):
    """Verification records for new subgroup entries"""
    VERIFIER_TYPES = (
        ('supervisor', 'Shift Supervisor'),
        ('quality', 'Quality Supervisor'),
    )
    
    subgroup = models.ForeignKey(SubgroupEntryNew, on_delete=models.CASCADE, related_name='verifications')
    verified_by = models.ForeignKey(User, on_delete=models.CASCADE)
    verifier_type = models.CharField(max_length=20, choices=VERIFIER_TYPES)
    verified_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=SubgroupEntryNew.VERIFICATION_STATUS_CHOICES)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['verified_at']
        verbose_name = "Subgroup Verification (New)"
        verbose_name_plural = "Subgroup Verifications (New)"


class SubgroupEditHistory(models.Model):
    subgroup = models.ForeignKey(SubgroupEntry, on_delete=models.CASCADE, related_name='edit_history')
    edited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    edited_at = models.DateTimeField(auto_now_add=True)
    field_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=200, null=True, blank=True)
    new_value = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        ordering = ['-edited_at']




class DefectCategory(models.Model):
    """Categories of defects, such as 'Incorrect parts', 'Damage', etc."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Defect Categories"



# Helper functions for category timing management
def get_next_due_category(checklist):
    """Get the next category that needs readings"""
    category_timings = SubgroupCategoryTiming.objects.filter(
        checklist=checklist,
        next_reading_due__lte=timezone.now()
    ).order_by('next_reading_due').first()
    
    return category_timings.category if category_timings else None


def create_category_timing_for_checklist(checklist):
    """Create initial timing records for all categories when checklist is created"""
    model_name = checklist.selected_model
    
    for category_code, category_name in SubgroupCategoryFrequencyConfig.CATEGORY_CHOICES:
        try:
            frequency_config = SubgroupCategoryFrequencyConfig.objects.get(
                model_name=model_name,
                category=category_code,
                is_active=True
            )
        except SubgroupCategoryFrequencyConfig.DoesNotExist:
            # Create default config if none exists
            frequency_config = SubgroupCategoryFrequencyConfig.objects.create(
                model_name=model_name,
                category=category_code,
                frequency_minutes=60,  # Default 1 hour
                max_readings_per_shift=5,
                is_active=True
            )
        
        from datetime import timedelta
        now = timezone.now()
        
        SubgroupCategoryTiming.objects.get_or_create(
            checklist=checklist,
            category=category_code,
            defaults={
                'last_reading_time': now,
                'next_reading_due': now + timedelta(minutes=frequency_config.frequency_minutes),
                'frequency_config': frequency_config,
                'readings_count': 0,
                'is_overdue': False
            }
        )


# Signals for automatic timing management
@receiver(post_save, sender=ChecklistBase)
def create_checklist_category_timings(sender, instance, created, **kwargs):
    """Automatically create category timing records when a new checklist is created"""
    if created:
        create_category_timing_for_checklist(instance)


@receiver(post_save, sender=SubgroupEntryNew)
def update_category_timing_on_reading(sender, instance, created, **kwargs):
    """Update category timing when a new reading is taken"""
    if created and instance.category:
        try:
            timing = SubgroupCategoryTiming.objects.get(
                checklist=instance.checklist,
                category=instance.category
            )
            
            timing.last_reading_time = instance.timestamp
            timing.readings_count += 1
            timing.update_next_due_time()
            
        except SubgroupCategoryTiming.DoesNotExist:
            # Create timing record if it doesn't exist
            create_category_timing_for_checklist(instance.checklist)


# Model for configurable checksheet content
class ChecksheetContentConfig(models.Model):
    """Configurable content for different models"""
    SECTION_CHOICES = [
        ('initial_setup', 'Initial Setup'),
        ('standard_measurements', 'Standard Measurements'),
        ('status_checks', 'Status Checks'),
        ('ids_part_numbers', 'IDs and Part Numbers'),
        ('model_specific', 'Model-Specific Parameters'),
    ]
    
    model_name = models.CharField(max_length=10, choices=ChecklistBase.MODEL_CHOICES)
    section = models.CharField(
        max_length=30, 
        choices=SECTION_CHOICES, 
        default='model_specific',
        verbose_name="Section",
        null=True
    )
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
    order = models.PositiveIntegerField(default=0, help_text="Display order within section")
    is_active = models.BooleanField(default=True)
    requires_comment_if_nok = models.BooleanField(default=True, verbose_name="Require comment if NOK/No")
    
    class Meta:
        ordering = ['model_name', 'section', 'order']
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

   
#  FTQ


from django.utils import timezone
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver


  
# Define these ONLY ONCE at the beginning
class OperationNumber(models.Model):
    """Operation numbers for the manufacturing process"""
    number = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.number} - {self.name}"


class DefectCategory(models.Model):
    """Categories of defects"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Defect Categories"


class FTQRecord(models.Model):
    """First Time Quality records"""
    MODEL_CHOICES = (
        ('P703', 'P703'),
        ('U704', 'U704'),
        ('FD', 'FD'),
        ('SA', 'SA'),
        ('Gnome', 'Gnome'),
    )
    
    SHIFTS = [
        ('S1', 'S1 - 6:30 AM to 6:30 PM'),
        ('A', 'A - 6:30 AM to 3:00 PM'),
        ('G', 'G - 8:30 AM to 5:00 PM'),
        ('B', 'B - 3:00 PM to 11:30 PM'),
        ('C', 'C - 11:30 PM to 6:30 AM'),
        ('S2', 'S2 - 6:30 PM to 6:30 AM'),
    ]

    verification_status = models.ForeignKey(
        'DailyVerificationStatus', 
        on_delete=models.CASCADE, 
        related_name='ftq_records', 
        null=True, 
        blank=True
    )
    date = models.DateField()
    shift_type = models.CharField(max_length=100, choices=SHIFTS, blank=True, null=True)
    model_name = models.CharField(max_length=10, choices=MODEL_CHOICES)
    julian_date = models.DateField(help_text="Date in Julian calendar")
    
    total_inspected = models.PositiveIntegerField(verbose_name="Production/day")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_ftq_records')
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='verified_ftq_records',
        null=True,
        blank=True,
        verbose_name="Supervisor"
    )
    production_per_shift = models.PositiveIntegerField(
        verbose_name="Production Data/Shift", 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_defects(self):
        """Calculate total defects by summing all time-based defect entries"""
        return self.time_based_defects.aggregate(
            total=Sum('count')
        )['total'] or 0
    
    @property
    def ftq_percentage(self):
        """Calculate FTQ percentage"""
        if self.total_inspected > 0:
            return ((self.total_inspected - self.total_defects) / self.total_inspected) * 100
        return 0
    
    def __str__(self):
        return f"{self.date} - {self.shift_type} - {self.model_name}: {self.ftq_percentage:.2f}%"
    
    class Meta:
        ordering = ['-date', '-created_at']
# Signal handlers for notifications



class DefectType(models.Model):
    """Define types of defects that can be tracked"""
    name = models.CharField(max_length=100)
    operation_number = models.ForeignKey(
        OperationNumber,  # Reference the class defined above
        on_delete=models.CASCADE, 
        related_name='defect_types'
    )
    category = models.ForeignKey(
        DefectCategory,  # Reference the class defined above
        on_delete=models.CASCADE, 
        related_name='defect_types'
    )
    description = models.TextField(blank=True, null=True)
    is_critical = models.BooleanField(default=False)
    is_default = models.BooleanField(
        default=False, 
        help_text="If true, this defect type will be shown by default"
    )
    order = models.PositiveIntegerField(
        default=0, 
        help_text="Order in which to display this defect type"
    )
    
    def __str__(self):
        return f"{self.operation_number.number} - {self.name}"
    
    class Meta:
        ordering = ['operation_number', 'order', 'name']


class TimeBasedDefectEntry(models.Model):
    """Track defects with timestamp"""
    ftq_record = models.ForeignKey(
        FTQRecord, 
        on_delete=models.CASCADE, 
        related_name='time_based_defects'
    )
    defect_type = models.ForeignKey(
        DefectType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    defect_type_custom = models.ForeignKey(
        'CustomDefectType', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    recorded_at = models.TimeField(
        verbose_name="Time Recorded",
        help_text="Time when this defect was observed"
    )
    count = models.PositiveIntegerField(
        verbose_name="Defect Count",
        help_text="Number of defects at this time"
    )
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        defect_name = ""
        if self.defect_type:
            defect_name = self.defect_type.name
        elif self.defect_type_custom:
            defect_name = self.defect_type_custom.name
        
        return f"{defect_name} - {self.recorded_at.strftime('%H:%M')} - Count: {self.count}"
    
    class Meta:
        ordering = ['recorded_at']
        verbose_name = "Time-Based Defect Entry"
        verbose_name_plural = "Time-Based Defect Entries"


class DefectRecord(models.Model):
    """Legacy defect record - kept for backward compatibility"""
    ftq_record = models.ForeignKey(FTQRecord, on_delete=models.CASCADE, related_name='defect_records')
    defect_type = models.ForeignKey(DefectType, on_delete=models.CASCADE, null=True, blank=True)
    defect_type_custom = models.ForeignKey('CustomDefectType', on_delete=models.CASCADE, null=True, blank=True)
    count = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        if self.defect_type:
            return f"{self.defect_type.name} ({self.count}) - {self.ftq_record.date}"
        elif self.defect_type_custom:
            return f"{self.defect_type_custom.name} ({self.count}) - {self.ftq_record.date}"
        return f"Defect record ({self.count}) - {self.ftq_record.date}"


class CustomDefectType(models.Model):
    """Custom defect types that can be added by operators"""
    ftq_record = models.ForeignKey(
        FTQRecord, 
        on_delete=models.CASCADE, 
        related_name='custom_defect_types'
    )
    name = models.CharField(max_length=200)
    operation_number = models.ForeignKey(
        OperationNumber,  # Reference the class defined above
        on_delete=models.CASCADE, 
        related_name='custom_defect_types'
    )
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.operation_number.number} - {self.name} (Custom)"
    


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

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('quality_approved', 'Quality Approved'),
        ('rejected', 'Rejected'),
    )

    # Link to verification status
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
        choices=[
            ('P703', 'P703'),
            ('U704', 'U704'),
            ('FD', 'FD'),
            ('SA', 'SA'),
            ('Gnome', 'Gnome'),
        ],
        verbose_name="Current Running Model",
        blank=True,
        null=True
    )
    
    # Shift choices
    SHIFTS = [
        ('S1', 'S1 - 6:30 AM to 6:30 PM'),
        ('A', 'A - 6:30 AM to 3:00 PM'),
        ('G', 'G - 8:30 AM to 5:00 PM'),
        ('B', 'B - 3:00 PM to 11:30 PM'),
        ('C', 'C - 11:30 PM to 6:30 AM'),
        ('S2', 'S2 - 6:30 PM to 6:30 AM'),
    ]
    
    shift = models.CharField(
        max_length=10,
        choices=SHIFTS,
        verbose_name="Shift",
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Auto-populate model and shift from related ChecklistBase"""
        # Auto-populate model and shift from checklist
        if self.verification_status:
            checklist = self.verification_status.checklists.first()
            if checklist:
                if not self.current_model:
                    self.current_model = checklist.selected_model
                if not self.shift:
                    self.shift = checklist.shift
        
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
    
    @property
    def ok_count(self):
        """Count of OK mechanisms"""
        return self.mechanism_statuses.filter(status='OK', is_not_applicable=False).count()
    
    @property
    def ng_count(self):
        """Count of NG mechanisms"""
        return self.mechanism_statuses.filter(status='NG', is_not_applicable=False).count()
    
    @property
    def na_count(self):
        """Count of N/A mechanisms"""
        return self.mechanism_statuses.filter(is_not_applicable=True).count()
    
    @property
    def total_mechanisms(self):
        """Total number of mechanisms"""
        return self.mechanism_statuses.count()
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Error Prevention Check"
        verbose_name_plural = "Error Prevention Checks"
    
    def __str__(self):
        shift_display = self.shift or "No Shift"
        if self.verification_status and self.verification_status.shift:
            shift_display = self.verification_status.shift.get_shift_type_display()
        return f"EP Check - {self.date} - {shift_display}"


class ErrorPreventionMechanism(models.Model):
    """Master list of Error Prevention mechanisms - Admin controlled"""
    
    # EP Mechanism ID
    mechanism_id = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="EP Mechanism ID"
    )
    
    # Description
    description = models.TextField(
        verbose_name="Mechanism Description",
        help_text="Full description of the EP mechanism"
    )
    
    # Verification method - NEW FIELD
    verification_method = models.TextField(
        verbose_name="Verification Method (English)",
        default="Start the machine with master and judgement will given by machine",
        help_text="English verification method description"
    )
    
    # Verification method in Hindi - NEW FIELD
    verification_method_hindi = models.TextField(
        verbose_name="Verification Method (Hindi)",
        default="मास्टर के साथ मशीन शुरू करें और मशीन द्वारा निर्णय दिया जाएगा",
        help_text="Hindi verification method description",
        blank=True
    )
    
    # Applicable models
    applicable_models = models.CharField(
        max_length=100,
        help_text="Comma-separated list of models (e.g., P703,U704,SA,FD or Gnome)",
        verbose_name="Applicable Models"
    )
    
    # Working status - ADMIN CONTROLLED
    is_currently_working = models.BooleanField(
        default=True,
        verbose_name="Currently Working",
        help_text="Admin-controlled: Is this mechanism currently functional?"
    )
    
    # Default alternative method when not working
    default_alternative_method = models.CharField(
        max_length=200,
        default="100% Inspection By Operator",
        verbose_name="Default Alternative Method"
    )
    
    # Display order
    display_order = models.IntegerField(
        default=0,
        verbose_name="Display Order",
        help_text="Order in which to display this mechanism"
    )
    
    # Active status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Is this mechanism currently in use?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'mechanism_id']
        verbose_name = "Error Prevention Mechanism (Master)"
        verbose_name_plural = "Error Prevention Mechanisms (Master)"
    
    def __str__(self):
        status = "✓" if self.is_currently_working else "✗"
        return f"{status} {self.mechanism_id} - {self.applicable_models}"



class ErrorPreventionMechanismStatus(models.Model):
    """Status for each EP mechanism in a daily check - Operator fills this"""
    
    OK_NG_CHOICES = [('OK', 'OK'), ('NG', 'NG')]
    
    # Relations
    ep_check = models.ForeignKey(
        ErrorPreventionCheck, 
        on_delete=models.CASCADE, 
        related_name='mechanism_statuses'
    )
    
    # Link to master mechanism
    mechanism = models.ForeignKey(
        ErrorPreventionMechanism,
        on_delete=models.CASCADE,
        related_name='daily_statuses',
        verbose_name="EP Mechanism",
          null=True,
                  blank=True,

     )
    
    # Legacy field for backward compatibility
    ep_mechanism_id = models.CharField(
        max_length=50,
        verbose_name="EP Mechanism ID (Legacy)",
        blank=True,
        null=True,
        editable=False
    )
    
    # Working status - COPIED FROM MASTER, NOT EDITABLE BY OPERATOR
    is_working = models.BooleanField(
        default=True, 
        verbose_name="Working",
        help_text="Admin-controlled via master mechanism"
    )
    
    # Alternative method - COPIED FROM MASTER
    alternative_method = models.CharField(
        max_length=200, 
        default="100% Inspection By Operator",
        verbose_name="Alternative Method",
        help_text="Admin-controlled via master mechanism"
    )
    
    # Operator-editable fields
    status = models.CharField(
        max_length=2, 
        choices=OK_NG_CHOICES, 
        verbose_name="Status",
        help_text="Operator selects OK or NG"
    )
    
    is_not_applicable = models.BooleanField(
        default=False, 
        verbose_name="N/A",
        help_text="Check if not applicable for this model"
    )
    
    # Comments - operator can add notes
    comments = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Operator Comments"
    )
    
    # Edit tracking
    last_edited_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_mechanism_statuses'
    )
    last_edited_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Sync from master mechanism
        if self.mechanism:
            self.is_working = self.mechanism.is_currently_working
            self.alternative_method = self.mechanism.default_alternative_method
            self.ep_mechanism_id = self.mechanism.mechanism_id
        
        # Track edits
        if self.pk:
            self.last_edited_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def can_operator_edit_status(self):
        """Check if operator can edit the status field"""
        # If mechanism is not working, operator cannot change status
        # They can only see it and the alternative method
        return self.is_working
    
    @property
    def display_status(self):
        """Get display status with working indicator"""
        if not self.is_working:
            return f"{self.status} (Not Working - {self.alternative_method})"
        return self.status
    
    class Meta:
        ordering = ['mechanism__display_order', 'mechanism__mechanism_id']
        verbose_name = "Mechanism Status"
        verbose_name_plural = "Mechanism Statuses"
    
    def __str__(self):
        mech_id = self.mechanism.mechanism_id if self.mechanism else self.ep_mechanism_id
        return f"{mech_id} - {self.ep_check.date} - {self.status}"


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
    
    changed_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='ep_check_changes'
    )
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    field_name = models.CharField(max_length=100, blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    additional_data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "EP Check History"
        verbose_name_plural = "EP Check Histories"
    
    def __str__(self):
        return f"{self.ep_check} - {self.action} by {self.changed_by.username}"
  
 
class ErrorPreventionMechanismHistory(models.Model):
    """Track changes made to individual mechanism statuses"""
    
    mechanism_status = models.ForeignKey(
        'ErrorPreventionMechanismStatus',
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    changed_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='mechanism_changes'
    )
    
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Mechanism Status History"
        verbose_name_plural = "Mechanism Status Histories"
    
    def __str__(self):
        mech_id = self.mechanism_status.mechanism.mechanism_id if self.mechanism_status.mechanism else "Unknown"
        return f"{mech_id} - {self.field_name} changed by {self.changed_by.username}"
     
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
from django.utils import timezone

class DTPMCheckpoint(models.Model):
    """Master table for DTPM checkpoints - fully editable in admin"""
    
    checkpoint_number = models.PositiveSmallIntegerField(
        unique=True,
        verbose_name="Checkpoint Number"
    )
    
    title_english = models.CharField(
        max_length=500,
        verbose_name="Title (English)"
    )
    
    title_hindi = models.CharField(
        max_length=500,
        verbose_name="Title (Hindi)",
        blank=True,
        null=True
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )
    
    reference_image = models.ImageField(
        upload_to='dtpm_checkpoints/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'gif'])],
        verbose_name="Reference Image"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Uncheck to disable this checkpoint"
    )
    
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Display Order",
        help_text="Order in which to display this checkpoint"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'checkpoint_number']
        verbose_name = "DTPM Checkpoint"
        verbose_name_plural = "DTPM Checkpoints"
    
    def __str__(self):
        return f"#{self.checkpoint_number} - {self.title_english}"


class DTPMChecklistFMA03New(models.Model):
    """Daily Tracking and Performance Monitoring Checklist for FMA03 Operation 35"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('quality_certified', 'Quality Certified'),
        ('rejected', 'Rejected'),
        ('quality_rejected', 'Quality Rejected'),
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
        choices=[
            ('P703', 'P703'),
            ('U704', 'U704'),
            ('FD', 'FD'),
            ('SA', 'SA'),
            ('Gnome', 'Gnome'),
        ],
        verbose_name="Current Running Model",
        blank=True,
        null=True
    )
    
    # Shift from checklist - will be auto-populated from ChecklistBase
    checklist_shift = models.CharField(
        max_length=10,
        choices=[
            ('S1', 'S1 - 6:30 AM to 6:30 PM'),
            ('A', 'A - 6:30 AM to 3:00 PM'),
            ('G', 'G - 8:30 AM to 5:00 PM'),
            ('B', 'B - 3:00 PM to 11:30 PM'),
            ('C', 'C - 11:30 PM to 6:30 AM'),
            ('S2', 'S2 - 6:30 PM to 6:30 AM'),
        ],
        verbose_name="Shift from Checklist",
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Verification fields
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
        verbose_name = "DTPM Checklist"
        verbose_name_plural = "DTPM Checklists"
    
    def __str__(self):
        shift_display = self.checklist_shift or "No Shift"
        if self.shift:
            shift_display = self.shift.get_shift_type_display()
        return f"DTPM Checklist - {self.date} - {shift_display}"
    
    @property
    def is_fully_completed(self):
        """Check if checklist is fully completed (quality certified)"""
        return self.status == 'quality_certified'
    
    @property
    def is_supervisor_approved(self):
        """Check if checklist is supervisor approved"""
        return self.status in ['supervisor_approved', 'quality_certified']


class DTPMCheckResultNew(models.Model):
    """Results for each checkpoint in a DTPM checklist - now linked to DTPMCheckpoint"""
    
    OK_NG_CHOICES = [('OK', 'OK'), ('NG', 'NG')]
    
    # Relations
    checklist = models.ForeignKey(
        DTPMChecklistFMA03New, 
        on_delete=models.CASCADE, 
        related_name='check_results'
    )
    
    # Link to checkpoint master
    checkpoint = models.ForeignKey(
        DTPMCheckpoint,
        on_delete=models.CASCADE,
        related_name='check_results',
        verbose_name="Checkpoint",
        blank=True, null=True
    )
    
    # Status - only field operators can change
    status = models.CharField(
        max_length=2, 
        choices=OK_NG_CHOICES, 
        verbose_name="Status",
        default='NG'
    )
    
    # Comments
    comments = models.TextField(blank=True, null=True)
    
    # Timestamps
    checked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['checklist', 'checkpoint']
        ordering = ['checkpoint__order', 'checkpoint__checkpoint_number']
    
    def __str__(self):
        return f"{self.checklist} - {self.checkpoint.checkpoint_number}: {self.status}"


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
        return f"Issue: {self.check_result.checkpoint.checkpoint_number} - {self.status}"


class DTPMVerificationHistory(models.Model):
    """Track all verification actions on DTPM checklists"""
    
    VERIFICATION_TYPES = [
        ('supervisor_approve', 'Supervisor Approved'),
        ('supervisor_reject', 'Supervisor Rejected'),
        ('quality_certify', 'Quality Certified'),
        ('quality_reject', 'Quality Rejected'),
    ]
    
    checklist = models.ForeignKey(
        DTPMChecklistFMA03New, 
        on_delete=models.CASCADE, 
        related_name='verification_history'
    )
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    verified_by = models.ForeignKey('User', on_delete=models.CASCADE)
    verified_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-verified_at']
        verbose_name = "DTPM Verification History"
        verbose_name_plural = "DTPM Verification Histories"
    
    def __str__(self):
        return f"{self.get_verification_type_display()} - {self.verified_by.username} - {self.verified_at}"


# Signal to automatically create checkpoint results when a new DTPM checklist is created
@receiver(post_save, sender=DTPMChecklistFMA03New)
def create_check_results(sender, instance, created, **kwargs):
    """Create check results for all active checkpoints when a new checklist is created"""
    if created:
        # Get all active checkpoints
        active_checkpoints = DTPMCheckpoint.objects.filter(is_active=True).order_by('order', 'checkpoint_number')
        
        # Create a check result for each active checkpoint
        for checkpoint in active_checkpoints:
            DTPMCheckResultNew.objects.create(
                checklist=instance,
                checkpoint=checkpoint,
                status='NG'  # Default status
            )
            
            
            



# New Checksheet  
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class Checksheet(models.Model):
    """Main checksheet template that can be created and managed by admin"""
    name = models.CharField(max_length=200, unique=True, verbose_name="Checksheet Name")
    name_hindi = models.CharField(max_length=200, blank=True, verbose_name="Checksheet Name (Hindi)")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='created_checksheets')
    
    applicable_models = models.CharField(
        max_length=100,
        blank=True,
        help_text="Comma-separated model names (e.g., P703,U704) or leave blank for all models"
    )
    
    class Meta:
        ordering = ['-is_active', 'name']
        verbose_name = "Checksheet Template"
        verbose_name_plural = "Checksheet Templates"
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status})"
    
    @property
    def section_count(self):
        return self.sections.count()
    
    @property
    def field_count(self):
        return ChecksheetField.objects.filter(section__checksheet=self).count()


class ChecksheetSection(models.Model):
    """Sections/Headers within a checksheet"""
    checksheet = models.ForeignKey(Checksheet, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=200, verbose_name="Section Name")
    name_hindi = models.CharField(max_length=200, blank=True, verbose_name="Section Name (Hindi)")
    description = models.TextField(blank=True, verbose_name="Section Description")
    order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        ordering = ['checksheet', 'order', 'name']
        unique_together = ['checksheet', 'name']
        verbose_name = "Checksheet Section"
        verbose_name_plural = "Checksheet Sections"
    
    def __str__(self):
        return f"{self.checksheet.name} - {self.name}"
    
    @property
    def field_count(self):
        return self.fields.count()


class ChecksheetField(models.Model):
    """Individual fields/parameters within a section"""
    FIELD_TYPE_CHOICES = [
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('decimal', 'Decimal Input'),
        ('dropdown', 'Dropdown Select'),
        ('ok_nok', 'OK/NOK'),
        ('yes_no', 'Yes/No'),
        ('date', 'Date'),
        ('time', 'Time'),
        ('datetime', 'Date & Time'),
        ('checkbox', 'Checkbox'),
        ('textarea', 'Text Area'),
    ]
    
    section = models.ForeignKey(ChecksheetSection, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=300, verbose_name="Field Label")
    label_hindi = models.CharField(max_length=300, blank=True, verbose_name="Field Label (Hindi)")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='text')
    
    choices = models.TextField(
        blank=True,
        verbose_name="Choices (comma-separated)",
        help_text="For dropdown fields, enter choices separated by commas"
    )
    
    is_required = models.BooleanField(default=True, verbose_name="Required Field")
    min_value = models.FloatField(null=True, blank=True, verbose_name="Minimum Value")
    max_value = models.FloatField(null=True, blank=True, verbose_name="Maximum Value")
    unit = models.CharField(max_length=50, blank=True, verbose_name="Unit (e.g., bar, kPa, LPM)")
    
    help_text = models.CharField(max_length=500, blank=True, verbose_name="Help Text")
    help_text_hindi = models.CharField(max_length=500, blank=True, verbose_name="Help Text (Hindi)")
    default_value = models.CharField(max_length=200, blank=True, verbose_name="Default Value")
    placeholder = models.CharField(max_length=200, blank=True, verbose_name="Placeholder Text")
    
    auto_fill_based_on_model = models.BooleanField(
        default=False,
        verbose_name="Auto-fill based on selected model"
    )
    model_value_mapping = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Model Value Mapping"
    )
    
    has_status_field = models.BooleanField(
        default=False,
        verbose_name="Has Status Field (OK/NOK)"
    )
    
    requires_comment_if_nok = models.BooleanField(
        default=False,
        verbose_name="Require comment if NOK/No"
    )
    
    order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        ordering = ['section', 'order', 'label']
        verbose_name = "Checksheet Field"
        verbose_name_plural = "Checksheet Fields"
    
    def __str__(self):
        return f"{self.section.name} - {self.label}"
    
    def get_choices_list(self):
        """Convert comma-separated choices to list"""
        if self.choices:
            return [choice.strip() for choice in self.choices.split(',')]
        return []
    
    def get_value_for_model(self, model_name):
        """Get the auto-fill value for a specific model"""
        if self.auto_fill_based_on_model and self.model_value_mapping:
            return self.model_value_mapping.get(model_name, self.default_value)
        return self.default_value


class ChecksheetResponse(models.Model):
    """Store responses to checksheet instances"""
    checksheet = models.ForeignKey(Checksheet, on_delete=models.CASCADE, related_name='responses')
    verification_status = models.ForeignKey(
        'DailyVerificationStatus',
        on_delete=models.CASCADE,
        related_name='checksheet_responses',
        null=True,
        blank=True
    )
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('quality_approved', 'Quality Approved'),
        ('rejected', 'Rejected'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    filled_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='filled_checksheets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    supervisor_approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervisor_approved_checksheets'
    )
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    
    quality_approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quality_approved_checksheets'
    )
    quality_approved_at = models.DateTimeField(null=True, blank=True)
    
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Checksheet Response"
        verbose_name_plural = "Checksheet Responses"
    
    def __str__(self):
        return f"{self.checksheet.name} - {self.status}"
    
    @property
    def can_be_edited(self):
        """Check if this response can be edited"""
        # Allow editing for draft and rejected statuses
        # Supervisors can edit submitted and supervisor_approved as well
        return self.status in ['draft', 'rejected', 'submitted']

    @property
    def can_be_edited_by_supervisor(self):
        """Check if this response can be edited by supervisor"""
        # Supervisors can edit more statuses
        return self.status in ['draft', 'rejected', 'submitted', 'supervisor_approved']

    @property
    def can_be_approved_by_supervisor(self):
        """Check if this response can be approved by supervisor"""
        return self.status == 'submitted'

    @property
    def can_be_approved_by_quality(self):
        """Check if this response can be approved by quality"""
        return self.status == 'supervisor_approved'

    @property
    def can_be_rejected(self):
        """Check if this response can be rejected"""
        return self.status in ['submitted', 'supervisor_approved']

    @property
    def is_final(self):
        """Check if this response is in a final state"""
        return self.status in ['quality_approved', 'rejected']

    @property
    def status_badge_class(self):
        """Get Bootstrap badge class for status"""
        status_classes = {
            'draft': 'bg-secondary',
            'submitted': 'bg-info',
            'supervisor_approved': 'bg-primary',
            'quality_approved': 'bg-success',
            'rejected': 'bg-danger',
        }
        return status_classes.get(self.status, 'bg-secondary')

    def can_user_edit(self, user):
        """Check if a specific user can edit this response"""
        # Owner can edit if status allows
        is_owner = self.filled_by == user
        
        # Supervisors and admins have extended permissions
        is_supervisor = user.user_type in ['shift_supervisor', 'quality_supervisor']
        is_admin = user.is_superuser
        
        if is_admin:
            # Admins can edit anything except quality_approved
            return self.status != 'quality_approved'
        elif is_supervisor:
            # Supervisors can edit their submissions and pending approvals
            return self.can_be_edited_by_supervisor
        elif is_owner:
            # Owners can only edit draft, rejected, or submitted
            return self.can_be_edited
        
        return False

    def approve_by_supervisor(self, user):
        """Approve the checksheet response by supervisor"""
        if not self.can_be_approved_by_supervisor:
            raise ValueError("This response cannot be approved by supervisor at this stage")
        
        self.status = 'supervisor_approved'
        self.supervisor_approved_by = user
        self.supervisor_approved_at = timezone.now()
        self.save()

    def approve_by_quality(self, user):
        """Approve the checksheet response by quality supervisor"""
        if not self.can_be_approved_by_quality:
            raise ValueError("This response cannot be approved by quality at this stage")
        
        self.status = 'quality_approved'
        self.quality_approved_by = user
        self.quality_approved_at = timezone.now()
        self.save()

    def reject(self, user, reason):
        """Reject the checksheet response"""
        if not self.can_be_rejected:
            raise ValueError("This response cannot be rejected at this stage")
        
        self.status = 'rejected'
        self.rejection_reason = reason
        self.save()

    def get_completion_percentage(self):
        """Calculate the completion percentage of required fields"""
        total_required = self.checksheet.sections.filter(
            is_active=True
        ).aggregate(
            count=models.Count('fields', filter=models.Q(fields__is_required=True, fields__is_active=True))
        )['count'] or 0
        
        if total_required == 0:
            return 100
        
        filled_required = self.field_responses.filter(
            field__is_required=True,
            field__is_active=True
        ).exclude(
            value=''
        ).count()
        
        return int((filled_required / total_required) * 100)

    def has_nok_items(self):
        """Check if there are any NOK or failed items"""
        return self.field_responses.filter(
            models.Q(status='NOK') | models.Q(value='NOK')
        ).exists()

    def get_nok_count(self):
        """Get count of NOK items"""
        return self.field_responses.filter(
            models.Q(status='NOK') | models.Q(value='NOK')
        ).count()


class ChecksheetFieldResponse(models.Model):
    """Store individual field responses"""
    response = models.ForeignKey(
        ChecksheetResponse,
        on_delete=models.CASCADE,
        related_name='field_responses'
    )
    field = models.ForeignKey(ChecksheetField, on_delete=models.CASCADE)
    
    value = models.TextField(blank=True, verbose_name="Field Value")
    
    status = models.CharField(
        max_length=10,
        choices=[('OK', 'OK'), ('NOK', 'NOK')],
        blank=True,
        verbose_name="Status"
    )
    
    comment = models.TextField(blank=True, verbose_name="Comment")
    
    filled_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    filled_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['response', 'field']
        verbose_name = "Field Response"
        verbose_name_plural = "Field Responses"
    
    def __str__(self):
        return f"{self.response.checksheet.name} - {self.field.label}: {self.value}"
    
    @property
    def is_ok(self):
        """Check if this field response is OK"""
        return self.status == 'OK' or self.value == 'OK'
    
    @property
    def is_nok(self):
        """Check if this field response is NOK"""
        return self.status == 'NOK' or self.value == 'NOK'
    
    @property
    def display_value(self):
        """Get formatted display value"""
        if self.field.field_type in ['ok_nok', 'yes_no']:
            return self.status if self.status else self.value
        elif self.field.unit:
            return f"{self.value} {self.field.unit}"
        return self.value
    
    
    
    
    
    
    
    # new 
    
    
    
    
    
#  Time-Based Progressive Parameter Display

 
class ParameterGroupConfig(models.Model):
    """Configuration for when each parameter group becomes available"""
    
    PARAMETER_GROUPS = [
        ('uv_vacuum', 'UV Vacuum Test (5 readings)'),
        ('uv_flow', 'UV Flow Value (5 readings)'),
        ('umbrella_valve', 'Umbrella Valve Assembly (5 checks)'),
        ('uv_clip', 'UV Clip Pressing (5 checks)'),
        ('workstation', 'Workstation Clean (1 check)'),
        ('bin_contamination', 'Bin Contamination Check (5 checks)'),
    ]
    
    model_name = models.CharField(
        max_length=10, 
        choices=[
            ('P703', 'P703'),
            ('U704', 'U704'),
            ('FD', 'FD'),
            ('SA', 'SA'),
            ('Gnome', 'Gnome'),
        ]
    )
    
    parameter_group = models.CharField(
        max_length=50,
        choices=PARAMETER_GROUPS,
        verbose_name="Parameter Group"
    )
    
    # Minutes after shift/checklist start when this parameter becomes available
    frequency_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Minutes after checklist creation when fields appear"
    )
    
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now=True,blank=True,null=True)

    
    class Meta:
        unique_together = ['model_name', 'parameter_group']
        ordering = ['display_order', 'frequency_minutes']
        verbose_name = "Parameter Group Configuration"
        verbose_name_plural = "Parameter Group Configurations"
    
    def __str__(self):
        return f"{self.model_name} - {self.get_parameter_group_display()} (after {self.frequency_minutes} min)"


class ParameterGroupEntry(models.Model):
    """Stores readings for each parameter group"""
    
    OK_NG_CHOICES = [('OK', 'OK'), ('NOK', 'NOK')]
    YES_NO_CHOICES = [('Yes', 'Yes'), ('No', 'No')]
    
    # Link to checklist
    checklist = models.ForeignKey(
        'ChecklistBase',
        on_delete=models.CASCADE,
        related_name='parameter_entries'
    )
    
    # Which parameter group this entry is for
    parameter_group = models.CharField(
        max_length=50,
        choices=ParameterGroupConfig.PARAMETER_GROUPS
    )
    
    # When this entry was filled
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_completed = models.BooleanField(default=False)
    
    # ============================================
    # UV VACUUM TEST (5 readings)
    # ============================================
    uv_vacuum_test_1 = models.FloatField(
        verbose_name="UV Vacuum Test 1 (kPa)",
        help_text="Range: -43 to -35 kPa",
        blank=True,
        null=True
    )
    uv_vacuum_test_1_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_vacuum_test_2 = models.FloatField(verbose_name="UV Vacuum Test 2 (kPa)", blank=True, null=True)
    uv_vacuum_test_2_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_vacuum_test_3 = models.FloatField(verbose_name="UV Vacuum Test 3 (kPa)", blank=True, null=True)
    uv_vacuum_test_3_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_vacuum_test_4 = models.FloatField(verbose_name="UV Vacuum Test 4 (kPa)", blank=True, null=True)
    uv_vacuum_test_4_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_vacuum_test_5 = models.FloatField(verbose_name="UV Vacuum Test 5 (kPa)", blank=True, null=True)
    uv_vacuum_test_5_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    # ============================================
    # UV FLOW VALUE (5 readings)
    # ============================================
    uv_flow_value_1 = models.FloatField(
        verbose_name="UV Flow Value 1 (LPM)",
        help_text="Range: 30-40 LPM",
        blank=True,
        null=True
    )
    uv_flow_value_1_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_flow_value_2 = models.FloatField(verbose_name="UV Flow Value 2 (LPM)", blank=True, null=True)
    uv_flow_value_2_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_flow_value_3 = models.FloatField(verbose_name="UV Flow Value 3 (LPM)", blank=True, null=True)
    uv_flow_value_3_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_flow_value_4 = models.FloatField(verbose_name="UV Flow Value 4 (LPM)", blank=True, null=True)
    uv_flow_value_4_comment = models.TextField(blank=True, null=True)  # ← ADD THIS
    
    uv_flow_value_5 = models.FloatField(verbose_name="UV Flow Value 5 (LPM)", blank=True, null=True)
    uv_flow_value_5_comment = models.TextField(blank=True, null=True)      
    # ============================================
    # UMBRELLA VALVE ASSEMBLY (5 checks)
    # ============================================
    umbrella_valve_assembly_1 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    umbrella_valve_assembly_1_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_2 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    umbrella_valve_assembly_2_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_3 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    umbrella_valve_assembly_3_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_4 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    umbrella_valve_assembly_4_comment = models.TextField(blank=True, null=True)
    umbrella_valve_assembly_5 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    umbrella_valve_assembly_5_comment = models.TextField(blank=True, null=True)
    
    # ============================================
    # UV CLIP PRESSING (5 checks)
    # ============================================
    uv_clip_pressing_1 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    uv_clip_pressing_1_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_2 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    uv_clip_pressing_2_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_3 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    uv_clip_pressing_3_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_4 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    uv_clip_pressing_4_comment = models.TextField(blank=True, null=True)
    uv_clip_pressing_5 = models.CharField(max_length=3, choices=OK_NG_CHOICES, blank=True, null=True)
    uv_clip_pressing_5_comment = models.TextField(blank=True, null=True)
    
    # ============================================
    # WORKSTATION CLEAN (1 check)
    # ============================================
    workstation_clean = models.CharField(
        max_length=3,
        choices=YES_NO_CHOICES,
        verbose_name="Workstation Clean",
        blank=True,
        null=True
    )
    workstation_clean_comment = models.TextField(blank=True, null=True)
    
    # ============================================
    # BIN CONTAMINATION (5 checks)
    # ============================================
    bin_contamination_check_1 = models.CharField(max_length=3, choices=YES_NO_CHOICES, blank=True, null=True)
    bin_contamination_check_1_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_2 = models.CharField(max_length=3, choices=YES_NO_CHOICES, blank=True, null=True)
    bin_contamination_check_2_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_3 = models.CharField(max_length=3, choices=YES_NO_CHOICES, blank=True, null=True)
    bin_contamination_check_3_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_4 = models.CharField(max_length=3, choices=YES_NO_CHOICES, blank=True, null=True)
    bin_contamination_check_4_comment = models.TextField(blank=True, null=True)
    bin_contamination_check_5 = models.CharField(max_length=3, choices=YES_NO_CHOICES, blank=True, null=True)
    bin_contamination_check_5_comment = models.TextField(blank=True, null=True)
    
    # ============================================
    # COMMON FIELDS
    # ============================================
    is_after_maintenance = models.BooleanField(default=False)
    maintenance_comment = models.TextField(blank=True, null=True)
    general_notes = models.TextField(blank=True, null=True)
    
    # Computed properties
    @property
    def uv_vacuum_average(self):
        """Calculate average of UV vacuum test readings"""
        values = [
            self.uv_vacuum_test_1, self.uv_vacuum_test_2, 
            self.uv_vacuum_test_3, self.uv_vacuum_test_4, 
            self.uv_vacuum_test_5
        ]
        valid_values = [v for v in values if v is not None]
        return sum(valid_values) / len(valid_values) if valid_values else 0
    
    @property
    def uv_flow_average(self):
        """Calculate average of UV flow value readings"""
        values = [
            self.uv_flow_value_1, self.uv_flow_value_2,
            self.uv_flow_value_3, self.uv_flow_value_4,
            self.uv_flow_value_5
        ]
        valid_values = [v for v in values if v is not None]
        return sum(valid_values) / len(valid_values) if valid_values else 0
    
    @property
    def umbrella_valve_ok_count(self):
        """Count OK readings for umbrella valve"""
        values = [
            self.umbrella_valve_assembly_1, self.umbrella_valve_assembly_2,
            self.umbrella_valve_assembly_3, self.umbrella_valve_assembly_4,
            self.umbrella_valve_assembly_5
        ]
        return sum(1 for v in values if v == 'OK')
    
    @property
    def uv_clip_ok_count(self):
        """Count OK readings for UV clip"""
        values = [
            self.uv_clip_pressing_1, self.uv_clip_pressing_2,
            self.uv_clip_pressing_3, self.uv_clip_pressing_4,
            self.uv_clip_pressing_5
        ]
        return sum(1 for v in values if v == 'OK')
    
    @property
    def bin_contamination_yes_count(self):
        """Count Yes readings for bin contamination"""
        values = [
            self.bin_contamination_check_1, self.bin_contamination_check_2,
            self.bin_contamination_check_3, self.bin_contamination_check_4,
            self.bin_contamination_check_5
        ]
        return sum(1 for v in values if v == 'Yes')
    
    @property
    def parameter_display_name(self):
        """Get display name for parameter group"""
        return dict(ParameterGroupConfig.PARAMETER_GROUPS).get(self.parameter_group, self.parameter_group)
    
    def get_applicable_fields(self):
        """Return list of field names applicable to this parameter group"""
        field_mapping = {
            'uv_vacuum': [
                'uv_vacuum_test_1', 'uv_vacuum_test_1_comment',  # ← UPDATE THIS
                'uv_vacuum_test_2', 'uv_vacuum_test_2_comment',  # ← UPDATE THIS
                'uv_vacuum_test_3', 'uv_vacuum_test_3_comment',  # ← UPDATE THIS
                'uv_vacuum_test_4', 'uv_vacuum_test_4_comment',  # ← UPDATE THIS
                'uv_vacuum_test_5', 'uv_vacuum_test_5_comment',  # ← UPDATE THIS
            ],
            'uv_flow': [
                'uv_flow_value_1', 'uv_flow_value_1_comment',    # ← UPDATE THIS
                'uv_flow_value_2', 'uv_flow_value_2_comment',    # ← UPDATE THIS
                'uv_flow_value_3', 'uv_flow_value_3_comment',    # ← UPDATE THIS
                'uv_flow_value_4', 'uv_flow_value_4_comment',    # ← UPDATE THIS
                'uv_flow_value_5', 'uv_flow_value_5_comment',    # ← UPDATE THIS
            ],

            'umbrella_valve': [
                'umbrella_valve_assembly_1', 'umbrella_valve_assembly_1_comment',
                'umbrella_valve_assembly_2', 'umbrella_valve_assembly_2_comment',
                'umbrella_valve_assembly_3', 'umbrella_valve_assembly_3_comment',
                'umbrella_valve_assembly_4', 'umbrella_valve_assembly_4_comment',
                'umbrella_valve_assembly_5', 'umbrella_valve_assembly_5_comment',
            ],
            'uv_clip': [
                'uv_clip_pressing_1', 'uv_clip_pressing_1_comment',
                'uv_clip_pressing_2', 'uv_clip_pressing_2_comment',
                'uv_clip_pressing_3', 'uv_clip_pressing_3_comment',
                'uv_clip_pressing_4', 'uv_clip_pressing_4_comment',
                'uv_clip_pressing_5', 'uv_clip_pressing_5_comment',
            ],
            'workstation': [
                'workstation_clean', 'workstation_clean_comment'
            ],
            'bin_contamination': [
                'bin_contamination_check_1', 'bin_contamination_check_1_comment',
                'bin_contamination_check_2', 'bin_contamination_check_2_comment',
                'bin_contamination_check_3', 'bin_contamination_check_3_comment',
                'bin_contamination_check_4', 'bin_contamination_check_4_comment',
                'bin_contamination_check_5', 'bin_contamination_check_5_comment',
            ],
        }
        
        # Always include common fields
        common_fields = ['is_after_maintenance', 'maintenance_comment', 'general_notes']
        return field_mapping.get(self.parameter_group, []) + common_fields

    @property
    def supervisor_verification(self):
        """Get supervisor verification for this entry"""
        return self.verifications.filter(verification_type='supervisor').first()
    
    @property
    def quality_verification(self):
        """Get quality verification for this entry"""
        return self.verifications.filter(verification_type='quality').first()
    
    @property
    def is_supervisor_verified(self):
        """Check if supervisor has verified"""
        return self.verifications.filter(verification_type='supervisor').exists()
    
    @property
    def is_quality_verified(self):
        """Check if quality has verified"""
        return self.verifications.filter(verification_type='quality').exists()
    
    @property
    def is_fully_verified(self):
        """Check if both supervisors have verified"""
        return self.is_supervisor_verified and self.is_quality_verified
    
    @property
    def verification_status_badge(self):
        """Get HTML badge for verification status"""
        if self.is_fully_verified:
            return '<span class="badge bg-success">✓ Fully Verified</span>'
        elif self.is_supervisor_verified:
            return '<span class="badge bg-warning">⏳ Quality Pending</span>'
        else:
            return '<span class="badge bg-secondary">⏳ Supervisor Pending</span>'
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = "Parameter Group Entry"
        verbose_name_plural = "Parameter Group Entries"
    
    def __str__(self):
        return f"{self.checklist} - {self.parameter_display_name} - {self.timestamp.strftime('%H:%M')}"    
    
    
    
    
#

class ParameterGroupVerification(models.Model):
    """Track verification of individual parameter group entries"""
    
    VERIFICATION_TYPES = [
        ('supervisor', 'Shift Supervisor'),
        ('quality', 'Quality Supervisor'),
    ]
    
    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    parameter_entry = models.ForeignKey(
        'ParameterGroupEntry',
        on_delete=models.CASCADE,
        related_name='verifications'
    )
    
    verification_type = models.CharField(
        max_length=20,
        choices=VERIFICATION_TYPES
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )
    
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='parameter_group_verifications'
    )
    
    verified_at = models.DateTimeField(auto_now_add=True)
    
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Verification Comment"
    )
    
    class Meta:
        ordering = ['-verified_at']
        unique_together = ['parameter_entry', 'verification_type']
        verbose_name = "Parameter Group Verification"
        verbose_name_plural = "Parameter Group Verifications"
    
    def __str__(self):
        return f"{self.parameter_entry.parameter_display_name} - {self.get_verification_type_display()} - {self.status}"