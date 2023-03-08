from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import csv


class GroupDefinition:
    def __init__(self, name, permissions):
        self.name = name
        self.permissions = permissions


def read_groups(scheme):
    with open(scheme) as scheme_fh:
        reader = csv.reader(scheme_fh)

        name = next(reader)
        if not name[0].startswith("#"):
            raise Exception("Could not read group name")

        name = name[0].removeprefix("#")
        group_permissions = []

        for entry in reader:
            if not entry:
                continue

            elif entry[0].startswith("#"):
                gdef = GroupDefinition(name=name, permissions=group_permissions)
                yield gdef

                name = entry[0].removeprefix("#")
                group_permissions = []

            else:
                group_permissions.append(entry)

    gdef = GroupDefinition(name=name, permissions=group_permissions)
    yield gdef


def create_or_update_group(gdef):
    group, created = Group.objects.get_or_create(name=gdef.name)
    permissions = []

    for perm in gdef.permissions:
        app_label, model, permission = perm
        content_type = ContentType.objects.get(app_label=app_label, model=model)
        permission = Permission.objects.get(
            content_type=content_type, codename=permission
        )
        permissions.append(permission)

    group.permissions.set(permissions)

    return group, created
