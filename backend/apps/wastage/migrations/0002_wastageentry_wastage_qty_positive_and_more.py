from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_thresholdconfig_threshold_amount_nonnegative'),
        ('kitchen', '0004_orderitem_order_item_qty_positive_and_more'),
        ('masterdata', '0002_location_unique_location_kind_and_more'),
        ('wastage', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='wastageentry',
            constraint=models.CheckConstraint(condition=models.Q(('qty__gt', 0)), name='wastage_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='wastageentry',
            constraint=models.CheckConstraint(condition=models.Q(('value__gte', 0)), name='wastage_value_nonnegative'),
        ),
    ]
