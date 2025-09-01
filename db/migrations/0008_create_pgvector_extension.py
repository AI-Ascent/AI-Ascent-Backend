# Generated manually

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('db', '0007_alter_onboardcatalog_specialization'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;"
        ),
    ]
