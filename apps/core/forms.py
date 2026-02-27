from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        self.max_files = kwargs.pop("max_files", None)
        self.max_file_size_mb = kwargs.pop("max_file_size_mb", None)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned = []
        for f in data:
            cleaned_file = super().clean(f, initial)
            cleaned.append(cleaned_file)

        if self.max_files is not None and len(cleaned) > self.max_files:
            raise forms.ValidationError(f"You can upload up to {self.max_files} files.")

        if self.max_file_size_mb is not None:
            limit_bytes = int(self.max_file_size_mb * 1024 * 1024)
            for f in cleaned:
                if f.size > limit_bytes:
                    raise forms.ValidationError(
                        f"Each file must be <= {self.max_file_size_mb} MB."
                    )

        return cleaned


class ApplyForm(forms.Form):
    companies_pdf = forms.FileField(required=True)
    resume_pdf = forms.FileField(required=True)

    subject = forms.CharField(required=True, max_length=200)
    cover_letter = forms.CharField(required=True, widget=forms.Textarea(attrs={"rows": 10}))

    # Extra attachments (optional) — CV is separate above
    attachments = MultipleFileField(
        required=False,
        max_files=5,
        max_file_size_mb=10,
    )