from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='main/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register_user, name='register'),

    # Dashboard URLs
    path('', views.dashboard, name='dashboard'),
    path('operator/', views.operator_dashboard, name='operator_dashboard'),
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('quality/', views.quality_dashboard, name='quality_dashboard'),

    # History URLs
    path('history/operator/', views.operator_history, name='operator_history'),
    path('history/supervisor/', views.supervisor_history, name='supervisor_history'),
    path('history/quality/', views.quality_history, name='quality_history'),
    path('checklist/<int:checklist_id>/export/', views.export_checklist_excel, name='export_checklist_excel'),
    # Checklist URLs
    path('checklist/create/', views.create_checklist, name='create_checklist'),
    path('checklist/<int:checklist_id>/', views.checklist_detail, name='checklist_detail'),
    path('checklist/<int:checklist_id>/subgroup/add/', views.add_subgroup, name='add_subgroup'),
    path('checklist/<int:checklist_id>/subgroup/<int:subgroup_id>/edit/', views.edit_subgroup, name='edit_subgroup'),  # New
    path('checklist/<int:checklist_id>/concern/add/', views.add_concern, name='add_concern'),  # New

   path('verification/<int:verification_id>/edit/', views.edit_verification, name='edit_verification'), 
    # Verification URLs
    path('checklist/<int:checklist_id>/verify/supervisor/', views.supervisor_verify, name='supervisor_verify'),
    path('checklist/<int:checklist_id>/verify/quality/', views.quality_verify, name='quality_verify'),

    # Reports URLs
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/daily/', views.daily_report, name='daily_report'),
    path('reports/weekly/', views.weekly_report, name='weekly_report'),
    path('reports/monthly/', views.monthly_report, name='monthly_report'),

    # Profile URLs
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # API URLs
    path('api/checklist/validate/', views.validate_checklist, name='validate_checklist'),
    path('api/subgroup/validate/', views.validate_subgroup, name='validate_subgroup'),  # New

    
        # User Settings URLs
    path('settings/', views.user_settings, name='user_settings'),
    path('settings/notifications/', views.notification_settings, name='notification_settings'),
    path('settings/preferences/', views.user_preferences, name='user_preferences'),
    
    path('subgroup/<int:subgroup_id>/verify/', 
         views.verify_subgroup_measurement, 
         name='verify_subgroup_measurement'),
    
path('verify-subgroup-ajax/', views.verify_subgroup_ajax, name='verify_subgroup_ajax'),



