# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0006_alter_stop_photo_reference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stop',
            name='reason_short',
            field=models.TextField(blank=True),
        ),
    ]