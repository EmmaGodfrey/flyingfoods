from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='kind',
            field=models.CharField(choices=[('BUDGET_APPROVED', 'Budget Approved'), ('SYNC_FAILED', 'Sync Failed'), ('LOW_STOCK', 'Low Stock'), ('ORDER_RETURNED', 'Order Returned'), ('APPROVAL_PENDING', 'Approval Pending'), ('INSUFFICIENT_STOCK', 'Insufficient Stock'), ('UNKNOWN_MENU_ITEM', 'Unknown Menu Item')], max_length=30),
        ),
    ]
