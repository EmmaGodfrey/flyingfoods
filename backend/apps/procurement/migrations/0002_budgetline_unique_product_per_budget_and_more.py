from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_thresholdconfig_threshold_amount_nonnegative'),
        ('masterdata', '0002_location_unique_location_kind_and_more'),
        ('procurement', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='budgetline',
            constraint=models.UniqueConstraint(fields=('budget', 'product'), name='unique_product_per_budget'),
        ),
        migrations.AddConstraint(
            model_name='budgetline',
            constraint=models.CheckConstraint(condition=models.Q(('qty__gt', 0)), name='budget_line_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='budgetline',
            constraint=models.CheckConstraint(condition=models.Q(('est_unit_cost__gte', 0)), name='budget_cost_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='grnline',
            constraint=models.UniqueConstraint(fields=('grn', 'po_line'), name='unique_po_line_per_grn'),
        ),
        migrations.AddConstraint(
            model_name='grnline',
            constraint=models.CheckConstraint(condition=models.Q(('qty_received__gt', 0)), name='grn_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='grnline',
            constraint=models.CheckConstraint(condition=models.Q(('unit_cost__gte', 0)), name='grn_cost_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='poline',
            constraint=models.UniqueConstraint(fields=('po', 'product'), name='unique_product_per_po'),
        ),
        migrations.AddConstraint(
            model_name='poline',
            constraint=models.CheckConstraint(condition=models.Q(('qty__gt', 0)), name='po_line_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='poline',
            constraint=models.CheckConstraint(condition=models.Q(('unit_price__gte', 0)), name='po_price_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='poline',
            constraint=models.CheckConstraint(condition=models.Q(('fulfilled_qty__gte', 0)), name='po_fulfilled_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='purchasebudget',
            constraint=models.CheckConstraint(condition=models.Q(('total_estimated__gte', 0)), name='budget_total_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='supplierinvoice',
            constraint=models.UniqueConstraint(fields=('supplier', 'invoice_ref'), name='unique_supplier_invoice_ref'),
        ),
        migrations.AddConstraint(
            model_name='supplierinvoice',
            constraint=models.CheckConstraint(condition=models.Q(('amount__gte', 0)), name='invoice_amount_nonnegative'),
        ),
    ]
