"""
URL configuration for svetransport project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main import views
from svetransport import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main, name='main'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register_user, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Shipment URLs
    path('shipment/create/', views.shipment_create, name='shipment_create'),
    path('shipments/', views.shipment_list, name='shipment_list'),
    path('shipment/<int:pk>/', views.shipment_detail, name='shipment_detail'),
    path('shipment/<int:pk>/update/', views.shipment_update, name='shipment_update'),
    path('shipment/bulk-upload/', views.shipment_bulk_upload, name='shipment_bulk_upload'),
    path('shipment/bulk-labels/', views.download_labels, name='download_labels'),
    path('shipments/report/download/', views.download_shipment_report, name='shipment_report_download'),

    # Manifest URLs
    path('manifest/create/', views.create_manifest, name='create_manifest'),
    path('manifests/', views.manifest_list, name='manifest_list'),
    path('manifest/<int:pk>/', views.manifest_detail, name='manifest_detail'),
    path('manifest/<int:pk>/pdf/', views.manifest_pdf, name='manifest_pdf'),
    path('manifests/print/', views.print_manifest_list, name='print_manifest_list'),

    # Label, Notes, POD
    path('print_label/', views.print_label, name='print_label'),
    path('consignment-note/', views.consignment_note, name='consignment_note'),
    path('shipment/consignment-note/', views.generate_consignment_notes, name='download_consignment_note'),

    # POD Upload
    path('pod-upload/', views.pod_upload_search, name='pod_upload_search'),
    path('pod-upload/<int:pk>/', views.pod_upload, name='pod_upload'),

    # Tracking
    path('consignment_tracking/', views.consignment_tracking, name='tracking'),
    path('track/bulk/', views.bulk_tracking, name='bulk_tracking'),
    path('public_tracking/', views.public_tracking, name='public_tracking'),
    path('public_tracking_status/', views.public_tracking_status, name='public_tracking_status'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
