# Generated migration for multi-sheet support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('treeapi', '0001_initial'),
    ]

    operations = [
        # Add sheet_names field to ExcelUploadTracker to store available sheets as JSON list
        migrations.AddField(
            model_name='exceluploadtracker',
            name='sheet_names',
            field=models.JSONField(blank=True, default=list),
        ),
        # Add sheet_name field to Node model to track which sheet each node belongs to
        migrations.AddField(
            model_name='node',
            name='sheet_name',
            field=models.CharField(blank=True, db_index=True, default='', max_length=255),
        ),
    ]
