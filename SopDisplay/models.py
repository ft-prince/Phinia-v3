from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.core.files import File
import os
import win32com.client
import pythoncom
from PIL import Image
import win32gui
import win32con
import win32api
import time
from django.db import transaction, OperationalError



class Product(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100,null=True,blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
# models.py
class ProductMedia(models.Model):
    product = models.ForeignKey(Product, related_name='media', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to='product_media/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'mp4', 'mov', 'xlsx', 'xls'])]
    )
    pdf_version = models.FileField(upload_to='product_media/pdf_versions/', null=True, blank=True)
    duration = models.PositiveIntegerField(default=15, blank=True, help_text="Duration in seconds")

    def __str__(self):
        return f"{self.product.code} - {self.file.name}"

    def convert_excel_to_pdf(self):
        if not self.file.name.lower().endswith(('.xlsx', '.xls')):
            return

        try:
            import comtypes.client
            
            # Create PDF path
            pdf_path = os.path.join(
                os.path.dirname(self.file.path),
                f'{os.path.splitext(os.path.basename(self.file.name))[0]}.pdf'
            )

            # Initialize Excel
            excel = comtypes.client.CreateObject('Excel.Application')
            excel.Visible = False
            excel.DisplayAlerts = False

            # Open workbook
            wb = excel.Workbooks.Open(self.file.path)

            # Constants for PDF format
            xlTypePDF = 0
            xlQualityStandard = 0

            # Save as PDF
            wb.ExportAsFixedFormat(Type=xlTypePDF, Filename=pdf_path, Quality=xlQualityStandard)

            # Save to pdf_version field
            with open(pdf_path, 'rb') as pdf_file:
                self.pdf_version.save(
                    os.path.basename(pdf_path),
                    File(pdf_file),
                    save=False
                )

        except Exception as e:
            print(f"Error converting Excel to PDF: {e}")
            import traceback
            traceback.print_exc()

        finally:
            try:
                # Close workbook
                wb.Close(SaveChanges=False)
            except:
                pass

            try:
                # Quit Excel
                excel.Quit()
            except:
                pass

            # Clean up COM objects
            try:
                del wb
                del excel
            except:
                pass

            # Remove temporary PDF
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except:
                    pass            
    def save(self, *args, **kwargs):
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                with transaction.atomic():
                    is_new = self.pk is None
                    super().save(*args, **kwargs)
                    
                    if self.file.name.lower().endswith(('.xlsx', '.xls')):
                        self.convert_excel_to_pdf()
                        if self.pdf_version:
                            super().save(*args, **kwargs)
                break  # Success, exit loop
            except OperationalError as e:
                if 'database is locked' in str(e):
                    attempt += 1
                    if attempt < max_attempts:
                        time.sleep(1)  # Wait before retrying
                        continue
                raise  # Re-raise if max attempts reached or different error

    def delete(self, *args, **kwargs):
        if self.pdf_version:
            if os.path.isfile(self.pdf_version.path):
                os.remove(self.pdf_version.path)
        super().delete(*args, **kwargs)
        
                
class Station(models.Model):
    name = models.CharField(max_length=100)
    screen_name=models.CharField(max_length=300,null=True,blank=True)
    products = models.ManyToManyField(Product, related_name='stations',blank=True)
    selected_media = models.ManyToManyField(ProductMedia, related_name='stations', blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('station_detail', kwargs={'pk': self.pk})
    
