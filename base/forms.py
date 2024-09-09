from django import forms
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result
    
class HeaderingForm(forms.Form):
    headers = forms.MultipleChoiceField(choices=[], required=False)
    initial_form_value = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    def __init__(self, *args, **kwargs):
        initial_form_value = kwargs.pop('initial_form_value', '')
        super().__init__(*args, **kwargs)
        self.fields['initial_form_value'].initial = initial_form_value
