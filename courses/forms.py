from django import forms
from django.utils.text import slugify

from .models import Course

WIDGET_INPUT = (
    'w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 '
    'text-sm text-slate-900 focus:outline-none focus:ring-2 '
    'focus:ring-violet-500/40 focus:border-violet-600 transition-all'
)
WIDGET_INPUT_PH = f'{WIDGET_INPUT} placeholder:text-slate-400'
WIDGET_FILE = (
    'w-full px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-200 '
    'text-sm text-slate-900 focus:outline-none focus:ring-2 '
    'focus:ring-violet-500/40 focus:border-violet-600 transition-all '
    'file:mr-4 file:py-1 file:px-3 file:rounded-full file:border-0 '
    'file:text-xs file:font-semibold file:bg-violet-50 '
    'file:text-violet-700 hover:file:bg-violet-100'
)
WIDGET_CHECKBOX = (
    'w-4 h-4 rounded text-violet-600 focus:ring-violet-500 border-slate-300'
)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title',
            'category',
            'level',
            'price',
            'short_description',
            'full_description',
            'thumbnail',
            'is_published',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': WIDGET_INPUT_PH,
                'placeholder': 'e.g. Distributed Systems in Rust & Go',
            }),
            'category': forms.Select(attrs={
                'class': WIDGET_INPUT,
            }),
            'level': forms.Select(attrs={
                'class': WIDGET_INPUT,
            }),
            'price': forms.NumberInput(attrs={
                'class': WIDGET_INPUT_PH,
                'placeholder': '0.00 for Free',
                'step': '0.01',
                'min': '0.00',
            }),
            'short_description': forms.Textarea(attrs={
                'class': WIDGET_INPUT_PH,
                'rows': 2,
                'placeholder': (
                    'One or two sentences summarizing the architectural '
                    'mastery track...'
                ),
            }),
            'full_description': forms.Textarea(attrs={
                'class': WIDGET_INPUT_PH,
                'rows': 5,
                'placeholder': (
                    'Comprehensive syllabus outline, prerequisites, '
                    'and learning outcomes...'
                ),
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': WIDGET_FILE,
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': WIDGET_CHECKBOX,
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Course title is required.")
        return title

    def save(self, commit=True, instructor=None):
        instance = super().save(commit=False)
        if instructor:
            instance.instructor = instructor
        if not instance.slug:
            base_slug = slugify(instance.title) or "course"
            slug = base_slug
            counter = 1
            while (
                Course.objects.filter(slug=slug)
                .exclude(pk=instance.pk).exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance
