from typing import Any
import uuid
from secrets import token_hex
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.core.checks.messages import CheckMessage
from accounts.models import Site, User
from utils.fields import LowerCharField, UpperCharField
from utils.constraints import unique_together
from simple_history.models import HistoricalRecords
from ..types import ALL_LOOKUPS


class Project(models.Model):
    code = LowerCharField(max_length=50, unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)


# TODO: Finalise and test
# This is just on the brink of exactly what I was after: a singular model for linking project, action, scope, group.
# Assuming speed not a problem, from this we can search groups by scope, action, project, without needing a group naming convention
# We do have the issue though that deleting a project will not cascade delete the groups, but I guess this is not an issue (?)
class ProjectGroup(models.Model):
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    action = LowerCharField(
        max_length=10,
        choices=[(x, x) for x in ["add", "view", "change", "delete"]],
    )
    scope = LowerCharField(max_length=50, default="base")

    class Meta:
        constraints = [
            unique_together(
                model_name="projectgroup",
                fields=["project", "scope", "action"],
            ),
        ]


# TODO: Change project to namespace? Or omit it entirely?
# TODO: Possibly some additional model, ChoiceLink, to link different names to the same set of choices?
# At the moment, to work with the filters, the field name must match the choice
class Choice(models.Model):
    project = models.ForeignKey(Project, to_field="code", on_delete=models.CASCADE)
    field = models.TextField()
    choice = models.TextField()
    is_active = models.BooleanField(default=True)
    constraints = models.ManyToManyField("Choice", related_name="reverse_constraints")

    class Meta:
        indexes = [
            models.Index(fields=["project", "field"]),
        ]
        constraints = [
            unique_together(
                model_name="choice",
                fields=["project", "field", "choice"],
            ),
        ]


def generate_cid():
    """
    Generate a random new CID.

    The CID consists of the prefix `C-` followed by 10 random hex digits.

    This means there are `16^10 = 1,099,511,627,776` CIDs to choose from.
    """
    cid = "C-" + "".join(token_hex(5).upper())

    if CID.objects.filter(cid=cid).exists():
        cid = generate_cid()

    return cid


class CID(models.Model):
    cid = UpperCharField(default=generate_cid, max_length=12, unique=True)


class BaseRecord(models.Model):
    # TODO: Make uuid primary key?
    # Stop worrying about collisions. its not going to happen m8
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    history = HistoricalRecords(inherit=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # TODO: Display sites again
    # site = models.ForeignKey(Site, to_field="code", on_delete=models.CASCADE)

    class Meta:
        default_permissions = []
        abstract = True

    @classmethod
    def check(cls, **kwargs: Any) -> list[CheckMessage]:
        errors = super().check(**kwargs)

        for field in cls._meta.get_fields():
            if field.name in ALL_LOOKUPS:
                errors.append(
                    checks.Error(
                        f"Field names must not match existing lookups.",
                        obj=field,
                    )
                )

        return errors


class ProjectRecord(BaseRecord):
    @classmethod
    def version(cls):
        raise NotImplementedError("A version number is required.")

    cid = UpperCharField(
        max_length=12,
        unique=True,
        help_text="Unique identifier for a project record. Set by Onyx.",
    )
    published_date = models.DateField(
        auto_now_add=True,
        help_text="The date the project record was published. Set by Onyx.",
    )
    suppressed = models.BooleanField(
        default=False,
        help_text="Indicator for whether a project record has been hidden from users.",
    )
    site_restricted = models.BooleanField(
        default=False,
        help_text="Indicator for whether a project record has been hidden from users not within the record's site.",
    )

    class Meta:
        default_permissions = []
        abstract = True
        indexes = [
            models.Index(fields=["published_date"]),
            models.Index(fields=["suppressed"]),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            cid = CID.objects.create()
            self.cid = cid.cid

        super().save(*args, **kwargs)


class Anonymiser(models.Model):
    hash = models.TextField(unique=True)
    identifier = UpperCharField(unique=True, max_length=12)

    class Meta:
        abstract = True

    @classmethod
    def get_identifier_prefix(cls) -> str:
        """
        Get the prefix for the identifier.
        """
        raise NotImplementedError("A prefix is required.")

    @classmethod
    def generate_identifier(cls) -> str:
        """
        Generate a random new identifier on the given `model`.

        The identifier consists of the given `prefix`, followed by a `-`, followed by 10 random hex digits.

        This means there are `16^10 = 1,099,511,627,776` identifiers to choose from for a given `model` and `prefix`.
        """

        identifier = cls.get_identifier_prefix() + "-" + "".join(token_hex(5).upper())

        if cls.objects.filter(identifier=identifier).exists():
            identifier = cls.generate_identifier()

        return identifier

    def save(self, *args, **kwargs):
        if not self.identifier:
            self.identifier = self.generate_identifier()

        super().save(*args, **kwargs)
