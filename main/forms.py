from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Shipment, Manifest, CustomUser

class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        exclude = ['delivery_date', 'pod_scan']


class ShipmentUpdateForm(forms.ModelForm):
    class Meta:
        model = Shipment
        exclude = ['consignment_no', 'date']  # Prevent editing consignment_no and date
        widgets = {
            'estimated_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }


from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'gender',
            'phone_number',
            'usertype',
            'company_name',
            'role',
            'password1',
            'password2',
        ]

    def clean(self):
        cleaned_data = super().clean()
        usertype = cleaned_data.get('usertype')
        company_name = cleaned_data.get('company_name')

        if usertype == 'External' and not company_name:
            self.add_error('company_name', 'External users must have a company assigned.')

        if usertype == 'Internal' and company_name:
            self.add_error('company_name', 'Internal users should not have a company assigned.')

        return cleaned_data


class ManifestForm(forms.ModelForm):
    class Meta:
        model = Manifest
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shipments'].widget = forms.CheckboxSelectMultiple()
        self.fields['shipments'].queryset = Shipment.objects.filter(status='Booked')

    def clean(self):
        cleaned_data = super().clean()
        shipments = cleaned_data.get('shipments')

        if shipments:
            total_articles = sum(s.no_article for s in shipments)
            total_freight = sum(s.freight for s in shipments)
            cleaned_data['total_articles'] = total_articles
            cleaned_data['total_freight'] = total_freight

        return cleaned_data


class PODUploadForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ['pod_scan', 'delivery_date']  # ✅ REMOVE 'status' from fields!
        widgets = {
            'pod_scan': forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.status = 'Delivered'  # ✅ FORCE status to Delivered
        if commit:
            instance.save()
        return instance