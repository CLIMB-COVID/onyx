from rest_framework import serializers
from rest_framework.validators import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _
from datetime import date


class YearMonthField(serializers.Field):
    def to_internal_value(self, data):
        try:
            year, month = str(data).split("-")
        except ValueError:
            raise ValidationError("Must be in YYYY-MM format.")

        try:
            value = date(int(year), int(month), 1)
        except ValueError as e:
            raise ValidationError(e)

        return value

    def to_representation(self, value):
        try:
            year, month, _ = str(value).split("-")
        except ValueError:
            raise ValidationError("Must be in YYYY-MM-DD format.")

        return year + "-" + month


class LowerCharField(serializers.CharField):
    def to_internal_value(self, data):
        data = str(data).lower()
        return super().to_internal_value(data)


class ContextedSlugRelatedField(serializers.RelatedField):
    """
    A read-write field that represents the target of the relationship
    by a unique 'slug' attribute (with context).
    """

    default_error_messages = {
        "does_not_exist": _("Object with {slug_name}={value} does not exist."),
        "invalid": _("Invalid value."),
    }

    def __init__(self, slug_field=None, **kwargs):
        assert slug_field is not None, "The `slug_field` argument is required."
        self.slug_field = slug_field
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            return queryset.get(  # type: ignore
                **{
                    "content_type": self.context["field_contexts"][
                        self.source
                    ].content_type,
                    "field": self.source,
                    self.slug_field: data,
                }
            )
        except ObjectDoesNotExist:
            self.fail(
                "does_not_exist", slug_name=self.slug_field, value=smart_str(data)
            )
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return getattr(obj, self.slug_field)
