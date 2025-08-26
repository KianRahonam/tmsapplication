import openpyxl
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.template.defaultfilters import default
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from django.http import HttpResponse
import pandas as pd
from datetime import datetime  # Import datetime here

from .models import CustomUser , Shipment, Manifest, CustomerMaster, Branch, Fleet
from .forms import ManifestForm

admin.site.site_header = "SAARIGE - ADMIN"
admin.site.site_title = "SAARIGE - TMS"
admin.site.index_title = "Welcome to Transport Management System"


# -------------------- CUSTOM USER --------------------
@admin.register(CustomUser )
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'role', 'usertype', 'company_name', 'user_status', 'is_staff'
    )
    list_filter = (
        'role', 'usertype', 'user_status', 'is_staff', 'is_superuser'
    )
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'email',
                'gender', 'phone_number',
                'usertype', 'company_name'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        ('Transport Role Info', {'fields': ('role', 'user_status')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2',
                'first_name', 'last_name', 'email',
                'gender', 'phone_number',
                'usertype', 'company_name',
                'role', 'user_status',
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            ),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)


# -------------------- SHIPMENT --------------------
class ShipmentUploadForm(forms.Form):
    file = forms.FileField()


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'consignment_no','billto_customer', 'date', 'origin', 'destination',
        'vehicle_no', 'payment_mode', 'status', 'estimated_delivery_date',
        'delivery_date', 'pod_preview','pod_link_display'
    )
    list_filter = ('status', 'payment_mode', 'origin', 'destination')
    search_fields = (
        'consignment_no', 'vehicle_no', 'driver_details',
        'consignor_name', 'consignee_name', 'invoice_ref_number'
    )
    date_hierarchy = 'date'
    readonly_fields = ('pod_preview',)

    fieldsets = (
        ('Billed To', {
            'fields': ('billto_customer',)
        }),
        ('Shipment Info', {
            'fields': ('date', 'freight', 'payment_mode', 'shipment_type', 'status')
        }),
        ('Route & Vehicle', {
            'fields': ('origin', 'origin_pin', 'destination', 'destination_pin',
                       'vehicle_no', 'driver_details')
        }),
        ('Consignor (Shipper)', {
            'fields': ('consignor_name', 'consignor_address', 'consignor_contact', 'consignor_gst')
        }),
        ('Consignee (Receiver)', {
            'fields': ('consignee_name', 'consignee_address', 'consignee_contact', 'consignee_gst')
        }),
        ('Invoice & Value', {
            'fields': ('invoice_ref_number', 'ewaybill_number', 'value', 'pack_type')
        }),
        ('Delivery Info', {
            'fields': ('estimated_delivery_date', 'delivery_date')
        }),
        ('Proof of Delivery', {
            'fields': ('pod_scan', 'pod_preview')
        }),
    )

    @admin.display(description='POD Preview', ordering='pod_scan')
    def pod_preview(self, obj):
        if obj.pod_scan:
            return format_html('<a href="{}" target="_blank">View POD</a>', obj.pod_scan.url)
        return "No POD uploaded"
        
    def pod_link_display(self, obj):
        if obj.pod_link:
            return format_html('<a href="{}" target="_blank">View POD</a>', obj.pod_link)
        return "-"
    pod_link_display.short_description = "POD Link"

    change_list_template = "admin/shipment_upload.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-shipments/', self.upload_shipments, name='upload-shipments'),
            path('download-template/', self.admin_site.admin_view(self.download_template),
                 name='shipment_download_template'),
        ]
        return custom_urls + urls

    def upload_shipments(self, request):
        if request.method == "POST":
            form = ShipmentUploadForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                try:
                    if file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file)

                    created_count = 0
                    for _, row in df.iterrows():
                        # Initialize date variables
                        date = None
                        estimated_delivery_date = None
                        delivery_date = None
                        appointment_date = None

                        # Debugging: Print the row being processed
                        print(f"Processing row: {row.to_dict()}")  # Log the entire row

                        # Convert date strings to datetime objects
                        try:
                            if isinstance(row['date'], str) and row['date']:
                                date = datetime.fromisoformat(row['date'])
                            if isinstance(row['estimated_delivery_date'], str) and row['estimated_delivery_date']:
                                estimated_delivery_date = datetime.fromisoformat(row['estimated_delivery_date'])
                            if isinstance(row['delivery_date'], str) and row['delivery_date']:
                                delivery_date = datetime.fromisoformat(row['delivery_date'])
                            if isinstance(row['appointment_date'], str) and row['appointment_date']:
                                appointment_date = datetime.fromisoformat(row['appointment_date'])
                        except ValueError as e:
                            self.message_user(request,
                                              f"❌ Error in date format for row {row.get('consignment_no', 'Unknown')}: {e}",
                                              level=messages.ERROR)
                            continue  # Skip this row if there's a date format error
                        except Exception as e:
                            self.message_user(request,
                                              f"❌ Unexpected error for row {row.get('consignment_no', 'Unknown')}: {e}",
                                              level=messages.ERROR)
                            continue  # Skip this row if there's an unexpected error

                        Shipment.objects.create(
                            consignment_no=row.get('consignment_no', None),
                            date=date,
                            freight=row['freight'],
                            shipment_type=row['shipment_type'],
                            payment_mode=row['payment_mode'],
                            origin=row['origin'],
                            origin_pin=row['origin_pin'],
                            destination=row['destination'],
                            destination_pin=row['destination_pin'],
                            vehicle_no=row['vehicle_no'],
                            driver_details=row['driver_details'],
                            consignor_name=row['consignor_name'],
                            consignor_address=row['consignor_address'],
                            consignor_gst=row.get('consignor_gst', None),
                            consignor_contact=row['consignor_contact'],
                            consignee_name=row['consignee_name'],
                            consignee_address=row['consignee_address'],
                            consignee_gst=row.get('consignee_gst', None),
                            consignee_contact=row['consignee_contact'],
                            invoice_ref_number=row['invoice_ref_number'],
                            ewaybill_number=row.get('ewaybill_number', None),
                            value=row['value'],
                            no_article=row['no_article'],
                            actual_weight=row['actual_weight'],
                            charged_weight=row['charged_weight'],
                            pack_type=row['pack_type'],
                            status=row.get('status', 'Booked'),
                            estimated_delivery_date=estimated_delivery_date,
                            delivery_date=delivery_date,
                            appointment_delivery=row.get('appointment_delivery', False),
                            appointment_date=appointment_date,
                            remark=row.get('remark', None),
                            pod_link=row.get('pod_link', None),   # ✅ FIXED HERE
                        )
                        created_count += 1

                    self.message_user(request, f"✅ Successfully uploaded {created_count} shipments.",
                                      level=messages.SUCCESS)
                    return redirect("..")
                except Exception as e:
                    self.message_user(request, f"❌ Error: {e}", level=messages.ERROR)
        else:
            form = ShipmentUploadForm()

        context = {
            'form': form,
            'title': 'Upload Shipments from File',
        }
        return render(request, "admin/upload_form.html", context)

    def download_template(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Shipment Template"

        headers = [
            "consignment_no", "date", "freight", "shipment_type", "payment_mode",
            "origin", "origin_pin", "destination", "destination_pin", "vehicle_no",
            "driver_details", "consignor_name", "consignor_address", "consignor_gst", "consignor_contact",
            "consignee_name", "consignee_address", "consignee_gst", "consignee_contact",
            "invoice_ref_number", "ewaybill_number", "value", "no_article",
            "actual_weight", "charged_weight", "pack_type", "status",
            "estimated_delivery_date", "delivery_date", "pod_scan",
            "appointment_delivery", "appointment_date", "remark","pod_link"
        ]

        ws.append(headers)

        # Example row
        ws.append([
            "CN-10001", "2025-08-13", 1500.00, "LTL", "TO-PAY",
            "Bengaluru", "560001", "Chennai", "600001", "KA01AB1234",
            "John Doe", "ABC Corp", "123 Street, Bengaluru", "29ABCDE1234F1Z5", "9876543210",
            "XYZ Pvt Ltd", "456 Street, Chennai", "33FGHIJ5678L9M", "9876501234",
            "INV-001", "EWB12345", 50000.00, 10,
            100.0, 120.0, "Box", "Booked",
            "2025-08-15", "2025-08-20", "http://example.com/pod.pdf",
            False, "", "Handle with care","http://example.com/pod.pdf"
        ])

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="shipment_template.xlsx"'
        wb.save(response)
        return response


# -------------------- MANIFEST --------------------
@admin.register(Manifest)
class ManifestAdmin(admin.ModelAdmin):
    form = ManifestForm
    list_display = (
        'manifest_id', 'vehicle_no', 'origin_branch', 'destination_branch',
        'total_articles', 'total_freight', 'created_at'
    )
    search_fields = (
        'manifest_id', 'vehicle_no', 'driver_name',
        'origin_branch', 'destination_branch'
    )
    list_filter = ('origin_branch', 'destination_branch', 'created_at')
    filter_horizontal = ('shipments',)


# -------------------- CUSTOMER --------------------
@admin.register(CustomerMaster)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'city',
        'state',
        'country',
        'contact_person',
        'contact_number',
        'email_id',
        'status',
        'contract_date_from',
        'contract_date_to',
    )
    list_filter = ('status', 'state', 'country')
    search_fields = (
        'customer_id',
        'company_name',
        'gstn',
        'pan',
        'cin',
        'contact_person',
        'contact_number',
        'email_id',
    )
    ordering = ('company_name',)
    date_hierarchy = 'contract_date_from'
    readonly_fields = ()  # Add any fields you want to make readonly

    fieldsets = (
        ('Basic Info', {
            'fields': ('company_name', 'status')
        }),
        ('Address Info', {
            'fields': ('billing_address', 'city', 'pin_code', 'state', 'country')
        }),
        ('Legal Info', {
            'fields': ('gstn', 'pan', 'cin')
        }),
        ('Contact Info', {
            'fields': ('contact_person', 'contact_number', 'email_id')
        }),
        ('Contract Period', {
            'fields': ('contract_date_from', 'contract_date_to')
        }),
    )

# -------------------- BRANCH --------------------
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_code', 'name', 'city', 'state', 'phone_number', 'is_active')
    list_filter = ('state', 'is_active')
    search_fields = ('branch_code', 'name', 'city', 'state')
    ordering = ('branch_code',)


# -------------------- FLEET --------------------
@admin.register(Fleet)
class FleetMasterAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number', 'vehicle_type', 'insurance_expiry', 'fitness_certificate_expiry')
    search_fields = ('vehicle_number', 'vehicle_type')
    readonly_fields = ('insurance_expiry', 'fitness_certificate_expiry')
    ordering = ('vehicle_number',)

    fieldsets = (
        ('Vehicle Details', {
            'fields': ('vehicle_number', 'vehicle_type', 'capacity_mt', 'status')
        }),
        ('Ownership & Branch', {
            'fields': ('owner_name', 'owner_contact', 'branch')
        }),
        ('Documents', {
            'fields': ('insurance_expiry', 'fitness_certificate_expiry')
        }),
    )
