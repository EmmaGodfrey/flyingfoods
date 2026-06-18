from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_thresholdconfig_threshold_amount_nonnegative'),
        ('inventory', '0002_initial'),
        ('masterdata', '0002_location_unique_location_kind_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='issuenote',
            constraint=models.CheckConstraint(condition=models.Q(('source', models.F('destination')), _negated=True), name='issue_locations_differ'),
        ),
        migrations.AddConstraint(
            model_name='issuenoteline',
            constraint=models.UniqueConstraint(fields=('issue_note', 'product'), name='unique_product_per_issue'),
        ),
        migrations.AddConstraint(
            model_name='issuenoteline',
            constraint=models.CheckConstraint(condition=models.Q(('qty__gt', 0)), name='issue_line_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='stockmovement',
            constraint=models.CheckConstraint(condition=models.Q(('qty_delta', 0), _negated=True), name='stock_movement_qty_nonzero'),
        ),
        migrations.AddConstraint(
            model_name='stocktakeline',
            constraint=models.CheckConstraint(condition=models.Q(('counted_qty__isnull', True), ('counted_qty__gte', 0), _connector='OR'), name='stocktake_count_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='stocktakeline',
            constraint=models.CheckConstraint(condition=models.Q(('value__gte', 0)), name='stocktake_value_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='transfer',
            constraint=models.CheckConstraint(condition=models.Q(('source', models.F('destination')), _negated=True), name='transfer_locations_differ'),
        ),
        migrations.AddConstraint(
            model_name='transfer',
            constraint=models.CheckConstraint(condition=models.Q(('total_value__gte', 0)), name='transfer_value_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='transferline',
            constraint=models.UniqueConstraint(fields=('transfer', 'product'), name='unique_product_per_transfer'),
        ),
        migrations.AddConstraint(
            model_name='transferline',
            constraint=models.CheckConstraint(condition=models.Q(('qty__gt', 0)), name='transfer_line_qty_positive'),
        ),
    ]
