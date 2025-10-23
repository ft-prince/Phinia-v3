from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import Checksheet, ChecksheetSection, ChecksheetField, User


class Command(BaseCommand):
    help = 'Creates UV Flow Assembly Daily Verification Checksheet'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting checksheet creation...'))

        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING('Creating admin user...'))
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                user_type='operator'
            )

        # Delete existing
        deleted = Checksheet.objects.filter(name="UV Flow Assembly Daily Verification").delete()
        if deleted[0] > 0:
            self.stdout.write(self.style.WARNING(f'Deleted {deleted[0]} existing checksheet(s)'))

        with transaction.atomic():
            # Create Checksheet
            checksheet = Checksheet.objects.create(
                name="UV Flow Assembly Daily Verification",
                name_hindi="यूवी फ्लो असेंबली दैनिक सत्यापन",
                description="Daily verification checksheet for UV Flow Assembly",
                is_active=True,
                created_by=admin_user,
                applicable_models="P703,U704,FD,SA,Gnome"
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Created checksheet: {checksheet.name}'))

            # SECTION 1: Initial Setup
            section1 = ChecksheetSection.objects.create(
                checksheet=checksheet,
                name="Initial Setup",
                name_hindi="प्रारंभिक सेटअप",
                description="Initial configuration",
                order=1,
                is_active=True
            )
            
            ChecksheetField.objects.create(
                section=section1,
                label="Shift",
                label_hindi="Shift select करना है",
                field_type="dropdown",
                choices="S1 - 6:30 AM to 6:30 PM,A - 6:30 AM to 3:00 PM,G - 8:30 AM to 5:00 PM,B - 3:00 PM to 11:30 PM,C - 11:30 PM to 6:30 AM,S2 - 6:30 PM to 6:30 AM",
                is_required=True,
                order=1,
                is_active=True
            )
            
            ChecksheetField.objects.create(
                section=section1,
                label="Program selection on HMI",
                label_hindi="HMI से Program select करना है",
                field_type="dropdown",
                choices="P703,U704,FD,SA,Gnome",
                is_required=True,
                help_text="Model selection",
                help_text_hindi="मॉडल चयन",
                order=2,
                is_active=True
            )
            
            self.stdout.write(f'  ✓ Section 1: {section1.name} - {section1.fields.count()} fields')

            # SECTION 2: Standard Measurements
            section2 = ChecksheetSection.objects.create(
                checksheet=checksheet,
                name="Standard Measurements",
                name_hindi="मानक मापन",
                description="Pressure measurements",
                order=2,
                is_active=True
            )
            
            ChecksheetField.objects.create(
                section=section2,
                label="Line Pressure",
                label_hindi="लाइन प्रेशर",
                field_type="decimal",
                min_value=4.5,
                max_value=5.5,
                unit="bar",
                is_required=True,
                help_text="Range: 4.5 - 5.5 bar",
                order=1,
                is_active=True
            )
            
            ChecksheetField.objects.create(
                section=section2,
                label="UV Flow Input Test Pressure",
                label_hindi="यूवी फ्लो इनपुट टेस्ट प्रेशर",
                field_type="decimal",
                min_value=11.0,
                max_value=15.0,
                unit="kPa",
                is_required=True,
                help_text="Range: 11-15 kPa",
                order=2,
                is_active=True
            )
            
            ChecksheetField.objects.create(
                section=section2,
                label="Test Pressure for Vacuum generation",
                label_hindi="वैक्यूम जनरेशन के लिए टेस्ट प्रेशर",
                field_type="decimal",
                min_value=0.25,
                max_value=0.30,
                unit="MPa",
                is_required=True,
                help_text="Range: 0.25 - 0.3 MPa",
                order=3,
                is_active=True
            )
            
            self.stdout.write(f'  ✓ Section 2: {section2.name} - {section2.fields.count()} fields')

            # SECTION 3: Status Checks
            section3 = ChecksheetSection.objects.create(
                checksheet=checksheet,
                name="Status Checks",
                name_hindi="स्टेटस चेक",
                description="Visual checks",
                order=3,
                is_active=True
            )
            
            ChecksheetField.objects.create(
                section=section3,
                label="O-ring condition (UV Flow check sealing area)",
                label_hindi="O-ring सील की स्थिति",
                field_type="ok_nok",
                is_required=True,
                requires_comment_if_nok=True,
                help_text="Check O-ring seal",
                order=1,
                is_active=True
            )
            
            self.stdout.write(f'  ✓ Section 3: {section3.name} - {section3.fields.count()} fields')

            # SECTION 4: IDs and Part Numbers
            section4 = ChecksheetSection.objects.create(
                checksheet=checksheet,
                name="IDs and Part Numbers",
                name_hindi="आईडी और पार्ट नंबर",
                description="Tool IDs and Part numbers",
                order=4,
                is_active=True
            )
            
            # Top Tool ID
            ChecksheetField.objects.create(
                section=section4,
                label="Top Tool ID",
                label_hindi="टॉप टूल आईडी",
                field_type="text",
                default_value="FMA-03-35-T05",
                is_required=True,
                has_status_field=True,
                auto_fill_based_on_model=True,
                model_value_mapping={
                    "P703": "FMA-03-35-T05",
                    "U704": "FMA-03-35-T05",
                    "SA": "FMA-03-35-T05",
                    "FD": "FMA-03-35-T05",
                    "Gnome": "FMA-03-35-T05"
                },
                help_text="FMA-03-35-T05 for all models",
                order=1,
                is_active=True
            )
            
            # Bottom Tool ID
            ChecksheetField.objects.create(
                section=section4,
                label="Bottom Tool ID",
                label_hindi="बॉटम टूल आईडी",
                field_type="text",
                is_required=True,
                has_status_field=True,
                auto_fill_based_on_model=True,
                model_value_mapping={
                    "P703": "FMA-03-35-T06",
                    "U704": "FMA-03-35-T06",
                    "SA": "FMA-03-35-T06",
                    "FD": "FMA-03-35-T06",
                    "Gnome": "FMA-03-35-T08"
                },
                help_text="T06 or T08 based on model",
                order=2,
                is_active=True
            )
            
            # UV Assy Stage 1 ID
            ChecksheetField.objects.create(
                section=section4,
                label="UV Assy Stage 1 ID",
                label_hindi="यूवी असेंबली स्टेज 1 आईडी",
                field_type="text",
                is_required=True,
                has_status_field=True,
                auto_fill_based_on_model=True,
                model_value_mapping={
                    "P703": "FMA-03-35-T07",
                    "U704": "FMA-03-35-T07",
                    "SA": "FMA-03-35-T07",
                    "FD": "FMA-03-35-T07",
                    "Gnome": "FMA-03-35-T09"
                },
                help_text="T07 or T09 based on model",
                order=3,
                is_active=True
            )
            
            # Retainer Part No
            ChecksheetField.objects.create(
                section=section4,
                label="Retainer Part no",
                label_hindi="रिटेनर पार्ट नंबर",
                field_type="text",
                is_required=True,
                has_status_field=True,
                auto_fill_based_on_model=True,
                model_value_mapping={
                    "P703": "42001878",
                    "U704": "42001878",
                    "SA": "42001878",
                    "FD": "42001878",
                    "Gnome": "42050758"
                },
                help_text="42001878 or 42050758",
                order=4,
                is_active=True
            )
            
            # UV Clip Part No
            ChecksheetField.objects.create(
                section=section4,
                label="UV Clip Part No",
                label_hindi="यूवी क्लिप पार्ट नंबर",
                field_type="text",
                default_value="42000829",
                is_required=True,
                has_status_field=True,
                auto_fill_based_on_model=True,
                model_value_mapping={
                    "P703": "42000829",
                    "U704": "42000829",
                    "SA": "42000829",
                    "FD": "42000829",
                    "Gnome": "42000829"
                },
                help_text="42000829 for all",
                order=5,
                is_active=True
            )
            
            # Umbrella Part No
            ChecksheetField.objects.create(
                section=section4,
                label="Umbrella Part No",
                label_hindi="अम्ब्रेला पार्ट नंबर",
                field_type="text",
                default_value="25094588",
                is_required=True,
                has_status_field=True,
                auto_fill_based_on_model=True,
                model_value_mapping={
                    "P703": "25094588",
                    "U704": "25094588",
                    "SA": "25094588",
                    "FD": "25094588",
                    "Gnome": "25094588"
                },
                help_text="25094588 for all",
                order=6,
                is_active=True
            )
            
            # Retainer ID Lubrication
            ChecksheetField.objects.create(
                section=section4,
                label="Retainer ID Lubrication - Visual Check",
                label_hindi="रिटेनर आईडी लुब्रिकेशन - दृश्य जांच",
                field_type="ok_nok",
                is_required=True,
                requires_comment_if_nok=True,
                help_text="Visual inspection",
                order=7,
                is_active=True
            )
            
            self.stdout.write(f'  ✓ Section 4: {section4.name} - {section4.fields.count()} fields')

            # Summary
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('SUMMARY'))
            self.stdout.write('='*60)
            self.stdout.write(f'Checksheet: {checksheet.name}')
            self.stdout.write(f'Sections: {checksheet.sections.count()}')
            self.stdout.write(f'Total Fields: {checksheet.field_count}')
            self.stdout.write(f'Status: Active')
            self.stdout.write('='*60)
            self.stdout.write(self.style.SUCCESS('\n✅ SUCCESS! Checksheet created with all fields!\n'))