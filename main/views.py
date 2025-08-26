import csv
import io
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.template.loader import get_template

import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import inch, mm
from reportlab.graphics.barcode import code128
from xhtml2pdf import pisa

from .models import Shipment, Manifest
from .forms import (
    ShipmentForm,
    ShipmentUpdateForm,
    ManifestForm,
    CustomUserCreationForm,
    PODUploadForm
)


# ---------------------------
# Auth & Basic Pages
# ---------------------------

def main(request):
    return render(request, 'main.html')

def register_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User registered successfully.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect(reverse('login'))

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            if user.user_status == 'Active':
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Your account is inactive. Please contact admin.')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'main.html')

def dashboard(request):
    return render(request, 'dashboard.html')


# ---------------------------
# Shipments
# ---------------------------

def shipment_create(request):
    if request.method == 'POST':
        form = ShipmentForm(request.POST, request.FILES)
        if form.is_valid():
            shipment = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                redirect_url = reverse('shipment_detail', args=[shipment.id])
                return JsonResponse({'success': True, 'redirect_url': redirect_url})
            else:
                return redirect('shipment_detail', shipment.id)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: errors.get_json_data() for field, errors in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = ShipmentForm()
    return render(request, 'shipment_create.html', {'form': form, 'pagename': 'Create Shipment'})

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Shipment


@login_required
def shipment_list(request):
    if request.user.is_authenticated:
        if request.user.usertype == "Internal":
            # Internal staff/admin → see all shipments
            shipments = Shipment.objects.all().order_by('-date')
        else:
            # External staff/users → only see shipments for their company
            shipments = Shipment.objects.filter(
                billto_customer=request.user.company_name
            ).order_by('-date')
    else:
        shipments = Shipment.objects.none()  # no access for anonymous users

    return render(request, 'shipment_list.html', {
        'shipments': shipments,
        'pagename': 'Shipment List'
    })

@login_required
def download_shipment_report(request):
    user = request.user

    if user.is_superuser or user.is_staff:
        shipments = Shipment.objects.all().order_by('-date')
    else:
        shipments = Shipment.objects.filter(
            billto_customer=user.customer
        ).order_by('-date') if user.customer else Shipment.objects.none()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="shipment_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Consignment No', 'Date', 'Freight', 'Shipment Type', 'Payment Mode',
        'Origin', 'Origin Pin', 'Destination', 'Destination Pin',
        'Vehicle No', 'Driver Details',
        'Consignor Name', 'Consignor Address', 'Consignor GST', 'Consignor Contact',
        'Consignee Name', 'Consignee Address', 'Consignee GST', 'Consignee Contact',
        'Invoice Ref No', 'E-waybill No', 'Value',
        'No. of Articles', 'Actual Weight', 'Charged Weight', 'Pack Type', 'Status',
        'Estimated Delivery Date', 'Delivery Date', 'POD Scan URL'
    ])

    for s in shipments:
        writer.writerow([
            s.consignment_no,
            s.date,
            s.freight,
            s.shipment_type,
            s.payment_mode,
            s.origin,
            s.origin_pin,
            s.destination,
            s.destination_pin,
            s.vehicle_no,
            s.driver_details,
            s.consignor_name,
            s.consignor_address,
            s.consignor_gst or '',
            s.consignor_contact,
            s.consignee_name,
            s.consignee_address,
            s.consignee_gst or '',
            s.consignee_contact,
            s.invoice_ref_number,
            s.ewaybill_number or '',
            s.value,
            s.no_article,
            s.actual_weight,
            s.charged_weight,
            s.pack_type,
            s.status,
            s.estimated_delivery_date or '',
            s.delivery_date or '',
            s.pod_scan.url if getattr(s, 'pod_scan', None) else ''
        ])

    return response


