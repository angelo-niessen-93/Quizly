"""Preserve existing URLs while adding the documented content timestamps."""

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [('quizzes', '0001_initial')]

    operations = [
        migrations.RenameField(
            model_name='quiz', old_name='youtube_url', new_name='video_url'
        ),
        migrations.AddField(
            model_name='quiz',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='question',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='question',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
    ]
