from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0003_initial'),
        ('menu', '0002_recipeline_recipe_line_qty_positive_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=models.CheckConstraint(condition=models.Q(('qty__gt', 0)), name='order_item_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=models.CheckConstraint(condition=models.Q(('price__isnull', True), ('price__gte', 0), _connector='OR'), name='order_item_price_nonnegative'),
        ),
    ]