def shipment_detail(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    return render(request, 'shipment_detail.html', {'shipment': shipment, 'pagename': f'Shipment Detail of {shipment.consignment_no}'})

def shipment_update(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    if request.method == 'POST':
        form = ShipmentUpdateForm(request.POST, request.FILES, instance=shipment)
        if form.is_valid():
            form.save()
            return redirect('shipment_list')
    else:
        form = ShipmentUpdateForm(instance=shipment)
    return render(request, 'shipment_update.html', {'form': form, 'shipment': shipment})

from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import HttpResponse
import pandas as pd
import csv

from .models import Shipment, CustomerMaster  # make sure CustomerMaster is imported

def shipment_bulk_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        ext = file.name.split('.')[-1].lower()
        try:
            if ext == 'csv':
                df = pd.read_csv(file)
            elif ext in ['xls', 'xlsx']:
                df = pd.read_excel(file)
            else:
                return HttpResponse("Unsupported file format", status=400)
        except Exception as e:
            return HttpResponse(f"Error reading file: {str(e)}", status=400)

        generated_data = []
        for index, row in df.iterrows():
            try:
                # --- Handle billto_customer (ForeignKey) ---
                customer_id = str(row['billto_customer']).strip() if pd.notnull(row.get('billto_customer')) else None
                billto_customer = None
                if customer_id:
                    try:
                        billto_customer = CustomerMaster.objects.get(customer_id=customer_id)
                    except CustomerMaster.DoesNotExist:
                        return HttpResponse(f"Row {index+1} failed: Customer with ID '{customer_id}' not found", status=400)

                # --- Create Shipment ---
                shipment = Shipment(
                    date=parse_date(str(row['date'])) if pd.notnull(row['date']) else timezone.now().date(),
                    freight=float(row['freight']),
                    payment_mode=row['payment_mode'],
                    shipment_type=row['shipment_type'],
                    billto_customer=billto_customer,   # ✅ fixed
                    origin=row['origin'],
                    origin_pin=str(row['origin_pin']),
                    destination=row['destination'],
                    destination_pin=str(row['destination_pin']),
                    vehicle_no=row['vehicle_no'],
                    driver_details=row['driver_details'],
                    consignor_name=row['consignor_name'],
                    consignor_address=row['consignor_address'],
                    consignor_gst=row.get('consignor_gst', ''),
                    consignor_contact=str(row['consignor_contact']),
                    consignee_name=row['consignee_name'],
                    consignee_address=row['consignee_address'],
                    consignee_gst=row.get('consignee_gst', ''),
                    consignee_contact=str(row['consignee_contact']),
                    invoice_ref_number=row['invoice_ref_number'],
                    ewaybill_number=row.get('ewaybill_number', ''),
                    value=float(row['value']),
                    no_article=int(row.get('no_article', 0)),
                    actual_weight=float(row.get('actual_weight', 0)),
                    charged_weight=float(row.get('charged_weight', 0)),
                    pack_type=row.get('pack_type', 'NA'),
                    status=row.get('status', 'Booked'),
                    estimated_delivery_date=parse_date(str(row.get('estimated_delivery_date'))) if pd.notnull(row.get('estimated_delivery_date')) else None,
                    delivery_date=parse_date(str(row.get('delivery_date'))) if pd.notnull(row.get('delivery_date')) else None
                )
                shipment.save()

                # --- Collect summary for download ---
                generated_data.append({
                    'invoice_ref_number': shipment.invoice_ref_number,
                    'consignment_no': shipment.consignment_no,
                    'date': shipment.date,
                    'origin': shipment.origin,
                    'destination': shipment.destination,
                    'freight': shipment.freight
                })
            except Exception as e:
                return HttpResponse(f"Row {index+1} failed: {str(e)}", status=500)

        # --- Return summary as CSV ---
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="uploaded_shipments.csv"'
        writer = csv.DictWriter(response, fieldnames=['invoice_ref_number', 'consignment_no', 'date', 'origin', 'destination', 'freight'])
        writer.writeheader()
        writer.writerows(generated_data)
        return response

    return render(request, 'shipment_bulk_upload.html', {'pagename': 'Bulk Upload'})


# ---------------------------
# Label, Notes, POD
# ---------------------------

def print_label(request):
    return render(request, 'shipment_print_label.html', {'pagename': 'Print Labels'})

def download_labels(request):
    if request.method == 'POST':
        consignment_input = request.POST.get('consignments')
        consignment_numbers = consignment_input.strip().split()
        shipments = Shipment.objects.filter(consignment_no__in=consignment_numbers)
        buffer = BytesIO()
        width, height = 5 * inch, 4 * inch
        p = canvas.Canvas(buffer, pagesize=(width, height))

        for shipment in shipments:
            for i in range(shipment.no_article):
                y = height - 15 * mm
                p.setFont("Helvetica-Bold", 10)
                p.drawString(10 * mm, y, "FROM:")
                y -= 5 * mm
                p.setFont("Helvetica", 9)
                p.drawString(10 * mm, y, shipment.consignor_name)
                y -= 5 * mm
                p.drawString(10 * mm, y, shipment.consignor_address[:60])
                y -= 5 * mm
                p.drawString(10 * mm, y, f"Ph: {shipment.consignor_contact}")
                y -= 10 * mm
                p.setFont("Helvetica-Bold", 10)
                p.drawString(10 * mm, y, "TO:")
                y -= 5 * mm
                p.setFont("Helvetica", 9)
                p.drawString(10 * mm, y, shipment.consignee_name)
                y -= 5 * mm
                p.drawString(10 * mm, y, shipment.consignee_address[:60])
                y -= 5 * mm
                p.drawString(10 * mm, y, f"Ph: {shipment.consignee_contact}")
                y -= 10 * mm
                p.setFont("Helvetica", 9)
                p.drawString(10 * mm, y, f"Consignment No: {shipment.consignment_no}")
                y -= 5 * mm
                p.drawString(10 * mm, y, f"Package: {i+1} of {shipment.no_article}")
                y -= 20 * mm
                barcode = code128.Code128(shipment.consignment_no, barHeight=15 * mm, barWidth=0.5)
                barcode.drawOn(p, 10 * mm, y)
                p.showPage()

        p.save()
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="shipment_labels.pdf"'})

    return HttpResponse("Only POST method allowed.")

def consignment_note(request):
    return render(request, 'consignment_notes.html', {'pagename': 'Download Consignment Notes'})

def generate_consignment_notes(request):
    consignment_nos = request.GET.get('consignments')
    if not consignment_nos:
        return HttpResponse("No consignment numbers provided.")
    consignment_nos = consignment_nos.strip().split()
    shipments = Shipment.objects.filter(consignment_no__in=consignment_nos)
    context = {'shipments': shipments, 'copy_labels': ['Consignor Copy', 'Consignee Copy']}
    template_path = 'consignment_notes_pdf.html'
    if request.GET.get('pdf') == 'yes':
        template = get_template(template_path)
        html = template.render(context)
        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), dest=result)
        if pdf.err:
            return HttpResponse('PDF generation failed', status=500)
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="consignment_notes.pdf"'
        return response
    return render(request, template_path, context)

