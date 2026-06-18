from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0002_location_unique_location_kind_and_more'),
        ('menu', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='recipeline',
            constraint=models.CheckConstraint(condition=models.Q(('qty_per_serving__gt', 0)), name='recipe_line_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='recipeversion',
            constraint=models.CheckConstraint(condition=models.Q(('effective_to__isnull', True), ('effective_from__isnull', True), ('effective_to__gt', models.F('effective_from')), _connector='OR'), name='recipe_effective_window_valid'),
        ),
    ]
