from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainer', '0018_trainerbooking_completion_email_sent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainerreview',
            name='show_on_homepage',
            field=models.BooleanField(default=False, help_text='Enable to show this review in landing page testimonials'),
        ),
    ]
