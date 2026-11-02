"""Initialize the unmanaged Users table and one local demo login safely."""

import json
import secrets

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from authentication.models import Users


DEMO_USER_ID = "demo-product-service"
DEMO_EMAIL = "demo.product@local.invalid"
DEMO_PHONE = "demo-product-service"


class Command(BaseCommand):
    help = "Create the unmanaged Users table and a local demo account without replacing existing data."

    def handle(self, *args, **options):
        db_path = settings.DATABASES["default"]["NAME"]
        db_path.parent.mkdir(parents=True, exist_ok=True)
        credentials_path = db_path.parent / "auth_demo_credentials.txt"

        if Users._meta.db_table not in connection.introspection.table_names():
            with connection.schema_editor() as editor:
                editor.create_model(Users)
            self.stdout.write("Created Users table.")
        else:
            existing_columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    connection.cursor(), Users._meta.db_table
                )
            }
            required_columns = {field.column for field in Users._meta.concrete_fields}
            if not required_columns <= existing_columns:
                raise CommandError("Existing Users table does not match the Auth Service model.")

        demo_exists = Users.objects.filter(userid=DEMO_USER_ID).exists()
        credentials_exist = credentials_path.exists()
        if demo_exists and credentials_exist:
            self.stdout.write("Demo account and local credentials already exist; no changes made.")
            return
        if demo_exists or credentials_exist:
            raise CommandError(
                "Demo account and credentials file are out of sync; no existing data was changed."
            )
        if Users.objects.filter(email=DEMO_EMAIL).exists() or Users.objects.filter(phone=DEMO_PHONE).exists():
            raise CommandError("Demo email or phone is already in use; no existing account was changed.")

        password = secrets.token_urlsafe(24)
        credentials_created = False
        try:
            with transaction.atomic():
                Users.objects.create(
                    userid=DEMO_USER_ID,
                    firstname="Demo",
                    lastname="Product Service",
                    password=make_password(password),
                    email=DEMO_EMAIL,
                    phone=DEMO_PHONE,
                    role=0,
                    status=1,
                )
                with credentials_path.open("x", encoding="utf-8") as credential_file:
                    credentials_created = True
                    json.dump({"identifier": DEMO_EMAIL, "password": password}, credential_file)
                    credential_file.write("\n")
        except Exception as exc:
            if credentials_created:
                credentials_path.unlink(missing_ok=True)
            if isinstance(exc, OSError):
                raise CommandError("Could not save local demo credentials.") from exc
            raise

        self.stdout.write("Created one demo account; local credentials are in database/auth_demo_credentials.txt.")