# new code 

    # Operation Number URLs
    path('operations/', views.operation_number_list, name='operation_number_list'),
    path('operations/create/', views.operation_number_create, name='operation_number_create'),
    path('operations/<int:pk>/edit/', views.operation_number_edit, name='operation_number_edit'),
    path('operations/<int:pk>/delete/', views.operation_number_delete, name='operation_number_delete'),
    
    # Defect Category URLs
    path('categories/', views.defect_category_list, name='defect_category_list'),
    path('categories/create/', views.defect_category_create, name='defect_category_create'),
    path('categories/<int:pk>/edit/', views.defect_category_edit, name='defect_category_edit'),
    path('categories/<int:pk>/delete/', views.defect_category_delete, name='defect_category_delete'),
    
    # Defect Type URLs
    path('defect-types/', views.defect_type_list, name='defect_type_list'),
    path('defect-types/create/', views.defect_type_create, name='defect_type_create'),
    path('defect-types/<int:pk>/edit/', views.defect_type_edit, name='defect_type_edit'),
    path('defect-types/<int:pk>/delete/', views.defect_type_delete, name='defect_type_delete'),
    
    # FTQ Record URLs
    path('ftq/', views.ftq_list, name='ftq_list'),
    path('ftq/create/', views.ftq_record_create, name='ftq_record_create'),
    path('ftq/<int:pk>/', views.ftq_record_detail, name='ftq_record_detail'),
    path('ftq/<int:pk>/edit/', views.ftq_record_edit, name='ftq_record_edit'),
    path('ftq/<int:pk>/verify/', views.ftq_record_verify, name='ftq_record_verify'),
    path('ftq/<int:pk>/delete/', views.ftq_record_delete, name='ftq_record_delete'),
    
    # FTQ Dashboard and Reports
    path('ftq-dashboard/', views.ftq_dashboard, name='ftq_dashboard'),
    path('ftq-report/daily/', views.ftq_report, {'report_type': 'daily'}, name='ftq_report_daily'),
    path('ftq-report/weekly/', views.ftq_report, {'report_type': 'weekly'}, name='ftq_report_weekly'),
    path('ftq-report/monthly/', views.ftq_report, {'report_type': 'monthly'}, name='ftq_report_monthly'),
    path('ftq-export/', views.export_ftq_excel, name='export_ftq_excel'),
    
    # API Routes for AJAX
    path('api/defect-types/', views.get_defect_types_by_operation, name='api_defect_types'),
    path('api/add-custom-defect/', views.add_custom_defect, name='api_add_custom_defect'),
    path('api/update-defect-count/', views.update_defect_count, name='api_update_defect_count'),
    
    
    # DTPM Checklist views
    path('dtpm/', views.dtpm_list, name='dtpm_list'),
    path('dtpm/create/', views.dtpm_create, name='dtpm_create'),
    path('dtpm/<int:pk>/', views.dtpm_detail, name='dtpm_detail'),
    path('dtpm/<int:pk>/edit/', views.dtpm_edit, name='dtpm_edit'),
    path('dtpm/<int:pk>/delete/', views.dtpm_delete, name='dtpm_delete'),
    path('dtpm/<int:pk>/edit_checks/', views.dtpm_edit_checks, name='dtpm_edit_checks'),
    path('dtpm/<int:pk>/verify/', views.dtpm_verify, name='dtpm_verify'),
    
    # DTPM Issue views
    path('dtpm/check/<int:check_id>/report-issue/', views.dtpm_report_issue, name='dtpm_report_issue'),
    path('dtpm/issue/<int:issue_id>/resolve/', views.dtpm_resolve_issue, name='dtpm_resolve_issue'),
    
    # DTPM Dashboard and exports
    path('dtpm/dashboard/', views.dtpm_dashboard, name='dtpm_dashboard'),
    path('dtpm/<int:pk>/export-excel/', views.export_dtpm_excel, name='export_dtpm_excel'),

    path('dtpm/<int:pk>/manage-images/', views.dtpm_manage_images, name='dtpm_manage_images'),





    # Error Prevention URLs
    path('ep-checks/', views.ep_check_list, name='ep_check_list'),
    path('ep-checks/create/', views.ep_check_create, name='ep_check_create'),
    path('ep-checks/<int:pk>/', views.ep_check_detail, name='ep_check_detail'),
    path('ep-checks/<int:pk>/edit/', views.ep_check_edit, name='ep_check_edit'),
    path('ep-checks/<int:pk>/edit-statuses/', views.ep_check_edit_statuses, name='ep_check_edit_statuses'),
    path('ep-checks/<int:pk>/verify-supervisor/', views.ep_check_verify_supervisor, name='ep_check_verify_supervisor'),
    path('ep-checks/<int:pk>/verify-quality/', views.ep_check_verify_quality, name='ep_check_verify_quality'),
    path('ep-checks/<int:pk>/delete/', views.ep_check_delete, name='ep_check_delete'),
    path('ep-checks/dashboard/', views.ep_check_dashboard, name='ep_check_dashboard'),
    path('ep-checks/<int:pk>/export-excel/', views.export_ep_excel, name='export_ep_excel'),
    path('ep-mechanism-status/<int:status_id>/update/', views.ep_mechanism_status_update, name='ep_mechanism_status_update'),
    
    
    
# DTPM URLs
    path('dtpm-new/', views.dtpm_new_list, name='dtpm_new_list'),
    path('dtpm-new/create/', views.dtpm_checklist_create, name='dtpm_checklist_create'),
    path('dtpm-new/<int:pk>/', views.dtpm_new_detail, name='dtpm_new_detail'),
    path('dtpm-new/<int:pk>/edit-checks/', views.dtpm_new_edit_checks, name='dtpm_new_edit_checks'),
    path('dtpm-new/<int:pk>/verify/', views.dtpm_new_verify, name='dtpm_new_verify'),
    path('dtpm-new/<int:pk>/delete/', views.dtpm_new_delete, name='dtpm_new_delete'),
    path('dtpm-new/report-issue/<int:check_id>/', views.dtpm_new_report_issue, name='dtpm_new_report_issue'),
    path('dtpm-new/resolve-issue/<int:issue_id>/', views.dtpm_new_resolve_issue, name='dtpm_new_resolve_issue'),
    path('dtpm-new/dashboard/', views.dtpm_new_dashboard, name='dtpm_new_dashboard'),
    path('reference-image/<int:checkpoint_id>/', views.serve_reference_image, name='serve_reference_image'),
    path('checkpoint-image/<int:checkpoint_id>/', views.serve_checkpoint_image, name='serve_checkpoint_image'),
    path('dtpm-images/<int:image_id>/', views.dtpm_image_view, name='dtpm_image_view'),

    # DTPM Verification URLs
    path('dtpm/new/<int:pk>/verify/', views.dtpm_new_verify, name='dtpm_new_verify'),
    path('dtpm/new/<int:pk>/supervisor-verify/', views.dtpm_new_supervisor_verify, name='dtpm_new_supervisor_verify'),
    path('dtpm/new/<int:pk>/quality-verify/', views.dtpm_new_quality_verify, name='dtpm_new_quality_verify'),

]