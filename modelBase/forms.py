from django import forms

class IdForm(forms.Form):
    ids = forms.MultipleChoiceField(
        required=True,
        choices=[],  # Initialize with an empty list
    )

    def __init__(self, ids_list,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ids'].choices = [(id,id) for id in ids_list]

        
