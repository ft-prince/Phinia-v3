from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import User, Shift, ChecklistBase, SubgroupEntry, Verification, Concern
from datetime import timedelta

class Command(BaseCommand):
    help = 'Creates dummy data for testing'

    def handle(self, *args, **kwargs):
        # Create users
        try:
            operator = User.objects.get_or_create(
                username='operator1',
                defaults={
                    'email': 'operator1@example.com',
                    'user_type': 'operator'
                }
            )[0]
            operator.set_password('Pass@123')
            operator.save()

            shift_supervisor = User.objects.get_or_create(
                username='supervisor1',
                defaults={
                    'email': 'supervisor1@example.com',
                    'user_type': 'shift_supervisor'
                }
            )[0]
            shift_supervisor.set_password('Pass@123')
            shift_supervisor.save()

            quality_supervisor = User.objects.get_or_create(
                username='quality1',
                defaults={
                    'email': 'quality1@example.com',
                    'user_type': 'quality_supervisor'
                }
            )[0]
            quality_supervisor.set_password('Pass@123')
            quality_supervisor.save()

            # Create shift
            shift = Shift.objects.create(
                date=timezone.now().date(),
                shift_type='day',
                operator=operator,
                shift_supervisor=shift_supervisor,
                quality_supervisor=quality_supervisor
            )

            # Create checklist
            checklist = ChecklistBase.objects.create(
                shift=shift,
                status='pending',
                selected_model='P703',
                line_pressure=5.0,
                oring_condition='OK',
                uv_flow_input_pressure=13.5,
                master_verification_lvdt='OK',
                good_bad_master_verification='OK',
                test_pressure_vacuum=0.28,
                tool_alignment='OK',
                top_tool_id='FMA-03-35-T05',
                bottom_tool_id='FMA-03-35-T06',
                uv_assy_stage_id='FMA-03-35-T07',
                retainer_part_no='42001878',
                uv_clip_part_no='42000829',
                umbrella_part_no='25094588'
            )

            # Create subgroup entries
            for i in range(1, 4):
                SubgroupEntry.objects.create(
                    checklist=checklist,
                    subgroup_number=i,
                    uv_vacuum_test=-37,
                    uv_flow_value=35,
                    umbrella_valve_assembly='OK',
                    uv_clip_pressing='OK',
                    workstation_clean='Yes',
                    bin_contamination_check='Yes'
                )

            # Create verification
            Verification.objects.create(
                checklist=checklist,
                team_leader=operator,
                shift_supervisor=shift_supervisor,
                quality_supervisor=quality_supervisor,
                comments="All checks completed successfully"
            )

            # Create concern
            Concern.objects.create(
                checklist=checklist,
                concern_identified="Minor pressure fluctuation",
                cause_if_known="Air supply variation",
                action_taken="Pressure regulator adjusted"
            )

            self.stdout.write(self.style.SUCCESS('Successfully created dummy data'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating dummy data: {str(e)}'))