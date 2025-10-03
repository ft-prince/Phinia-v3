# Import necessary modules
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta, time
from .models import ChecklistBase
from .forms import VerificationForm, UserProfileForm

# Verification Views
@login_required
@user_passes_test(lambda u: u.user_type == 'shift_supervisor')
def supervisor_verify(request, checklist_id):
    checklist = get_object_or_404(ChecklistBase, id=checklist_id)
    
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            checklist.status = 'supervisor_approved'
            checklist.supervisor_verified_at = timezone.now()
            checklist.supervisor_comments = form.cleaned_data['comments']
            checklist.save()
            
            messages.success(request, 'Checklist verified successfully')
            return redirect('supervisor_dashboard')
    else:
        form = VerificationForm()
    
    return render(request, 'main/verify_checklist.html', {
        'form': form,
        'checklist': checklist,
        'verification_type': 'Supervisor'
    })

@login_required
@user_passes_test(lambda u: u.user_type == 'quality_supervisor')
def quality_verify(request, checklist_id):
    checklist = get_object_or_404(ChecklistBase, id=checklist_id)
    
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            checklist.status = 'quality_approved'
            checklist.quality_verified_at = timezone.now()
            checklist.quality_comments = form.cleaned_data['comments']
            checklist.save()
            
            messages.success(request, 'Quality verification completed')
            return redirect('quality_dashboard')
    else:
        form = VerificationForm()
    
    return render(request, 'main/verify_checklist.html', {
        'form': form,
        'checklist': checklist,
        'verification_type': 'Quality'
    })

# Report Views
@login_required
def daily_report(request):
    date = request.GET.get('date', timezone.now().date())
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d').date()
    
    checklists = ChecklistBase.objects.filter(shift__date=date)
    
    summary = {
        'total': checklists.count(),
        'pending': checklists.filter(status='pending').count(),
        'supervisor_approved': checklists.filter(status='supervisor_approved').count(),
        'quality_approved': checklists.filter(status='quality_approved').count(),
        'rejected': checklists.filter(status='rejected').count(),
    }
    
    return render(request, 'main/reports/daily_report.html', {
        'date': date,
        'checklists': checklists,
        'summary': summary
    })

@login_required
def weekly_report(request):
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    checklists = ChecklistBase.objects.filter(
        shift__date__range=[start_date, end_date]
    ).order_by('shift__date')
    
    daily_stats = {}
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        daily_checklists = checklists.filter(shift__date=current_date)
        
        daily_stats[current_date] = {
            'total': daily_checklists.count(),
            'approved': daily_checklists.filter(status='quality_approved').count(),
            'rejected': daily_checklists.filter(status='rejected').count(),
        }
    
    return render(request, 'main/reports/weekly_report.html', {
        'start_date': start_date,
        'end_date': end_date,
        'daily_stats': daily_stats
    })

@login_required
def monthly_report(request):
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    checklists = ChecklistBase.objects.filter(
        shift__date__range=[start_date, end_date]
    )
    
    # Calculate statistics by model
    model_stats = {}
    for model in ChecklistBase.MODEL_CHOICES:
        model_checklists = checklists.filter(selected_model=model[0])
        model_stats[model[0]] = {
            'total': model_checklists.count(),
            'approved': model_checklists.filter(status='quality_approved').count(),
            'rejected': model_checklists.filter(status='rejected').count(),
        }
    
    return render(request, 'main/reports/monthly_report.html', {
        'start_date': start_date,
        'end_date': end_date,
        'model_stats': model_stats
    })

# Profile Views
@login_required
def user_profile(request):
    return render(request, 'main/profile/user_profile.html', {
        'user': request.user
    })

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'main/profile/edit_profile.html', {
        'form': form
    })

# API Views
@login_required
def validate_checklist(request):
    """API endpoint for validating checklist data"""
    if request.method == 'POST':
        data = request.POST
        errors = []
        
        # Validate line pressure
        line_pressure = float(data.get('line_pressure', 0))
        if not (4.5 <= line_pressure <= 5.5):
            errors.append("Line pressure must be between 4.5 and 5.5 bar")
        
        # Validate UV flow test pressure
        uv_pressure = float(data.get('uv_flow_test_pressure', 0))
        if not (11 <= uv_pressure <= 15):
            errors.append("UV flow test pressure must be between 11 and 15 kPa")
        
        # Validate UV vacuum test
        uv_vacuum = float(data.get('uv_vacuum_test', 0))
        if not (-43 <= uv_vacuum <= -35):
            errors.append("UV vacuum test must be between -43 and -35 kPa")
        
        return JsonResponse({
            'is_valid': len(errors) == 0,
            'errors': errors
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

