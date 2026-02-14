"""
Seed Firestore with default budgeting groups and categories.
Run: python manage.py seed_firestore_budgeting
Creates collections: budgeting_groups, budgeting_categories (if not present).
"""
from django.core.management.base import BaseCommand
from budgeting.firestore_models import GroupFS, CategoryFS


DEFAULT_GROUPS = [
    ("Home", 0),
    ("Food", 1),
    ("Transportation", 2),
    ("Utilities", 3),
    ("Health", 4),
    ("Other", 5),
]

DEFAULT_CATEGORIES = [
    # (name, group_name, include_in_reports, order)
    ("Rent / Mortgage", "Home", True, 0),
    ("Maintenance", "Home", True, 1),
    ("Groceries", "Food", True, 0),
    ("Restaurants", "Food", True, 1),
    ("Fuel", "Transportation", True, 0),
    ("Public transport", "Transportation", True, 1),
    ("Electricity", "Utilities", True, 0),
    ("Water", "Utilities", True, 1),
    ("Insurance", "Health", True, 0),
    ("Medical", "Health", True, 1),
    ("Other", "Other", True, 0),
]


class Command(BaseCommand):
    help = "Seed Firestore with default budgeting groups and categories"

    def handle(self, *args, **options):
        existing_groups = {g.name: g for g in GroupFS.list_all()}
        group_ids = {}
        for name, order in DEFAULT_GROUPS:
            if name in existing_groups:
                group_ids[name] = existing_groups[name].pk
                self.stdout.write(self.style.WARNING(f"Group already exists: {name}"))
                continue
            g = GroupFS(name=name, order=order)
            g.save()
            group_ids[name] = g.pk
            self.stdout.write(self.style.SUCCESS(f"Created group: {name}"))
        existing_cat_keys = {(c.name, c.group_id) for c in CategoryFS.list_all()}
        for name, group_name, include_in_reports, order in DEFAULT_CATEGORIES:
            gid = group_ids.get(group_name)
            if not gid:
                self.stdout.write(self.style.ERROR(f"Group not found: {group_name}"))
                continue
            if (name, gid) in existing_cat_keys:
                self.stdout.write(self.style.WARNING(f"Category already exists: {name} ({group_name})"))
                continue
            c = CategoryFS(name=name, group_id=gid, include_in_reports=include_in_reports, order=order)
            c.save()
            existing_cat_keys.add((name, gid))
            self.stdout.write(self.style.SUCCESS(f"Created category: {name} ({group_name})"))
        self.stdout.write(self.style.SUCCESS("Done. Groups and categories are in Firestore."))
