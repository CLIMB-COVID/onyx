import pkgutil
import importlib, inspect
from django.db.models import Model
from . import projects
from .serializers import ProjectRecordSerializer, SerializerNode, SummarySerializer
from .serializers import BaseRecordSerializer


class ProjectSerializerMap:
    MAPPING = {}

    @classmethod
    def add(cls, model: type[Model], serializer: type[ProjectRecordSerializer]):
        """
        Add a root project `Model` and its `ProjectRecordSerializer` to the `ProjectSerializerMap`.
        """
        cls.MAPPING[model] = serializer

    @classmethod
    def get(cls, model: type[Model]) -> type[ProjectRecordSerializer]:
        """
        Retrieve the `ModelSerializer` for a `Model`.
        """
        return cls.MAPPING[model]


for module_info in pkgutil.iter_modules(
    path=projects.__path__,
    prefix=".projects.",
):
    module = importlib.import_module(
        name=module_info.name,
        package=__package__,
    )

    # Predicate that ensures members satisfy the following:
    # - The member is a subclass of ProjectRecordSerializer
    # - The member has a Meta.model attribute
    predicate = (
        lambda x: inspect.isclass(x)
        and issubclass(x, BaseRecordSerializer)
        and hasattr(x.Meta, "model")
    )

    # For each member of the module that satisfies the predicate
    # Add it to the mapping
    for name, cls in inspect.getmembers(module, predicate):
        ProjectSerializerMap.add(
            model=cls.Meta.model,
            serializer=cls,
        )
