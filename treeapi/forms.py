from django import forms


class NoteForm(forms.Form):
    """Form for editing node notes."""
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 10,
            "class": "form-control",
            "placeholder": "Write your note here. Metadata will be inserted automatically on save.",
        }),
    )
    problem_category = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "note-problem-category",
        }),
        label="Problem Category",
    )
    problem_subcategory = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "note-problem-subcategory",
        }),
        label="Problem Sub-Category",
    )
    problem_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control",
        }),
        label="Problem Raised Date",
    )
    fault_resolved = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "id": "fault-resolved-checkbox",
        }),
        label="Fault Resolved",
    )
