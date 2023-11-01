from typing import Any
from django.db import models
from datetime import datetime
from .models import Choice


EMPTY_VALUES = [None, ""]


def validate_optional_value_groups(
    errors: dict[str, list[str]],
    data: dict[str, Any],
    groups: list[list[str]],
    instance: type[models.Model] | None = None,
):
    """
    Ensure each group of fields has at least one non-null field.
    """

    if instance:
        for group in groups:
            # Existing fields from the group
            instance_fields = set(
                field for field in group if getattr(instance, field) not in EMPTY_VALUES
            )

            # Fields specified by the request data
            request_fields = set(
                field
                for field in group
                if field in data and data[field] not in EMPTY_VALUES
            )

            # Fields that exist/are being added
            keep_fields = instance_fields | request_fields

            # Fields specified by the request data that are going to be removed
            remove_fields = set(
                field
                for field in group
                if field in data and data[field] in EMPTY_VALUES
            )

            # If the resulting set is empty, it means one of two not-good things:
            # * The request is emptying enough fields from the group to make all fields in the group empty
            # * All fields in the group were (somehow) empty to begin with...
            if not (keep_fields - remove_fields):
                errors.setdefault("non_field_errors", []).append(
                    f"At least one of {', '.join(group)} is required."
                )
    else:
        for group in groups:
            for field in group:
                if field in data and data[field] not in EMPTY_VALUES:
                    break
            else:
                # If you're reading this I'm sorry
                # I couldn't help but try a for-else
                # I just found out it can be done, so I did it :)
                # And its dreadful
                errors.setdefault("non_field_errors", []).append(
                    f"At least one of {', '.join(group)} is required."
                )


def validate_orderings(
    errors: dict[str, list[str]],
    data: dict[str, Any],
    orderings: list[tuple[str, str]],
    instance: type[models.Model] | None = None,
):
    """
    Ensure all ordered fields have correctly ordered values.
    """

    for lower, higher in orderings:
        if instance:
            lower_value = data.get(lower, getattr(instance, lower))
            higher_value = data.get(higher, getattr(instance, higher))
        else:
            lower_value = data.get(lower)
            higher_value = data.get(higher)

        if (
            lower_value is not None
            and higher_value is not None
            and lower_value not in EMPTY_VALUES
            and higher_value not in EMPTY_VALUES
            and lower_value > higher_value
        ):
            errors.setdefault("non_field_errors", []).append(
                f"The {lower} cannot be greater than the {higher}."
            )


def validate_non_futures(
    errors: dict[str, list[str]],
    data: dict[str, Any],
    non_futures: list[str],
):
    """
    Ensure dates are not from the future.
    """

    for non_future in non_futures:
        if data.get(non_future) and data[non_future] > datetime.now().date():
            errors.setdefault(non_future, []).append("Value cannot be from the future.")


def validate_identifiers(
    errors: dict[str, list[str]],
    data: dict[str, Any],
    identifiers: list[str],
):
    """
    Ensure identifiers are provided.
    """

    for identifier in identifiers:
        if identifier not in data:
            errors.setdefault(identifier, []).append("This field is required.")


def validate_choice_constraints(
    errors: dict[str, list[str]],
    data: dict[str, Any],
    choice_constraints: list[tuple[str, str]],
    project: str,
    instance: type[models.Model] | None = None,
):
    """
    Ensure all choices are compatible with each other.
    """

    # Getting a little bit gnarly
    # This is a mapping from tuples of (field_x, choice_x)
    # to all (field_y, choice_y) tuples that are allowed to occur with said tuple
    constraints = {
        (choice.field, choice.choice): {
            (constraint.field, constraint.choice)
            for constraint in choice.constraints.all()
        }
        for choice in Choice.objects.prefetch_related("constraints")
        .filter(project_id=project)
        .filter(
            field__in=set(
                field
                for constraint_group in choice_constraints
                for field in constraint_group
            )
        )
    }

    for choice_x, choice_y in choice_constraints:
        if instance:
            choice_x_value = data.get(choice_x, getattr(instance, choice_x))
            choice_y_value = data.get(choice_y, getattr(instance, choice_y))
        else:
            choice_x_value = data.get(choice_x)
            choice_y_value = data.get(choice_y)

        if (
            choice_x_value is not None
            and choice_y_value is not None
            and choice_x_value not in EMPTY_VALUES
            and choice_y_value not in EMPTY_VALUES
            and (
                (
                    (choice_y, choice_y_value)
                    not in constraints[(choice_x, choice_x_value)]
                )
                or (
                    (choice_x, choice_x_value)
                    not in constraints[(choice_y, choice_y_value)]
                )
            )
        ):
            errors.setdefault("non_field_errors", []).append(
                f"Choices for fields {choice_x}, {choice_y} are incompatible."
            )


def validate_conditional_required(
    errors: dict[str, list[str]],
    data: dict[str, Any],
    conditional_required: dict[str, list[str]],
    instance: type[models.Model] | None = None,
):
    """
    Ensure all conditionally-required fields are provided.
    """

    for field, requirements in conditional_required.items():
        if instance:
            required_values = [
                data.get(req, getattr(instance, req)) for req in requirements
            ]
            field_value = data.get(field, getattr(instance, field))
        else:
            required_values = [data.get(req) for req in requirements]
            field_value = data.get(field)

        if field_value not in EMPTY_VALUES:
            for i, req in enumerate(required_values):
                if req in EMPTY_VALUES:
                    errors.setdefault(requirements[i], []).append(
                        f"This field is required if {field} is provided."
                    )
