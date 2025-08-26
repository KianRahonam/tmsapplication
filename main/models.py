from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
import uuid
from django.utils import timezone
from django.contrib.auth.hashers import make_password

class CustomerMaster(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    customer_id = models.CharField(max_length=50, unique=True, editable=False)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.TextField()
    city = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')

    gstn = models.CharField(max_length=20, blank=True, null=True)
    pan = models.CharField(max_length=20, blank=True, null=True)
    cin = models.CharField(max_length=30, blank=True, null=True)

    contact_person = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    email_id = models.EmailField()

    contract_date_from = models.DateField()
    contract_date_to = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = self.generate_customer_id()
        super().save(*args, **kwargs)

    def generate_customer_id(self):
        return f"CUST-{uuid.uuid4().hex[:6].upper()}"

    def __str__(self):
        return f"{self.company_name} ({self.customer_id})"


class Branch(models.Model):
    branch_code = models.CharField(max_length=20, unique=True)  # e.g., BLR001
    name = models.CharField(max_length=100)  # Branch Name
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"

    def __str__(self):
        return f"{self.name} ({self.city})"


class Fleet(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('Truck', 'Truck'),
        ('Trailer', 'Trailer'),
        ('Container', 'Container'),
        ('Tempo', 'Tempo'),
        ('Van', 'Van'),
        ('Other', 'Other'),
    ]

    vehicle_number = models.CharField(max_length=20, unique=True)  # Registration Number
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    capacity_mt = models.DecimalField(max_digits=6, decimal_places=2, help_text="Capacity in Metric Tons")
    make = models.CharField(max_length=50, blank=True, null=True)  # Manufacturer
    model = models.CharField(max_length=50, blank=True, null=True)  # Model name
    year_of_manufacture = models.PositiveIntegerField(blank=True, null=True)
    owner_name = models.CharField(max_length=100, blank=True, null=True)
    owner_contact = models.CharField(max_length=15, blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[('Active', 'Active'), ('Inactive', 'Inactive')],
        default='Active'
    )

    insurance_validity = models.DateField(blank=True, null=True)
    fitness_validity = models.DateField(blank=True, null=True)
    permit_validity = models.DateField(blank=True, null=True)
    pollution_validity = models.DateField(blank=True, null=True)

    remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def insurance_expiry(self):
        """Read-only field for admin."""
        return self.insurance_validity
    insurance_expiry.short_description = "Insurance Expiry"

    def fitness_certificate_expiry(self):
        """Read-only field for admin."""
        return self.fitness_validity
    fitness_certificate_expiry.short_description = "Fitness Certificate Expiry"

    def __str__(self):
        return f"{self.vehicle_number} - {self.vehicle_type}"


class CustomUser(AbstractUser):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Supervisor', 'Supervisor'),
        ('Co-ordinator', 'Co-ordinator'),
        ('Executive', 'Executive'),
        ('Branch Manager', 'Branch Manager'),
        ('Customer', 'Customer'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    USERTYPE_CHOICES = [
        ('Internal', 'Internal'),
        ('External', 'External'),
    ]

    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=15)
    usertype = models.CharField(max_length=10, choices=USERTYPE_CHOICES, default='Internal')

    company_name = models.ForeignKey('main.CustomerMaster', on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey('main.Branch', on_delete=models.SET_NULL, null=True, blank=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    user_status = models.CharField(max_length=8, choices=STATUS_CHOICES, default='Active')

    def save(self, *args, **kwargs):
        # If the user is being created and no password is set, assign a default password
        if not self.pk and not self.password:
            self.password = make_password('admin@2025')  # Set default password securely
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class Shipment(models.Model):
    objects = None
    PAYMENT_MODES = [
        ('TO-PAY', 'TO-PAY'),
        ('TBB', 'TBB'),
        ('PAID', 'PAID'),
        ('FOC', 'FOC'),
    ]

    STATUS_CHOICES = [
        ('Booked', 'Booked'),
        ('In Transit', 'In Transit'),
        ('Out For Delivery', 'Out For Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    SHIPMENT_TYPES = [
        ('LTL', 'LTL'),
        ('FTL', 'FTL')
    ]
    
    consignment_no = models.CharField(max_length=50, unique=True, editable=False)
    date = models.DateField(default=timezone.now)
    freight = models.DecimalField(max_digits=10, decimal_places=2)
    shipment_type = models.CharField(max_length=10, choices=SHIPMENT_TYPES)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODES)
    origin = models.CharField(max_length=100)
    origin_pin = models.CharField(max_length=6)
    destination = models.CharField(max_length=100)
    destination_pin = models.CharField(max_length=6)
    vehicle_no = models.CharField(max_length=50)
    driver_details = models.CharField(max_length=100)
    billto_customer = models.ForeignKey(
        "CustomerMaster",
        on_delete=models.CASCADE,
        to_field="customer_id",   # ✅ point to customer_id
        db_column="billto_customer",  # ✅ column in Shipment table
        related_name="shipments",
        null=True,
        blank=True,
    )

    # Consignor (Shipper)
    consignor_name = models.CharField(max_length=100)
    consignor_address = models.TextField()
    consignor_gst = models.CharField(max_length=20, blank=True, null=True)
    consignor_contact = models.CharField(max_length=20)

    # Consignee (Receiver)
    consignee_name = models.CharField(max_length=100)
    consignee_address = models.TextField()
    consignee_gst = models.CharField(max_length=20, blank=True, null=True)
    consignee_contact = models.CharField(max_length=20)

    invoice_ref_number = models.CharField(max_length=500)
    boe_num = models.TextField(default=None)
    ewaybill_number = models.CharField(max_length=500, blank=True, null=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    no_article = models.IntegerField(default=0)
    actual_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    charged_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    pack_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Booked')

    estimated_delivery_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(blank=True, null=True)
    pod_scan = models.FileField(upload_to='pod_scans/', blank=True, null=True)

    appointment_delivery = models.BooleanField(default=False)
    appointment_date = models.DateField(blank=True, null=True)

    remark = models.TextField(null=True, blank=True)
    pod_link = models.URLField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.consignment_no:
            current_year = timezone.now().year
            year_prefix = str(current_year)[2:4]

            last_shipment = Shipment.objects.filter(
                consignment_no__startswith=f"CN-{year_prefix}"
            ).order_by('-id').first()

            if last_shipment and last_shipment.consignment_no[-3:].isdigit():
                last_number = int(last_shipment.consignment_no[-3:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.consignment_no = f"CN-{year_prefix}{new_number:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.consignment_no


class Manifest(models.Model):
    manifest_id = models.CharField(max_length=100, unique=True, editable=False)
    shipments = models.ManyToManyField('Shipment', related_name='manifests')
    total_articles = models.IntegerField(default=0)
    total_freight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    origin_branch = models.CharField(max_length=100, null=True)
    destination_branch = models.CharField(max_length=100, null=True)
    vehicle_no = models.CharField(max_length=50, null=True)
    driver_name = models.CharField(max_length=100, blank=True)
    driver_contact = models.CharField(max_length=20, blank=True)
    document = models.FileField(upload_to='manifest_documents/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.manifest_id:
            year_prefix = str(timezone.now().year)[2:]
            last_manifest = Manifest.objects.filter(manifest_id__startswith=f"MF-{year_prefix}").order_by('-id').first()
            if last_manifest:
                last_number = int(last_manifest.manifest_id[-3:])
                new_number = last_number + 1
            else:
                new_number = 1
            self.manifest_id = f"MF-{year_prefix}{new_number:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.manifest_id

class VendorMaster(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    vendor_code = models.CharField(max_length=20, unique=True, editable=False)
    vendor_name = models.CharField(max_length=255)
    billing_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")

    gstn = models.CharField(max_length=20, blank=True, null=True)
    pan = models.CharField(max_length=20, blank=True, null=True)

    short_intro = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active_till = models.DateField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")

    def save(self, *args, **kwargs):
        if not self.vendor_code:
            last_vendor = VendorMaster.objects.order_by('-id').first()
            if last_vendor and last_vendor.vendor_code[-3:].isdigit():
                last_number = int(last_vendor.vendor_code[-3:])
                new_number = last_number + 1
            else:
                new_number = 1
            self.vendor_code = f"VND-{new_number:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor_name} ({self.vendor_code})"


class TripOutToVendor(models.Model):
    STATUS_CHOICES = [
        ('In-Progress', 'In-Progress'),
        ('Cancelled', 'Cancelled'),
        ('Closed', 'Closed'),
        ('Hold', 'Hold'),
    ]

    trip_id = models.CharField(max_length=20, unique=True, editable=False)
    vendor = models.ForeignKey(VendorMaster, on_delete=models.CASCADE, related_name="trips")

    vehicle_type = models.CharField(max_length=50)
    vehicle_capacity = models.DecimalField(max_digits=6, decimal_places=2, help_text="Capacity in MT")
    from_location = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    kilometer = models.DecimalField(max_digits=10, decimal_places=2)
    trip_charge = models.DecimalField(max_digits=12, decimal_places=2)
    additional_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    total_bill_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="In-Progress")

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.trip_id:
            last_trip = TripOutToVendor.objects.order_by('-id').first()
            if last_trip and last_trip.trip_id[-3:].isdigit():
                last_number = int(last_trip.trip_id[-3:])
                new_number = last_number + 1
            else:
                new_number = 1
            year_prefix = str(timezone.now().year)[2:]  # e.g. 25 for 2025
            self.trip_id = f"TRP-{year_prefix}{new_number:03d}"

        # Auto-calculate total bill if not given
        if not self.total_bill_amount:
            self.total_bill_amount = self.trip_charge + self.additional_charge

        super().save(*args, **kwargs)

    def __str__(self):
        return self.trip_id
