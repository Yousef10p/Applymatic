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
    companies_file = forms.FileField(
        required=False, 
        label="Upload Leads File",
        help_text="Accepts .pdf, .docx, .txt, .xlsx, .csv"
    )
    manual_leads_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Or paste raw text containing emails here...'}),
        required=False,
        label="Manual Text Entry"
    )
    subject = forms.CharField(max_length=255, required=True)
    cover_letter = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}), required=True)
    resume_pdf = forms.FileField(required=True, label="Resume (PDF)")
    
    # FIX: Use your custom MultipleFileField here instead of standard forms.FileField
    attachments = MultipleFileField(
        required=False, 
        label="Extra Attachments",
        max_files=5, # Optional: You can now use the custom kwargs you built!
        max_file_size_mb=10 
    )

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("companies_file")
        text = cleaned_data.get("manual_leads_text")

        # Ensure the user provides at least ONE source of leads
        if not file and not text.strip():
            raise forms.ValidationError("You must either upload a file or paste text containing emails.")
        return cleaned_data