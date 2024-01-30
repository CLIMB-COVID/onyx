from django.db import models
from accounts.models import User


def init_project_queryset(
    model: type[models.Model],
    user: User,
    fields: list[str] | None = None,
) -> models.manager.BaseManager[models.Model]:
    qs = model.objects.select_related()

    # if not user.is_staff:
    #     # If the user is not a member of staff:
    #     # - Ignore suppressed data
    #     # - Ignore site_restricted objects from other sites
    #     # TODO: For site_restricted to work properly, need to have site stored directly on project record
    #     qs = qs.filter(suppressed=False).exclude(
    #         models.Q(site_restricted=True) & ~models.Q(user__site=user.site)
    #     )
    # elif fields and "suppressed" not in fields:
    #     # If the user is a member of staff, but the suppressed field is not in scope:
    #     # - Ignore suppressed data
    #     qs = qs.filter(suppressed=False)

    return qs


def prefetch_nested(
    qs: models.QuerySet,
    fields_dict: dict,
    prefix: str | None = None,
) -> models.QuerySet:
    """
    For each field in `fields_dict` that contains nested data, apply prefetching to the QuerySet `qs`.
    """

    for field, nested in fields_dict.items():
        if nested:
            if prefix:
                field = f"{prefix}__{field}"

            qs = qs.prefetch_related(field)
            qs = prefetch_nested(
                qs=qs,
                fields_dict=nested,
                prefix=field,
            )

    return qs
