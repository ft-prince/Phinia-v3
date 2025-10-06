from django import forms
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import inlineformset_factory
from .models import (
    DefectCategory,
    User, 
    Shift, 
    DailyVerificationStatus,
    ChecklistBase, 
    SubgroupEntry, 
    Verification, 
    Concern, 
    SubgroupVerification,
    FTQRecord,
    DefectRecord,
    CustomDefectType,
    OperationNumber,
    DefectType
)
from .models import SubgroupEntry, SubgroupFrequencyConfig, ChecksheetContentConfig

class DateInput(forms.DateInput):
    """Custom DateInput with HTML5 date type for better date pickers"""
    input_type = 'date'


class DailyVerificationStatusForm(forms.ModelForm):
    """Form for creating a new daily verification status entry"""
    class Meta:
        model = DailyVerificationStatus
        fields = ['date']
        widgets = {
            'date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Set default date to today
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()


class ShiftForm(forms.ModelForm):
    """Form for creating a new shift entry"""
    class Meta:
        model = Shift
        fields = ['date', 'shift_type', 'operator', 'shift_supervisor', 'quality_supervisor']
        widgets = {
            'date': DateInput(),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Filter users by role
        self.fields['operator'].queryset = User.objects.filter(user_type='operator')
        self.fields['shift_supervisor'].queryset = User.objects.filter(user_type='shift_supervisor')
        self.fields['quality_supervisor'].queryset = User.objects.filter(user_type='quality_supervisor')
        
        # Set default date to today
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()
            
        # Set default operator to current user if they're an operator
        if self.user and self.user.user_type == 'operator' and not self.initial.get('operator'):
            self.initial['operator'] = self.user


class ChecklistBaseForm(forms.ModelForm):
    """Form for base checklist information with dynamic content support"""
    class Meta:
        model = ChecklistBase
        exclude = ['verification_status', 'status', 'created_at', 'shift', 'frequency_config']
    
    def __init__(self, *args, **kwargs):
        # Get the verification status instance if provided
        self.verification_status = kwargs.pop('verification_status', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply base styling to all fields
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'required': True
            })

            # Update field attributes without validation restrictions
            if field == 'line_pressure':
                self.fields[field].widget.attrs.update({
                    'type': 'number',
                    'step': 'any',
                    'placeholder': 'Recommended: 4.5 - 5.5 bar'
                })
            elif field == 'uv_flow_input_pressure':
                self.fields[field].widget.attrs.update({
                    'type': 'number',
                    'step': 'any',
                    'placeholder': 'Recommended: 11 - 15 kPa'
                })
            elif field == 'test_pressure_vacuum':
                self.fields[field].widget.attrs.update({
                    'type': 'number',
                    'step': 'any',
                    'placeholder': 'Recommended: 0.25 - 0.3 MPa'
                })
        
        # Add dynamic fields based on ChecksheetContentConfig if model is selected
        if self.data and self.data.get('selected_model'):
            self._add_dynamic_fields(self.data.get('selected_model'))
        elif self.instance and self.instance.pk and self.instance.selected_model:
            self._add_dynamic_fields(self.instance.selected_model)
    
    def _add_dynamic_fields(self, model_name):
        """Add dynamic fields based on ChecksheetContentConfig"""
        try:
            dynamic_params = ChecksheetContentConfig.objects.filter(
                model_name=model_name,
                is_active=True
            ).order_by('order')
            
            for param in dynamic_params:
                field_name = f'dynamic_{param.id}'
                
                # Create field based on measurement type
                if param.measurement_type == 'numeric':
                    self.fields[field_name] = forms.FloatField(
                        label=f"{param.parameter_name} ({param.parameter_name_hindi})" if param.parameter_name_hindi else param.parameter_name,
                        help_text=f"Range: {param.min_value}-{param.max_value} {param.unit}" if param.min_value else f"Unit: {param.unit}",
                        required=False,
                        widget=forms.NumberInput(attrs={
                            'class': 'form-control',
                            'step': 'any',
                            'placeholder': f"{param.min_value}-{param.max_value} {param.unit}" if param.min_value else ""
                        })
                    )
                elif param.measurement_type == 'ok_nok':
                    self.fields[field_name] = forms.ChoiceField(
                        choices=[('', '---'), ('OK', 'OK'), ('NOK', 'NOK')],
                        label=f"{param.parameter_name} ({param.parameter_name_hindi})" if param.parameter_name_hindi else param.parameter_name,
                        required=False,
                        widget=forms.Select(attrs={'class': 'form-control'})
                    )
                    
                    # Add comment field if NOK requires comment
                    if param.requires_comment_if_nok:
                        comment_field_name = f'{field_name}_comment'
                        self.fields[comment_field_name] = forms.CharField(
                            label=f"Comment for {param.parameter_name}",
                            required=False,
                            widget=forms.Textarea(attrs={
                                'class': 'form-control',
                                'rows': 2,
                                'placeholder': 'Required if NOK'
                            })
                        )
                elif param.measurement_type == 'yes_no':
                    self.fields[field_name] = forms.ChoiceField(
                        choices=[('', '---'), ('Yes', 'Yes'), ('No', 'No')],
                        label=f"{param.parameter_name} ({param.parameter_name_hindi})" if param.parameter_name_hindi else param.parameter_name,
                        required=False,
                        widget=forms.Select(attrs={'class': 'form-control'})
                    )
                    
                    # Add comment field if No requires comment
                    if param.requires_comment_if_nok:
                        comment_field_name = f'{field_name}_comment'
                        self.fields[comment_field_name] = forms.CharField(
                            label=f"Comment for {param.parameter_name}",
                            required=False,
                            widget=forms.Textarea(attrs={
                                'class': 'form-control',
                                'rows': 2,
                                'placeholder': 'Required if No'
                            })
                        )
                
                # Store parameter config for later validation
                if not hasattr(self, '_dynamic_params'):
                    self._dynamic_params = {}
                self._dynamic_params[field_name] = param
        
        except Exception as e:
            # Log error but don't break the form
            print(f"Error adding dynamic fields: {e}")

    def clean(self):
        cleaned_data = super().clean()
        warnings = []
        errors = []

        # Validate standard measurements
        try:
            line_pressure = float(cleaned_data.get('line_pressure', 0))
            if not (4.5 <= line_pressure <= 5.5):
                warnings.append(f"Line pressure {line_pressure} is outside recommended range (4.5 - 5.5 bar)")
        except (TypeError, ValueError):
            pass

        try:
            uv_pressure = float(cleaned_data.get('uv_flow_input_pressure', 0))
            if not (11 <= uv_pressure <= 15):
                warnings.append(f"UV flow input pressure {uv_pressure} is outside recommended range (11 - 15 kPa)")
        except (TypeError, ValueError):
            pass

        try:
            test_pressure = float(cleaned_data.get('test_pressure_vacuum', 0))
            if not (0.25 <= test_pressure <= 0.3):
                warnings.append(f"Test pressure vacuum {test_pressure} is outside recommended range (0.25 - 0.3 MPa)")
        except (TypeError, ValueError):
            pass

        # Validate dynamic fields
        if hasattr(self, '_dynamic_params'):
            for field_name, param in self._dynamic_params.items():
                value = cleaned_data.get(field_name)
                
                if value:
                    # Validate numeric ranges
                    if param.measurement_type == 'numeric' and param.min_value and param.max_value:
                        try:
                            num_value = float(value)
                            if not (param.min_value <= num_value <= param.max_value):
                                warnings.append(
                                    f"{param.parameter_name}: {num_value} {param.unit} is outside range "
                                    f"({param.min_value}-{param.max_value} {param.unit})"
                                )
                        except (TypeError, ValueError):
                            pass
                    
                    # Check for required comments on NOK/No values
                    if param.requires_comment_if_nok:
                        comment_field = f'{field_name}_comment'
                        
                        if param.measurement_type == 'ok_nok' and value == 'NOK':
                            if not cleaned_data.get(comment_field):
                                errors.append(f"Comment required for {param.parameter_name} (NOK)")
                        
                        elif param.measurement_type == 'yes_no' and value == 'No':
                            if not cleaned_data.get(comment_field):
                                errors.append(f"Comment required for {param.parameter_name} (No)")

        # Store warnings and errors
        if warnings:
            self.warnings = warnings
        
        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data
    
    def save(self, commit=True):
        """Save form with verification status and frequency config"""
        instance = super().save(commit=False)
        
        if self.verification_status:
            instance.verification_status = self.verification_status
        
        # Get or create frequency config for the selected model
        if instance.selected_model:
            frequency_config, created = SubgroupFrequencyConfig.objects.get_or_create(
                model_name=instance.selected_model,
                defaults={
                    'frequency_hours': 2,
                    'max_subgroups': 6,
                    'is_active': True
                }
            )
            instance.frequency_config = frequency_config
        
        if commit:
            instance.save()
            
            # Save dynamic field values to a separate model if needed
            if hasattr(self, '_dynamic_params'):
                self._save_dynamic_values(instance)
        
        return instance
    
    def _save_dynamic_values(self, instance):
        """Save dynamic field values to ChecklistDynamicValue model"""
        # You would need to create a ChecklistDynamicValue model to store these
        try:
            from .models import ChecklistDynamicValue
            
            for field_name, param in self._dynamic_params.items():
                value = self.cleaned_data.get(field_name)
                comment = self.cleaned_data.get(f'{field_name}_comment', '')
                
                if value:
                    ChecklistDynamicValue.objects.update_or_create(
                        checklist=instance,
                        parameter=param,
                        defaults={
                            'value': str(value),
                            'comment': comment
                        }
                    )
        except ImportError:
            # Model doesn't exist yet, skip
            pass
        
        # forms.py - Updated for 5 readings per parameter


# Updated utility functions for views.py
def get_current_shift_type():
    """Get current shift type based on time - UPDATED"""
    from django.utils import timezone
    
    current_hour = timezone.localtime(timezone.now()).hour
    current_minute = timezone.localtime(timezone.now()).minute
    current_time_minutes = current_hour * 60 + current_minute
    
    # Define shift time ranges in minutes from midnight
    if (6 * 60 + 30) <= current_time_minutes < (15 * 60):  # 6:30 AM to 3:00 PM
        return 'A'
    elif (8 * 60 + 30) <= current_time_minutes < (17 * 60):  # 8:30 AM to 5:00 PM
        return 'G'
    elif (15 * 60) <= current_time_minutes < (23 * 60 + 30):  # 3:00 PM to 11:30 PM
        return 'B'
    elif current_time_minutes >= (23 * 60 + 30) or current_time_minutes < (6 * 60 + 30):  # 11:30 PM to 6:30 AM
        return 'C'
    elif (6 * 60 + 30) <= current_time_minutes < (18 * 60 + 30):  # 6:30 AM to 6:30 PM
        return 'S1'
    else:  # 6:30 PM to 6:30 AM
        return 'S2'



def get_current_shift(user):
    """Get or create the current shift based on date and time"""
    from django.utils import timezone
    
    current_date = timezone.now().date()
    shift_type = get_current_shift_type()
    
    # Try to find an existing shift for today and this shift type
    try:
        shift = Shift.objects.get(date=current_date, shift_type=shift_type)
    except Shift.DoesNotExist:
        # Create a new shift if none exists
        shift_supervisor = User.objects.filter(user_type='shift_supervisor').first()
        quality_supervisor = User.objects.filter(user_type='quality_supervisor').first()
        
        if not shift_supervisor or not quality_supervisor:
            raise ValueError("Cannot create shift: No supervisors available")
        
        shift = Shift.objects.create(
            date=current_date,
            shift_type=shift_type,
            operator=user,
            shift_supervisor=shift_supervisor,
            quality_supervisor=quality_supervisor
        )
    
    return shift

class SubgroupEntryForm(forms.ModelForm):
    class Meta:
        model = SubgroupEntry
        fields = [
            # UV Vacuum Test
            'uv_vacuum_test_1', 'uv_vacuum_test_2', 'uv_vacuum_test_3', 'uv_vacuum_test_4', 'uv_vacuum_test_5',
            'uv_vacuum_test_1_comment', 'uv_vacuum_test_2_comment', 'uv_vacuum_test_3_comment', 
            'uv_vacuum_test_4_comment', 'uv_vacuum_test_5_comment',
            
            # UV Flow Value
            'uv_flow_value_1', 'uv_flow_value_2', 'uv_flow_value_3', 'uv_flow_value_4', 'uv_flow_value_5',
            'uv_flow_value_1_comment', 'uv_flow_value_2_comment', 'uv_flow_value_3_comment',
            'uv_flow_value_4_comment', 'uv_flow_value_5_comment',
            
            # Umbrella Valve Assembly
            'umbrella_valve_assembly_1', 'umbrella_valve_assembly_2', 'umbrella_valve_assembly_3', 
            'umbrella_valve_assembly_4', 'umbrella_valve_assembly_5',
            'umbrella_valve_assembly_1_comment', 'umbrella_valve_assembly_2_comment', 
            'umbrella_valve_assembly_3_comment', 'umbrella_valve_assembly_4_comment', 
            'umbrella_valve_assembly_5_comment',
            
            # UV Clip Pressing
            'uv_clip_pressing_1', 'uv_clip_pressing_2', 'uv_clip_pressing_3', 'uv_clip_pressing_4', 'uv_clip_pressing_5',
            'uv_clip_pressing_1_comment', 'uv_clip_pressing_2_comment', 'uv_clip_pressing_3_comment',
            'uv_clip_pressing_4_comment', 'uv_clip_pressing_5_comment',
            
            # Workstation Clean
            'workstation_clean',
            'workstation_clean_comment',
            
            # Bin Contamination Check
            'bin_contamination_check_1', 'bin_contamination_check_2', 'bin_contamination_check_3', 
            'bin_contamination_check_4', 'bin_contamination_check_5',
            'bin_contamination_check_1_comment', 'bin_contamination_check_2_comment',
            'bin_contamination_check_3_comment', 'bin_contamination_check_4_comment',
            'bin_contamination_check_5_comment',
            
            # Maintenance
            'is_after_maintenance', 'maintenance_comment', 'effectiveness_comment'
        ]
        
        widgets = {
            # Comment fields styling
            'uv_vacuum_test_1_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_vacuum_test_2_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_vacuum_test_3_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_vacuum_test_4_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_vacuum_test_5_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            
            'uv_flow_value_1_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_flow_value_2_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_flow_value_3_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_flow_value_4_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_flow_value_5_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            
            'umbrella_valve_assembly_1_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'umbrella_valve_assembly_2_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'umbrella_valve_assembly_3_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'umbrella_valve_assembly_4_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'umbrella_valve_assembly_5_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            
            'uv_clip_pressing_1_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_clip_pressing_2_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_clip_pressing_3_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_clip_pressing_4_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'uv_clip_pressing_5_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            
            'workstation_clean_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            
            'bin_contamination_check_1_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'bin_contamination_check_2_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'bin_contamination_check_3_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'bin_contamination_check_4_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'bin_contamination_check_5_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            
            'maintenance_comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'effectiveness_comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.checklist = kwargs.pop('checklist', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        errors = []
        
        # ONLY validate maintenance comment if checkbox is checked
        is_after_maintenance = cleaned_data.get('is_after_maintenance')
        maintenance_comment = cleaned_data.get('maintenance_comment')
        
        if is_after_maintenance and not maintenance_comment:
            errors.append('Maintenance activity description is required when marking as after maintenance')
        
        if errors:
            raise forms.ValidationError(errors)
        
        return cleaned_data
    
    
    
class NOKApprovalForm(forms.Form):
    """Form for supervisor/quality to approve NOK entries"""
    approval_type = forms.ChoiceField(
        choices=[('supervisor', 'Supervisor'), ('quality', 'Quality')],
        widget=forms.HiddenInput()
    )
    approval_comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Approval Comments"
    )
    approved = forms.BooleanField(
        required=True,
        label="I approve these NOK entries after reviewing comments"
    )


class FrequencyConfigForm(forms.ModelForm):
    """Form for configuring measurement frequency"""
    class Meta:
        model = SubgroupFrequencyConfig
        fields = '__all__'
        widgets = {
            'frequency_hours': forms.NumberInput(attrs={'min': 1, 'max': 12}),
            'max_subgroups': forms.NumberInput(attrs={'min': 1, 'max': 24}),
        }


class ChecksheetContentForm(forms.ModelForm):
    """Form for adding/editing checksheet parameters"""
    class Meta:
        model = ChecksheetContentConfig
        fields = '__all__'
        widgets = {
            'parameter_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parameter_name_hindi': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        
        
class SubgroupVerificationForm(forms.ModelForm):
    """Form for subgroup verifications"""
    class Meta:
        model = SubgroupVerification
        fields = ['status', 'comments']
    
    def __init__(self, *args, **kwargs):
        # Get the subgroup and verifier info if provided
        self.subgroup = kwargs.pop('subgroup', None)
        self.verified_by = kwargs.pop('verified_by', None)
        self.verifier_type = kwargs.pop('verifier_type', None)
        
        super().__init__(*args, **kwargs)
        
        self.fields['status'].widget.attrs.update({'class': 'form-control'})
        self.fields['comments'].widget.attrs.update({
            'class': 'form-control',
            'rows': '3'
        })
    
    def save(self, commit=True):
        """Save form with subgroup and verifier info"""
        instance = super().save(commit=False)
        
        if self.subgroup:
            instance.subgroup = self.subgroup
            
        if self.verified_by:
            instance.verified_by = self.verified_by
            
        if self.verifier_type:
            instance.verifier_type = self.verifier_type
            
        if commit:
            instance.save()
            
            # Update the subgroup entry verification status
            self.subgroup.verification_status = instance.status
            self.subgroup.save()
            
        return instance


class VerificationForm(forms.ModelForm):
    """Form for final checklist verifications"""
    class Meta:
        model = Verification
        fields = ['comments']
    
    def __init__(self, *args, **kwargs):
        # Get verification info if provided
        self.checklist = kwargs.pop('checklist', None)
        self.team_leader = kwargs.pop('team_leader', None)
        self.shift_supervisor = kwargs.pop('shift_supervisor', None)
        self.quality_supervisor = kwargs.pop('quality_supervisor', None)
        
        super().__init__(*args, **kwargs)
        
        self.fields['comments'].widget.attrs.update({
            'class': 'form-control',
            'rows': '3'
        })
    
    def save(self, commit=True):
        """Save form with verification info"""
        instance = super().save(commit=False)
        
        if self.checklist:
            instance.checklist = self.checklist
            
        if self.team_leader:
            instance.team_leader = self.team_leader
            
        if self.shift_supervisor:
            instance.shift_supervisor = self.shift_supervisor
            
        if self.quality_supervisor:
            instance.quality_supervisor = self.quality_supervisor
            
        if commit:
            instance.save()
            
            # Update the checklist status
            self.checklist.status = 'quality_approved'
            self.checklist.save()
            
        return instance


class ConcernForm(forms.ModelForm):
    """Form for concerns and actions"""
    class Meta:
        model = Concern
        exclude = ['checklist', 'subgroup', 'manufacturing_approval', 'quality_approval', 'created_at']
    
    def __init__(self, *args, **kwargs):
        # Get the checklist and/or subgroup if provided
        self.checklist = kwargs.pop('checklist', None)
        self.subgroup = kwargs.pop('subgroup', None)
        
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
            if field in ['concern_identified', 'cause_if_known', 'action_taken']:
                self.fields[field].widget.attrs.update({'rows': '3'})
    
    def save(self, commit=True):
        """Save form with checklist and subgroup info"""
        instance = super().save(commit=False)
        
        if self.checklist:
            instance.checklist = self.checklist
            
        if self.subgroup:
            instance.subgroup = self.subgroup
            
        if commit:
            instance.save()
            
        return instance


class UserRegistrationForm(UserCreationForm):
    """Form for user registration"""
    email = forms.EmailField(required=False)
    user_type = forms.ChoiceField(choices=User.USER_TYPES)
    company_id = forms.CharField(max_length=100, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'company_id', 'user_type', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form with styling"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})



from .models import (
    FTQRecord, DefectRecord, DefectType, CustomDefectType, 
    OperationNumber, TimeBasedDefectEntry, Shift, ChecklistBase, User
)


class FTQRecordForm(forms.ModelForm):
    """Form for FTQ Record model"""
    class Meta:
        model = FTQRecord
        fields = [
            'date', 'shift_type', 'model_name', 'julian_date',
            'total_inspected', 'production_per_shift'
        ]
        widgets = {
            'date': DateInput(),
            'julian_date': DateInput(),
            'total_inspected': forms.NumberInput(attrs={'min': 0}),
            'production_per_shift': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        self.verification_status = kwargs.pop('verification_status', None)
        self.user = kwargs.pop('user', None)
        
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()
        
        if not self.initial.get('julian_date'):
            self.initial['julian_date'] = timezone.now().date()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.verification_status:
            instance.verification_status = self.verification_status
            
        if self.user:
            instance.created_by = self.user
            
        if commit:
            instance.save()
            
        return instance


class TimeBasedDefectEntryForm(forms.ModelForm):
    """Form for time-based defect entry"""
    class Meta:
        model = TimeBasedDefectEntry
        fields = ['defect_type', 'recorded_at', 'count', 'notes']
        widgets = {
            'recorded_at': forms.TimeInput(attrs={'type': 'time'}),
            'count': forms.NumberInput(attrs={'min': 0}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.ftq_record = kwargs.pop('ftq_record', None)
        
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Filter defect types to only show relevant ones
        if self.ftq_record:
            operation = OperationNumber.objects.filter(number='OP#35').first()
            if operation:
                self.fields['defect_type'].queryset = DefectType.objects.filter(
                    operation_number=operation
                ).order_by('order', 'name')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.ftq_record:
            instance.ftq_record = self.ftq_record
            
        if commit:
            instance.save()
            
        return instance


class DefectRecordForm(forms.ModelForm):
    """Form for Defect Record model"""
    class Meta:
        model = DefectRecord
        fields = ['defect_type', 'count', 'notes']
        widgets = {
            'count': forms.NumberInput(attrs={'min': 0}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get the FTQ record if provided
        self.ftq_record = kwargs.pop('ftq_record', None)
        
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Filter defect types to only show relevant ones
        if self.ftq_record:
            operation = OperationNumber.objects.filter(number='OP#35').first()
            if operation:
                self.fields['defect_type'].queryset = DefectType.objects.filter(
                    operation_number=operation
                ).order_by('order', 'name')
    
    def save(self, commit=True):
        """Save form with FTQ record"""
        instance = super().save(commit=False)
        
        if self.ftq_record:
            instance.ftq_record = self.ftq_record
            
        if commit:
            instance.save()
            
            # Update FTQ record total defects
            self.ftq_record.save()  # This will trigger the calculate_total_defects method
            
        return instance



# Create a combined form for daily verification workflow
class DailyVerificationWorkflowForm(forms.Form):
    """Combined form for creating a daily verification workflow"""
    date = forms.DateField(widget=DateInput(), initial=timezone.now().date())
    
    shift_type = forms.ChoiceField(
        choices=Shift.SHIFT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    model = forms.ChoiceField(
        choices=ChecklistBase.MODEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    operator = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='operator'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    shift_supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='shift_supervisor'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    quality_supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='quality_supervisor'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set current user as default operator if applicable
        if self.user and self.user.user_type == 'operator':
            self.initial['operator'] = self.user
            
        # Set default shift based on current time
        current_hour = timezone.now().hour
        self.initial['shift_type'] = 'day' if 6 <= current_hour < 18 else 'night'


TimeBasedDefectEntryFormSet = inlineformset_factory(
    FTQRecord,
    TimeBasedDefectEntry,
    form=TimeBasedDefectEntryForm,
    extra=3,
    can_delete=True,
    fields=['defect_type', 'recorded_at', 'count', 'notes']
)


# Keep legacy formset for backward compatibility
DefectRecordFormSet = inlineformset_factory(
    FTQRecord,
    DefectRecord,
    fields=['defect_type', 'count', 'notes'],
    extra=1,
    can_delete=True
)



from django import forms
from django.utils import timezone

from .models import FTQRecord, DefectRecord, DefectType, CustomDefectType, OperationNumber

class FTQRecordEditForm(forms.ModelForm):
    """Form for editing FTQ records with time-based defects"""
    class Meta:
        model = FTQRecord
        fields = [
            'date', 'shift_type', 'model_name', 'julian_date',
            'total_inspected', 'production_per_shift'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'julian_date': forms.DateInput(attrs={'type': 'date'}),
            'total_inspected': forms.NumberInput(attrs={'min': 0}),
            'production_per_shift': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # If an instance is provided, prepare defect data
        if instance:
            self.setup_defect_data(instance)
            
    def setup_defect_data(self, ftq_record):
        """Set up data structures for defects"""
        # Get all time-based defect entries grouped by defect type
        time_entries = TimeBasedDefectEntry.objects.filter(
            ftq_record=ftq_record
        ).select_related('defect_type', 'defect_type_custom').order_by('recorded_at')
        
        # Organize by defect type
        self.defect_entries = {}
        
        for entry in time_entries:
            if entry.defect_type:
                key = f"standard_{entry.defect_type.id}"
                name = entry.defect_type.name
                defect_id = entry.defect_type.id
                is_custom = False
            else:
                key = f"custom_{entry.defect_type_custom.id}"
                name = entry.defect_type_custom.name
                defect_id = entry.defect_type_custom.id
                is_custom = True
            
            if key not in self.defect_entries:
                self.defect_entries[key] = {
                    'name': name,
                    'defect_id': defect_id,
                    'is_custom': is_custom,
                    'entries': []
                }
            
            self.defect_entries[key]['entries'].append({
                'time': entry.recorded_at,
                'count': entry.count,
                'entry_id': entry.id
            })
        
        # Get default defect types for display
        try:
            operation = OperationNumber.objects.get(number='OP#35')
            self.default_defect_types = DefectType.objects.filter(
                operation_number=operation,
                is_default=True
            ).order_by('order')[:10]
        except OperationNumber.DoesNotExist:
            self.default_defect_types = []
    
    def save(self, commit=True):
        ftq_record = super().save(commit=commit)
        
        if commit:
            # Defect entries will be saved separately via AJAX or form processing
            pass
            
        return ftq_record
  
       
class CustomDefectTypeForm(forms.ModelForm):
    """Form for Custom Defect Type model"""
    class Meta:
        model = CustomDefectType
        fields = ['name', 'operation_number']
    
    def __init__(self, *args, **kwargs):
        self.ftq_record = kwargs.pop('ftq_record', None)
        self.user = kwargs.pop('user', None)
        
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Set default operation number to OP#35
        operation = OperationNumber.objects.filter(number='OP#35').first()
        if operation:
            self.initial['operation_number'] = operation
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.ftq_record:
            instance.ftq_record = self.ftq_record
            
        if self.user:
            instance.added_by = self.user
            
        if commit:
            instance.save()
            
        return instance
            
            
            
            
            
            
class OperationNumberForm(forms.ModelForm):
    """Form for Operation Number model"""
    class Meta:
        model = OperationNumber
        fields = ['number', 'name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class DefectCategoryForm(forms.ModelForm):
    """Form for Defect Category model"""
    class Meta:
        model = DefectCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class DefectTypeForm(forms.ModelForm):
    """Form for Defect Type model"""
    class Meta:
        model = DefectType
        fields = [
            'name', 'operation_number', 'category', 'description', 
            'is_critical', 'is_default', 'order'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'order': forms.NumberInput(attrs={'min': 0}),
        }            
            
            
            
            
    
# new form for new code 
from django import forms
from django.forms import inlineformset_factory
from .models import DTPMChecklistFMA03, DTPMCheckResult, DTPMIssue

class DateInput(forms.DateInput):
    """Custom DateInput with HTML5 date type for better date pickers"""
    input_type = 'date'

class DTPMChecklistForm(forms.ModelForm):
    """Form for creating and updating DTPM checklists"""
    class Meta:
        model = DTPMChecklistFMA03
        fields = ['date', 'notes']
        widgets = {
            'date': DateInput(),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        is_supervisor = kwargs.pop('is_supervisor', False)
        super().__init__(*args, **kwargs)
        
        # Add header_image field only for supervisors
        if is_supervisor:
            self.fields['header_image'] = forms.ImageField(required=False)
            
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Make date field required
        self.fields['date'].required = True
        
        # Set initial date to today if creating a new record
        if not self.instance.pk:
            from django.utils import timezone
            self.initial['date'] = timezone.now().date()
            

class DTPMCheckResultForm(forms.ModelForm):
    """Form for individual check results with image directly included"""
    class Meta:
        model = DTPMCheckResult
        fields = ['result', 'comments', 'image']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Make the image field not required
        self.fields['image'].required = False
            

class DTPMCheckResultFormSet(forms.BaseInlineFormSet):
    """Custom formset for managing multiple check results at once"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure all forms are available even if data is not submitted
        self.queryset = DTPMCheckResult.objects.filter(checklist=self.instance).order_by('item_number')


# Create formset for handling all 7 check results at once
DTPMCheckResultInlineFormSet = inlineformset_factory(
    DTPMChecklistFMA03,
    DTPMCheckResult,
    form=DTPMCheckResultForm,
    formset=DTPMCheckResultFormSet,
    extra=0,  # No extra empty forms since we create them in the post_save signal
    can_delete=False,  # Don't allow deletion of check results
    max_num=7  # Maximum of 7 checks
)





class DTPMIssueForm(forms.ModelForm):
    """Form for reporting issues found during checks"""
    class Meta:
        model = DTPMIssue
        fields = ['description', 'priority', 'issue_image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class DTPMIssueResolveForm(forms.ModelForm):
    """Form for resolving reported issues"""
    class Meta:
        model = DTPMIssue
        fields = ['status', 'action_taken', 'resolution_image']
        widgets = {
            'action_taken': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Only allow in_progress and resolved statuses for resolution
        self.fields['status'].choices = [
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved')
        ]
    
    def save(self, commit=True):
        """Save resolution data with timestamp"""
        instance = super().save(commit=False)
        
        # Set resolution date if status is 'resolved'
        if instance.status == 'resolved' and not instance.resolution_date:
            from django.utils import timezone
            instance.resolution_date = timezone.now()
        
        if commit:
            instance.save()
        
        return instance


class DTPMChecklistFilterForm(forms.Form):
    """Form for filtering DTPM checklists in a list view"""
    date_from = forms.DateField(
        required=False, 
        widget=DateInput(attrs={'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False, 
        widget=DateInput(attrs={'class': 'form-control'})
    )
    shift = forms.ChoiceField(
        choices=[('', 'All Shifts')] + list(DTPMChecklistFMA03.SHIFT_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(DTPMChecklistFMA03.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    
        
    
#  new code     
# Forms for Error Prevention models
from django import forms
from .models import ErrorPreventionCheck, ErrorPreventionMechanismStatus, DailyVerificationStatus ,ErrorPreventionMechanism

class ErrorPreventionCheckForm(forms.ModelForm):
    """Form for creating/editing Error Prevention Check records"""
    class Meta:
        model = ErrorPreventionCheck
        fields = ['date', 'comments']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Add any comments about this EP check...'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get the verification status if provided
        self.verification_status = kwargs.pop('verification_status', None)
        self.user = kwargs.pop('user', None)
        
        super().__init__(*args, **kwargs)
        
        # Set default date to current date if not provided
        if not self.initial.get('date') and not self.instance.pk:
            self.initial['date'] = timezone.now().date()
        
        # If we have a verification status, show the model and shift as read-only info
        if self.verification_status:
            checklist = self.verification_status.checklists.first()
            if checklist:
                # Add read-only fields to display the model and shift from checklist
                self.fields['current_model_display'] = forms.CharField(
                    label='Current Model (from Checklist)',
                    initial=checklist.selected_model,
                    widget=forms.TextInput(attrs={
                        'readonly': 'readonly', 
                        'class': 'form-control',
                        'style': 'background-color: #2a2a2a; cursor: not-allowed;'
                    }),
                    required=False
                )
                self.fields['shift_display'] = forms.CharField(
                    label='Shift (from Checklist)',
                    initial=dict(ChecklistBase.SHIFTS).get(checklist.shift, checklist.shift),
                    widget=forms.TextInput(attrs={
                        'readonly': 'readonly', 
                        'class': 'form-control',
                        'style': 'background-color: #2a2a2a; cursor: not-allowed;'
                    }),
                    required=False
                )
    
    def save(self, commit=True):
        """Save form with verification status and auto-populated data"""
        instance = super().save(commit=False)
        
        if self.verification_status:
            instance.verification_status = self.verification_status
        
        # Set operator to current user if not set and user is provided
        if not instance.operator_id and self.user:
            instance.operator = self.user
            
        # Set supervisors from verification status shift if not set
        if self.verification_status and self.verification_status.shift:
            if not instance.supervisor_id:
                instance.supervisor = self.verification_status.shift.shift_supervisor
                
            if not instance.quality_supervisor_id:
                instance.quality_supervisor = self.verification_status.shift.quality_supervisor
        
        if commit:
            instance.save()  # The save method will auto-populate model and shift
        
        return instance


class ErrorPreventionMechanismStatusForm(forms.ModelForm):
    """Form for updating the status of a specific EP mechanism"""
    class Meta:
        model = ErrorPreventionMechanismStatus
        fields = ['status', 'is_not_applicable', 'comments', 'is_working', 'alternative_method']
        widgets = {
            'status': forms.Select(
                choices=ErrorPreventionMechanismStatus.OK_NG_CHOICES,
                attrs={'class': 'form-control'}
            ),
            'is_not_applicable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'comments': forms.Textarea(attrs={
                'rows': 2, 
                'class': 'form-control',
                'placeholder': 'Add comments if needed...'
            }),
            'is_working': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'alternative_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '100% Inspection By Operator'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If mechanism is linked, make is_working and alternative_method read-only
        # since they should be controlled by the master mechanism
        if self.instance and self.instance.mechanism:
            self.fields['is_working'].disabled = True
            self.fields['is_working'].help_text = "Controlled by master mechanism"
            self.fields['alternative_method'].widget.attrs['readonly'] = True
            self.fields['alternative_method'].help_text = "Controlled by master mechanism"


class ErrorPreventionStatusInlineFormSet(forms.BaseInlineFormSet):
    """Formset for handling multiple EP mechanism statuses"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False


ErrorPreventionStatusFormSet = forms.inlineformset_factory(
    ErrorPreventionCheck,
    ErrorPreventionMechanismStatus,
    form=ErrorPreventionMechanismStatusForm,
    formset=ErrorPreventionStatusInlineFormSet,
    extra=0,
    can_delete=False
)


class ErrorPreventionFilterForm(forms.Form):
    """Form for filtering Error Prevention checks"""
    date_from = forms.DateField(
        required=False, 
        label='From Date',
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'placeholder': 'Start date'
        })
    )
    date_to = forms.DateField(
        required=False, 
        label='To Date',
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'placeholder': 'End date'
        })
    )
    model = forms.ChoiceField(
        choices=[
            ('', 'All Models'),
            ('P703', 'P703'),
            ('U704', 'U704'),
            ('FD', 'FD'),
            ('SA', 'SA'),
            ('Gnome', 'Gnome')
        ],
        required=False,
        label='Model',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('pending', 'Pending'),
            ('supervisor_approved', 'Supervisor Approved'),
            ('quality_approved', 'Quality Approved'),
            ('rejected', 'Rejected'),
        ],
        required=False,
        label='Status',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    shift = forms.ChoiceField(
        choices=[('', 'All Shifts')] + ErrorPreventionCheck.SHIFTS,
        required=False,
        label='Shift',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    operator = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='operator'),
        required=False,
        label='Operator',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Operators'
    )


class ErrorPreventionWorkflowForm(forms.Form):
    """Combined form for creating a daily verification workflow with EP check"""
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date(),
        label='Date'
    )
    
    shift_type = forms.ChoiceField(
        choices=Shift.SHIFT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Shift'
    )
    
    operator = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='operator', is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Operator'
    )
    
    shift_supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='shift_supervisor', is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Production Supervisor',
        required=False
    )
    
    quality_supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='quality_supervisor', is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Quality Supervisor',
        required=False
    )
    
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'class': 'form-control',
            'placeholder': 'Add any initial comments...'
        }),
        label='Comments'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set current user as default operator if applicable
        if self.user and self.user.user_type == 'operator':
            self.initial['operator'] = self.user
            self.fields['operator'].widget.attrs['readonly'] = True
            
        # Set default shift based on current time
        from main.utils import get_current_shift_type
        current_shift_type = get_current_shift_type()
        if current_shift_type:
            self.initial['shift_type'] = current_shift_type
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        shift_type = cleaned_data.get('shift_type')
        
        # Check if a verification status already exists for this date and shift
        if date and shift_type:
            existing = DailyVerificationStatus.objects.filter(
                date=date,
                shift__shift_type=shift_type
            ).exists()
            
            if existing:
                raise forms.ValidationError(
                    f"A verification status already exists for {date} - {shift_type}"
                )
        
        return cleaned_data    
    
    
    
# new code 
from django import forms
from django.forms import inlineformset_factory
from .models import DTPMChecklistFMA03New, DTPMCheckResultNew, DTPMIssueNew

class DateInput(forms.DateInput):
    """Custom DateInput with HTML5 date type for better date pickers"""
    input_type = 'date'

# Add to your forms.py

from django import forms
from .models import DTPMChecklistFMA03New, DTPMCheckResultNew, ChecklistBase

class DTPMChecklistFMA03NewForm(forms.ModelForm):
    """Form for creating and updating DTPM checklists - Dynamic Version"""
    class Meta:
        model = DTPMChecklistFMA03New
        fields = ['date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        verification_status = kwargs.pop('verification_status', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply styling
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Set initial date
        if not self.instance.pk:
            from django.utils import timezone
            self.initial['date'] = timezone.now().date()
            
            if verification_status:
                self.instance.verification_status = verification_status
            if user:
                self.instance.operator = user
        
        # Show model and shift info
        if verification_status:
            checklist = verification_status.checklists.first()
            if checklist:
                self.fields['current_model_display'] = forms.CharField(
                    label='Current Model',
                    initial=checklist.selected_model,
                    widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
                    required=False
                )
                self.fields['shift_display'] = forms.CharField(
                    label='Shift',
                    initial=dict(ChecklistBase.SHIFTS).get(checklist.shift, checklist.shift),
                    widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
                    required=False
                )



class DTPMCheckResultNewForm(forms.ModelForm):
    """Form for updating checkpoint status (OK/NG)"""
    class Meta:
        model = DTPMCheckResultNew
        fields = ['status', 'comments']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply bootstrap styling
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Make the checkpoint info available in the template
        if self.instance and self.instance.pk:
            self.checkpoint_info = {
                'number': self.instance.checkpoint_number,
                'description': dict(DTPMChecklistFMA03New.CHECKPOINT_CHOICES).get(
                    self.instance.checkpoint_number, ''
                )
            }


class DTPMCheckResultNewFormSet(forms.BaseInlineFormSet):
    """Custom formset for managing multiple checkpoint results at once"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure all forms are available even if data is not submitted
        self.queryset = DTPMCheckResultNew.objects.filter(
            checklist=self.instance
        ).order_by('checkpoint_number')


# Create formset for handling all 7 checkpoint results at once
DTPMCheckResultNewInlineFormSet = forms.inlineformset_factory(
    DTPMChecklistFMA03New,
    DTPMCheckResultNew,
    form=DTPMCheckResultNewForm,
    formset=DTPMCheckResultNewFormSet,
    extra=0,  # No extra empty forms since we create them in the post_save signal
    can_delete=False,  # Don't allow deletion of check results
    max_num=7  # Maximum of 7 checkpoints
)


class DTPMIssueNewForm(forms.ModelForm):
    """Form for reporting issues found during checks"""
    class Meta:
        model = DTPMIssueNew
        fields = ['description', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Make description required
        self.fields['description'].required = True


class DTPMIssueResolveNewForm(forms.ModelForm):
    """Form for resolving reported issues"""
    class Meta:
        model = DTPMIssueNew
        fields = ['status', 'action_taken']
        widgets = {
            'action_taken': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Only allow in_progress and resolved statuses for resolution
        self.fields['status'].choices = [
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved')
        ]
        
        # Make action_taken required
        self.fields['action_taken'].required = True
    
    def save(self, commit=True):
        """Save resolution data with timestamp"""
        instance = super().save(commit=False)
        
        # Set resolution date if status is 'resolved'
        if instance.status == 'resolved' and not instance.resolution_date:
            from django.utils import timezone
            instance.resolution_date = timezone.now()
        
        if commit:
            instance.save()
        
        return instance


class DTPMChecklistNewFilterForm(forms.Form):
    """Form for filtering DTPM checklists in a list view"""
    date_from = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(DTPMChecklistFMA03New.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    has_issues = forms.ChoiceField(
        choices=[
            ('', 'All Records'),
            ('yes', 'Has Issues'),
            ('no', 'No Issues'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
