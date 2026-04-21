from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0005_usermembership'),
    ]

    operations = [
        migrations.AddField(
            model_name='usermembership',
            name='expiry_warning_sent',
            field=models.BooleanField(default=False),
        ),
    ]