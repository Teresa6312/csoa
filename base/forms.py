from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.exceptions import ValidationError
from django.conf import settings


class MultipleFileInput(forms.ClearableFileInput):
    template_name = "base_weights/custom_clearable_file_input.html"
    allow_multiple_selected = True

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs["data-max-files"] = (
            settings.FILE_UPLOAD_MAX_VOLUME
        )  # Add the data attribute
        return super().render(name, value, attrs, renderer)

    def __init__(self, *args, **kwargs):
        # Accept an additional parameter for the initial file URL if needed
        self.original_required = kwargs.pop("original_required", False)
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile)):
            context["widget"]["value"] = value.name  # Set the value to the file name
            context["widget"][
                "display_value"
            ] = value.name  # Set the display value to the file name
        else:
            context["widget"]["is_initial"] = bool(
                value is not None and len(value) > 0 and value[0] is not None
            )  # Set is_initial to True if a file exists
            context["widget"]["display_value"] = (
                value
                if value is not None and len(value) > 0 and value[0] is not None
                else None
            )
        context["widget"]["required"] = self.original_required
        return context


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            if len(data) > settings.FILE_UPLOAD_MAX_VOLUME:
                raise ValidationError("You can select a maximum of 10 files.")
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class CustomClearableFileInput(forms.ClearableFileInput):
    template_name = "base_weights/custom_clearable_file_input.html"

    def __init__(self, *args, **kwargs):
        # Accept an additional parameter for the initial file URL if needed
        self.original_required = kwargs.pop("original_required", False)
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile)):
            context["widget"]["value"] = value.name  # Set the value to the file name
            context["widget"][
                "display_value"
            ] = value.name  # Set the display value to the file name
        else:
            context["widget"]["is_initial"] = bool(
                value is not None and len(value) > 0 and value[0] is not None
            )  # Set is_initial to True if a file exists
            context["widget"]["display_value"] = (
                value
                if value is not None and len(value) > 0 and value[0] is not None
                else None
            )
        context["widget"]["required"] = self.original_required
        return context


class ModelDataImportForm(forms.Form):
    file = forms.FileField(required=True)

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            if not file.name.endswith(".json") and not file.name.endswith(".JSON"):
                raise ValidationError("Only JSON files are allowed.")
        return file
