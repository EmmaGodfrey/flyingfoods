from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='location',
            constraint=models.UniqueConstraint(fields=('kind',), name='unique_location_kind'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('purchase_to_stock_factor__gt', 0)), name='product_purchase_factor_positive'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('recipe_to_stock_factor__gt', 0)), name='product_recipe_factor_positive'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('reorder_level__gte', 0)), name='product_reorder_nonnegative'),
        ),
    ]
