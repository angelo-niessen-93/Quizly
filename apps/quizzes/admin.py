"""Manage complete quizzes and individual questions without shape changes."""

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, ModelForm

from .models import Answer, Question, Quiz


class AnswerForm(ModelForm):
    def _get_validation_exclusions(self):
        """Validate the solution across all choices instead of per row."""
        return super()._get_validation_exclusions() | {'is_correct'}


class AnswerFormSet(BaseInlineFormSet):
    def clean(self):
        """Require four distinct answers and exactly one correct solution."""
        super().clean()
        if any(self.errors):
            return
        answers = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE')
        ]
        validate_admin_answers(answers)

    def save(self, commit=True):
        """Remove the prior solution before saving a changed correct answer."""
        if commit:
            chosen = next(
                form.instance
                for form in self.forms
                if form.cleaned_data.get('is_correct')
            )
            self.instance.answers.filter(is_correct=True).exclude(
                pk=chosen.pk
            ).update(is_correct=False)
        return super().save(commit=commit)


class AnswerInline(admin.TabularInline):
    model = Answer
    form = AnswerForm
    formset = AnswerFormSet
    extra = 0
    min_num = 4
    max_num = 4
    validate_min = True
    validate_max = True
    can_delete = False
    readonly_fields = ['position']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    can_delete = False
    show_change_link = True
    readonly_fields = ['position', 'question']

    def has_add_permission(self, request, obj=None):
        """Keep the quiz's ten-question structure intact."""
        return False


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'created_at']
    search_fields = ['title', 'owner__username']
    list_filter = ['created_at']
    readonly_fields = ['owner', 'video_url', 'created_at', 'updated_at']
    inlines = [QuestionInline]

    def has_add_permission(self, request):
        """Create complete content through the validated API."""
        return False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question', 'quiz', 'position']
    list_filter = ['quiz']
    search_fields = ['question', 'quiz__title']
    readonly_fields = ['quiz', 'position', 'created_at', 'updated_at']
    inlines = [AnswerInline]

    def has_add_permission(self, request):
        """Prevent partial quizzes through standalone question creation."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve ten questions by deleting quizzes as a whole."""
        return False


def validate_admin_answers(answers):
    """Apply the four-choice and single-solution rule to admin form data."""
    if (
        len(answers) != 4
        or sum(a.get('is_correct', False) for a in answers) != 1
    ):
        raise ValidationError('Provide four answers and one correct solution.')
    if len({a['text'].strip().casefold() for a in answers}) != 4:
        raise ValidationError('Answer texts must be distinct.')
