from django import forms

from .models import District, TransportRequest


class TransportRequestForm(forms.ModelForm):
    class Meta:
        model = TransportRequest
        fields = [
            'requester_name', 'department', 'position', 'programme_activity',
            'period_from', 'period_to', 'province', 'district',
            'destination', 'num_vehicles', 'num_drivers', 'num_passengers',
            'is_emergency',
        ]
        widgets = {
            'period_from': forms.DateInput(attrs={'type': 'date'}),
            'period_to': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # District choices depend on province; start empty and populate via HTMX or POST data.
        self.fields['district'].queryset = District.objects.none()
        if 'province' in self.data:
            try:
                province_id = int(self.data.get('province'))
                self.fields['district'].queryset = District.objects.filter(province_id=province_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['district'].queryset = District.objects.filter(province=self.instance.province)

    def clean(self):
        cleaned = super().clean()
        period_from = cleaned.get('period_from')
        period_to = cleaned.get('period_to')
        if period_from and period_to and period_to < period_from:
            raise forms.ValidationError('End date must be on or after the start date.')
        district = cleaned.get('district')
        province = cleaned.get('province')
        if district and province and district.province != province:
            raise forms.ValidationError('Selected district does not belong to the selected province.')
        return cleaned


class CoordinationAcknowledgmentForm(forms.Form):
    acknowledged = forms.BooleanField(
        required=True,
        label='I have read the coordination note and still need a separate vehicle.',
        error_messages={'required': 'You must acknowledge the coordination opportunity before submitting.'},
    )
    coordination_note = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='Reason for separate vehicle (optional)',
        help_text='Briefly explain why coordination is not possible for this trip.',
    )
