from typing import Any
from django.db import models
from django.contrib.auth.models import Group
from rest_framework import exceptions
from utils.fields import (
    StrippedCharField,
    LowerCharField,
    UpperCharField,
    ChoiceField,
    YearMonthField,
)
from utils.functions import get_suggestions
from accounts.models import User
from .models import Choice, Project, ProjectRecord
from .types import OnyxType


TEXT_FIELDS = [
    models.CharField,
    models.TextField,
    StrippedCharField,
    LowerCharField,
    UpperCharField,
]


ALL_LOOKUPS = set(lookup for onyx_type in OnyxType for lookup in onyx_type.lookups)


class OnyxField:
    """
    Class for storing information on a field (and lookup) requested by a user.
    """

    __slots__ = (
        "project",
        "field_model",
        "field_path",
        "field_name",
        "field_instance",
        "field_type",
        "onyx_type",
        "required",
        "choices",
        "lookup",
    )

    def __init__(
        self,
        project: str,
        field_model: type[models.Model],
        field_path: str,
        lookup: str,
        allow_lookup: bool = False,
    ):
        self.project = project
        self.field_model = field_model
        self.field_path = field_path
        self.field_name = self.field_path.split("__")[-1]
        self.field_instance = self.field_model._meta.get_field(self.field_name)
        self.field_type = type(self.field_instance)

        if self.field_type in TEXT_FIELDS:
            self.onyx_type = OnyxType.TEXT
            self.required = not self.field_instance.blank

        elif self.field_type == ChoiceField:
            self.onyx_type = OnyxType.CHOICE
            self.required = not self.field_instance.blank
            self.choices = Choice.objects.filter(
                project=self.project,
                field=self.field_name,
            ).values_list("choice", flat=True)

        elif self.field_type == models.IntegerField:
            self.onyx_type = OnyxType.INTEGER
            self.required = not self.field_instance.null

        elif self.field_type == models.FloatField:
            self.onyx_type = OnyxType.DECIMAL
            self.required = not self.field_instance.null

        elif self.field_type == YearMonthField:
            self.onyx_type = OnyxType.DATE_YYYY_MM
            self.required = not self.field_instance.null

        elif self.field_type == models.DateField:
            self.onyx_type = OnyxType.DATE_YYYY_MM_DD
            self.required = not self.field_instance.null

        elif self.field_type == models.DateTimeField:
            self.onyx_type = OnyxType.DATETIME
            self.required = not self.field_instance.null

        elif self.field_type == models.BooleanField:
            self.onyx_type = OnyxType.BOOLEAN
            self.required = not self.field_instance.null

        elif self.field_instance.is_relation:
            self.onyx_type = OnyxType.RELATION
            self.required = not self.field_instance.null

        else:
            raise NotImplementedError(
                f"Field {self.field_type} did not match an OnyxType."
            )

        if not allow_lookup and lookup:
            raise exceptions.ValidationError("Lookups are not allowed.")

        if allow_lookup and lookup not in self.onyx_type.lookups:
            suggestions = get_suggestions(
                lookup,
                options=self.onyx_type.lookups,
                cutoff=0,
                message_prefix="Invalid lookup.",
            )

            raise exceptions.ValidationError(suggestions)

        self.lookup = lookup


