from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='thresholdconfig',
            constraint=models.CheckConstraint(condition=models.Q(('amount__gte', 0)), name='threshold_amount_nonnegative'),
        ),
    ]