# POD Upload
def pod_upload_search(request):
    if request.method == 'POST':
        consignment_no = request.POST.get('consignment_no')
        try:
            shipment = Shipment.objects.get(consignment_no=consignment_no)
            return redirect('pod_upload', pk=shipment.pk)
        except Shipment.DoesNotExist:
            messages.error(request, 'Consignment not found.')
    return render(request, 'pod_upload_search.html',{'pagename':"POD Upload"})

def pod_upload(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    if request.method == 'POST':
        form = PODUploadForm(request.POST, request.FILES, instance=shipment)
        if form.is_valid():
            form.save()
            messages.success(request, 'POD uploaded successfully.')
            return redirect('shipment_detail', pk=shipment.pk)
    else:
        form = PODUploadForm(instance=shipment)
    return render(request, 'pod_upload_form.html', {'form': form, 'shipment': shipment, 'pagename':"POD Upload"})


# ---------------------------
# Tracking
# ---------------------------

def consignment_tracking(request):
    return render(request, 'consignment_tracking.html')

def bulk_tracking(request):
    consignment_nos = request.GET.get('consignments')
    shipments = Shipment.objects.filter(consignment_no__in=consignment_nos.strip().split()) if consignment_nos else []
    return render(request, 'bulk_tracking.html', {'shipments': shipments,'pagename':'Bulk Consignment Tracking'})

def public_tracking(request):
    return render(request, 'public_tracking.html')

def public_tracking_status(request):
    consignment_nos = request.GET.get('consignments')
    shipments = Shipment.objects.filter(consignment_no__in=consignment_nos.strip().split()) if consignment_nos else []
    return render(request, 'public_tracking.html', {'shipments': shipments})


# ---------------------------
# Manifest
# ---------------------------

def create_manifest(request):
    if request.method == 'POST':
        form = ManifestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manifest_list')
    else:
        form = ManifestForm()
    return render(request, 'manifest_create.html', {'form': form,'pagename':'Create Manifest'})

def manifest_detail(request, pk):
    manifest = get_object_or_404(Manifest, pk=pk)
    shipments = manifest.shipments.all()
    total_articles = sum(s.no_article for s in shipments)
    total_freight = sum(s.freight for s in shipments)
    return render(request, 'manifest_detail.html', {
        'manifest': manifest,
        'total_articles': total_articles,
        'total_freight': total_freight
    })

def manifest_pdf(request, pk):
    manifest = Manifest.objects.get(pk=pk)
    template_path = 'manifest/manifest_pdf_template.html'
    context = {'manifest': manifest, 'shipments': manifest.shipments.all()}
    template = get_template(template_path)
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="manifest_{manifest.manifest_id}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation failed.')
    return response

def manifest_list(request):
    manifests = Manifest.objects.all().order_by('-created_at')
    return render(request, 'manifest_list.html', {'manifests': manifests})

def print_manifest_list(request):
    manifests = Manifest.objects.all()
    return render(request, 'print_manifest_list.html', {'manifests': manifests})