class FieldHandler:
    __slots__ = "code", "model", "app_label", "action", "user", "user_fields"

    def __init__(
        self,
        project: Project,
        action: str,
        user: User,
    ) -> None:
        self.code = project.code
        model = project.content_type.model_class()
        assert model is not None
        assert issubclass(model, ProjectRecord)
        self.model = model
        self.app_label = project.content_type.app_label
        self.action = action
        self.user = user
        self.user_fields = None

    def get_fields(
        self,
        scopes: list[str] | None = None,
    ) -> list[str]:
        if scopes:
            scopes = ["base"] + scopes
        else:
            scopes = ["base"]

        groups = Group.objects.filter(
            projectgroup__project__code=self.code,
            projectgroup__action=self.action,
            projectgroup__scope__in=scopes,
        )

        permissions = [
            permission for group in groups for permission in group.permissions.all()
        ]

        fields = [permission.codename.partition("__")[2] for permission in permissions]

        return fields

    def get_user_fields(
        self,
    ) -> list[str]:
        if not self.user_fields:
            groups = self.user.groups.filter(
                projectgroup__project__code=self.code,
                projectgroup__action=self.action,
            )

            permissions = [
                permission for group in groups for permission in group.permissions.all()
            ]

            fields = [
                permission.codename.partition("__")[2] for permission in permissions
            ]
            self.user_fields = fields

        return self.user_fields

    def unknown_field_suggestions(self, field) -> str:
        suggestions = get_suggestions(
            field,
            options=self.get_user_fields(),
            message_prefix="This field is unknown.",
        )

        return suggestions

    def check_field_permissions(
        self,
        field: str,
    ):
        # Check whether the user can perform the action on the field
        field_action_permission = f"{self.app_label}.{self.action}_{self.code}__{field}"

        if not self.user.has_perm(field_action_permission):
            # If they do not have permission, check whether they can view the field
            field_view_permission = f"{self.app_label}.view_{self.code}__{field}"

            if self.action != "view" and self.user.has_perm(field_view_permission):
                # If the user has permission to view the field, return the action permission required
                raise exceptions.ValidationError(
                    f"You cannot {self.action} this field."
                )
            else:
                # If the user does not have permission, tell them it is unknown
                raise exceptions.ValidationError(self.unknown_field_suggestions(field))

    def resolve_field(
        self,
        field: str,
        allow_lookup=False,
    ) -> OnyxField:
        # Check for trailing underscore
        # This is required because if a field ends in "__"
        # Splitting will result in some funky stuff
        if field.endswith("_"):
            raise exceptions.ValidationError(self.unknown_field_suggestions(field))

        # Base model for the project
        current_model = self.model
        model_fields = {x.name: x for x in current_model._meta.get_fields()}

        # Split the field into its individual components
        # If there are multiple components, these should specify
        # a chain of relations through multiple models
        components = field.split("__")
        for i, component in enumerate(components):
            # If the current component is not known on the current model
            # Then add to unknown fields
            if component not in model_fields:
                raise exceptions.ValidationError(self.unknown_field_suggestions(field))

            # Corresponding field instance for the component
            component_instance = model_fields[component]
            field_path = "__".join(components[: i + 1])
            lookup = "__".join(components[i + 1 :])

            if lookup in ALL_LOOKUPS:
                # The field is valid, and the lookup is not sus
                # So we attempt to instantiate the field instance
                # This could fail if the lookup is not allowed for the given field

                onyx_field = OnyxField(
                    project=self.code,
                    field_model=current_model,
                    field_path=field_path,
                    lookup=lookup,
                    allow_lookup=allow_lookup,
                )

                # Check that the user can perform the given action on this field
                # Raises a ValidationError if this is not the case
                self.check_field_permissions(onyx_field.field_path)

                # Return OnyxField object
                return onyx_field

            elif component_instance.is_relation:
                # The field's 'lookup' may be remaining components in a relation
                # Move on to them
                current_model = component_instance.related_model
                assert current_model is not None
                model_fields = {x.name: x for x in current_model._meta.get_fields()}

            else:
                # Otherwise, it is unknown
                break

        raise exceptions.ValidationError(self.unknown_field_suggestions(field))

    def resolve_fields(
        self,
        fields: list[str],
        allow_lookup=False,
    ) -> dict[str, OnyxField]:
        """
        Resolves provided `fields`, determining which models they come from.

        This information is stored in `OnyxField` objects.
        """

        errors = {}
        resolved = {}

        # Resolve each field
        for field in fields:
            try:
                resolved[field] = self.resolve_field(field, allow_lookup=allow_lookup)
            except exceptions.ValidationError as e:
                errors[field] = [e.args[0]]

        if errors:
            raise exceptions.ValidationError(errors)

        return resolved


def generate_fields_spec(
    fields_dict: dict,
    onyx_fields: dict[str, OnyxField],
    prefix: str | None = None,
) -> dict[str, Any]:
    """
    Annote `fields_dict` with information from `onyx_fields`.

    This information includes the front-facing type name, required status, and restricted choices for each field.

    Args:
        fields_dict: The nested dictionary structure containing fields to annotate.
        onyx_fields: The dictionary of `OnyxField` objects to use for annotation.
        prefix: The prefix to use for the field paths.

    Returns:
        The annotated dictionary of fields.
    """

    for field, nested in fields_dict.items():
        if prefix:
            field_path = f"{prefix}__{field}"
        else:
            field_path = field

        if nested:
            onyx_type = onyx_fields[field_path].onyx_type
            required = onyx_fields[field_path].required
            generate_fields_spec(
                fields_dict=nested,
                onyx_fields=onyx_fields,
                prefix=field_path,
            )
            fields_dict[field] = {
                "type": onyx_type.label,
                "required": required,
                "fields": nested,
            }
        else:
            onyx_type = onyx_fields[field_path].onyx_type
            field_instance = onyx_fields[field_path].field_instance
            required = onyx_fields[field_path].required

            if onyx_type == OnyxType.CHOICE:
                choices = onyx_fields[field_path].choices
                fields_dict[field] = {
                    "description": field_instance.help_text,
                    "type": onyx_type.label,
                    "required": required,
                    "values": choices,
                }
            else:
                fields_dict[field] = {
                    "description": field_instance.help_text,
                    "type": onyx_type.label,
                    "required": required,
                }

    return fields_dict


# TODO: This function feels very hacky.
# A lack of type-checking is required on obj in order for request.data to pass.
# Which does make me wonder: is this robust against whatever could be provided through request.data?
# E.g. how sure are we that all 'fields' have been flattened from obj?
def flatten_fields(obj) -> list[str]:
    """
    Flatten a JSON-like `obj` into a list of dunderised keys.

    Args:
        obj: The JSON-like object to flatten.

    Returns:
        The flattened list of dunderised keys.
    """

    dunders = []
    if isinstance(obj, dict):
        for key, item in obj.items():
            # TODO: An ugly but effective fix until I come up with a more elegant solution
            # Basically just want to prevent any dunder separators in keys
            # Long-term would be nice to not need the flatten_fields function, and check perms recursively
            if "__" in key:
                raise exceptions.ValidationError(
                    {
                        "detail": "Field names in request body cannot contain '__' separator."
                    }
                )
            prefix = key
            values = flatten_fields(item)

            if values:
                for v in values:
                    dunders.append(f"{prefix}__{v}")
            else:
                dunders.append(prefix)
    elif isinstance(obj, list):
        for item in obj:
            values = flatten_fields(item)

            for v in values:
                dunders.append(v)
    else:
        return []

    return list(set(dunders))


def unflatten_fields(
    fields: list[str],
) -> dict[str, Any]:
    """
    Unflatten `fields` by splitting on double underscores to form a nested dictionary.

    Args:
        fields: The list of fields to unflatten.

    Returns:
        The unflattened nested dictionary.
    """

    fields_dict = {}

    for field in fields:
        field_pieces = field.split("__")

        if field_pieces:
            current_dict = fields_dict

            for piece in field_pieces:
                if not piece:
                    # Ignore empty strings
                    # These come from permissions where there is no field attached
                    # So there is no __ to split on
                    break

                current_dict.setdefault(piece, {})
                current_dict = current_dict[piece]

    return fields_dict


def include_exclude_fields(
    fields: list[str],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    """
    Filters `fields` to only include/exclude those specified in `include`/`exclude`.

    Args:
        fields: The list of fields to filter.
        include: The list of fields to include. If None, all fields are included.
        exclude: The list of fields to exclude. If None, no fields are excluded.

    Returns:
        The filtered list of fields.
    """

    if include:
        # Include fields that match or are connected by a double underscore to any of the provided inclusion values
        fields = [
            field
            for field in fields
            if any(field == inc or field.startswith(inc + "__") for inc in include)
        ]

    if exclude:
        # Exclude fields that match or are connected by a double underscore to any of the provided exclusion values
        fields = [
            field
            for field in fields
            if not any(field == exc or field.startswith(exc + "__") for exc in exclude)
        ]

    return fields
