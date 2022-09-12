from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import CursorPagination
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.conf import settings
from . import serializers, models
from .filters import METADBFilter
from .models import Pathogen
from accounts.views import IsApproved
from metadb.utils.responses import APIResponse
import inspect


def get_pathogen_model_or_404(pathogen_code, accept_base=False):
    """
    Returns the model for the given `pathogen_code`, raising a `Http404` if it doesn't exist.
    """
    members = inspect.getmembers(models, inspect.isclass)

    for name, model in members:
        # Find model with matching name (case insensitive)
        if pathogen_code.upper() == name.upper():
            # Confirm whether the model inherits from the Pathogen class
            # If accept_base=True, we can also get the Pathogen class itself
            if Pathogen in model.__bases__ or (accept_base and model == Pathogen):
                return model

    return None


def enforce_optional_value_groups(data, groups):
    """
    For each group in `groups`, verify that at least one field in the group is contained in `data`.
    """
    errors = {"required_fields": []}
    # A group is a list of field names where at least one of them is required
    for group in groups:
        for field in group:
            if field in data:
                break
        else:
            # If you're reading this I'm sorry
            # I couldn't help but try a for-else
            # I just found out it can be done, so I did it :)
            errors["required_fields"].append(
                {"At least one of the following fields is required.": group}
            )

    if errors["required_fields"]:
        return errors
    else:
        return {}


def enforce_field_set(data, accepted_fields, rejected_fields):
    """
    Check `data` for unknown fields, or known fields which cannot be accepted.
    """
    rejected = {}
    unknown = {}

    for field in data:
        if field in rejected_fields:
            rejected[field] = ["This field cannot be accepted."]
        elif field not in accepted_fields:
            unknown[field] = ["This field is unknown."]

    return rejected, unknown


class CustomCursorPagination(CursorPagination):
    def add_errors(self, errors):
        self.errors = errors

    def add_warnings(self, warnings):
        self.warnings = warnings

    def get_paginated_response(self, data):
        data = super().get_paginated_response(data).data
        if data:
            response = APIResponse()
            response.next = data["next"]
            response.previous = data["previous"]
            response.errors = self.errors
            response.warnings = self.warnings
            response.results = data["results"]

            return Response(response.data)
        else:
            return Response(data)


class PathogenCodeView(APIView):
    permission_classes = [(IsAuthenticated & IsApproved) | IsAdminUser]

    def get(self, request):
        """
        Get a list of `pathogen_codes`, that correspond to tables in the database.
        """
        response = APIResponse()

        try:
            members = inspect.getmembers(models, inspect.isclass)
            pathogen_codes = []

            # For each model in data.models
            for name, model in members:
                # If the model inherits from Pathogen, add it to the list
                if Pathogen in model.__bases__:
                    pathogen_codes.append(name.upper())

            response.results.append({"pathogen_codes": pathogen_codes})

            return Response(response.data, status=status.HTTP_200_OK)

        except Exception as e:
            response.errors[(type(e)).__name__] = str(e)
            return Response(response.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateGetPathogenView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            # Creating data requires being an admin user
            permission_classes = [IsAdminUser]
        else:
            # Getting data requires being an authenticated, approved user
            permission_classes = [(IsAuthenticated & IsApproved) | IsAdminUser]
        return [permission() for permission in permission_classes]

    def post(self, request, pathogen_code):
        """
        Use `request.data` to save a model instance for the model specified by `pathogen_code`.
        """
        response = APIResponse()

        try:
            # Get the corresponding model. The base class Pathogen is NOT accepted when creating data
            pathogen_model = get_pathogen_model_or_404(pathogen_code, accept_base=False)

            # If pathogen model does not exist, return error
            if pathogen_model is None:
                response.errors[pathogen_code] = response.NOT_FOUND
                return Response(response.data, status=status.HTTP_404_NOT_FOUND)

            # If a pathogen_code was provided in the body, and it doesn't match the url, tell them to stop it
            request_pathogen_code = request.data.get("pathogen_code")
            if (
                request_pathogen_code
                and request_pathogen_code.upper() != pathogen_code.upper()
            ):
                response.errors[
                    pathogen_code
                ] = "pathogen code provided in request body does not match URL"
                return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

            # Check the request data contains at least one field from each optional value group
            response.errors.update(
                enforce_optional_value_groups(
                    data=request.data, groups=pathogen_model.OPTIONAL_VALUE_GROUPS
                )
            )

            # Check the request data contains only model fields allowed for creation
            rejected, unknown = enforce_field_set(
                data=request.data,
                accepted_fields=pathogen_model.create_fields(),
                rejected_fields=pathogen_model.no_create_fields(),
            )

            # Rejected fields (e.g. CID) are not allowed during creation
            response.errors.update(rejected)

            # Unknown fields will be a warning
            response.warnings.update(unknown)

            # Serializer also carries out validation of input data
            serializer = getattr(serializers, f"{pathogen_model.__name__}Serializer")(
                data=request.data
            )

            # If data is valid, save to the database. If not valid, return errors
            if serializer.is_valid() and not response.errors:
                serializer.save()

                response.results.append(serializer.data)

                return Response(response.data, status=status.HTTP_200_OK)
            else:
                # Combine serializer errors with current errors
                response.errors.update(serializer.errors)

                return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            response.errors[(type(e)).__name__] = str(e)
            return Response(response.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pathogen_code):
        """
        Use `request.query_params` to filter data for the model specified by `pathogen_code`.
        """
        response = APIResponse()

        try:
            # Get the corresponding model. The base class Pathogen is accepted when creating data
            pathogen_model = get_pathogen_model_or_404(pathogen_code, accept_base=True)

            # If pathogen model does not exist, return error
            if pathogen_model is None:
                response.errors[pathogen_code] = response.NOT_FOUND
                return Response(response.data, status=status.HTTP_404_NOT_FOUND)

            # Prepare paginator
            paginator = CustomCursorPagination()
            paginator.ordering = "created"
            paginator.page_size = settings.CURSOR_PAGINATION_PAGE_SIZE

            _mutable = request.query_params._mutable
            request.query_params._mutable = True

            # Remove cursor parameter from the request, as its used for pagination and not filtering
            cursor = request.query_params.get(paginator.cursor_query_param)
            if cursor:
                request.query_params.pop(paginator.cursor_query_param)

            # Remove the distinct parameter from the request, as its not a filter parameter
            distinct = request.query_params.get("distinct")
            if distinct:
                request.query_params.pop("distinct")

            request.query_params._mutable = _mutable

            # Generate filterset and validate request query parameters
            filterset = METADBFilter(
                pathogen_model,
                request.query_params,
                queryset=pathogen_model.objects.filter(suppressed=False),
            )
            # Retrieve the resulting queryset, filtered by the query parameters
            qs = filterset.qs

            # Append any unknown fields to error dict
            for field in request.query_params:
                if field not in filterset.filters:
                    response.errors[field] = ["This field is unknown."]

            # Check the distinct field is a known field
            if distinct and distinct not in filterset.filters:
                response.errors[distinct] = ["This field is unknown."]

            if not filterset.is_valid():
                # Append any filterset errors to the errors dict
                for field, msg in filterset.errors.items():
                    response.errors[field] = msg

            if response.errors:
                return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

            # If a parameter was provided for getting distinct results, apply it
            if distinct:
                try:
                    # I have no idea how this could go wrong at this point
                    # But hey you never know
                    qs = qs.distinct(distinct)
                except Exception as e:
                    response.errors.update(e.__dict__)

                    return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

                # Serialize the results
                serializer = getattr(
                    serializers, f"{pathogen_model.__name__}Serializer"
                )(qs, many=True)

                response.results = serializer.data

                return Response(response.data, status=status.HTTP_200_OK)
            else:
                # Non-distinct results have the potential to be quite large
                # So pagination (splitting the data into multiple pages) is used

                # Add the pagination cursor param back into the request
                if cursor is not None:
                    _mutable = request.query_params._mutable
                    request.query_params._mutable = True
                    request.query_params[paginator.cursor_query_param] = cursor
                    request.query_params._mutable = _mutable

                # Paginate the response
                instances = filterset.qs.order_by("id")

                result_page = paginator.paginate_queryset(instances, request)

                # Serialize the results
                serializer = getattr(
                    serializers, f"{pathogen_model.__name__}Serializer"
                )(result_page, many=True)

                # Make it look like the other responses for consistency
                # And we might want to change in future to provide some warnings
                paginator.add_errors(response.errors)
                paginator.add_warnings(response.warnings)
                return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            response.errors[(type(e)).__name__] = str(e)
            return Response(response.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateSuppressPathogenView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pathogen_code, cid):
        """
        Use `request.data` and a `cid` to update an instance for the model specified by `pathogen_code`.
        """
        response = APIResponse()

        try:
            # Get the corresponding model. The base class Pathogen is accepted when updating data
            pathogen_model = get_pathogen_model_or_404(pathogen_code, accept_base=True)

            # If pathogen model does not exist, return error
            if pathogen_model is None:
                response.errors[pathogen_code] = response.NOT_FOUND
                return Response(response.data, status=status.HTTP_404_NOT_FOUND)

            # Get the instance to be updated
            instance = get_object_or_404(
                pathogen_model.objects.filter(suppressed=False), cid=cid
            )

            # Check the request data contains only model fields allowed for updating
            rejected, unknown = enforce_field_set(
                data=request.data,
                accepted_fields=pathogen_model.update_fields(),
                rejected_fields=pathogen_model.no_update_fields(),
            )

            # Rejected fields (e.g. CID) are not allowed during creation
            response.errors.update(rejected)

            # Unknown fields will be a warning
            response.warnings.update(unknown)

            # Serializer also carries out validation of input data
            serializer = getattr(serializers, f"{pathogen_model.__name__}Serializer")(
                instance=instance, data=request.data, partial=True
            )

            # If data is valid, update existing record in the database. If not valid, return errors
            if serializer.is_valid() and not response.errors:
                if not serializer.validated_data:
                    response.errors.setdefault("non_field_errors", []).append(
                        "no fields were updated"
                    )

                    return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

                serializer.save()

                response.results.append(serializer.data)

                return Response(response.data, status=status.HTTP_200_OK)
            else:
                # Combine serializer errors with current errors
                response.errors.update(serializer.errors)

                return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            response.errors[(type(e)).__name__] = str(e)
            return Response(response.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pathogen_code, cid):
        """
        Use the provided `pathogen_code` and `cid` to suppress a record.
        """
        response = APIResponse()

        try:
            # Get the corresponding model. The base class Pathogen is accepted when suppressing data
            pathogen_model = get_pathogen_model_or_404(pathogen_code, accept_base=True)

            # If pathogen model does not exist, return error
            if pathogen_model is None:
                response.errors[pathogen_code] = response.NOT_FOUND
                return Response(response.data, status=status.HTTP_404_NOT_FOUND)

            try:
                # Get the instance to be suppressed
                instance = pathogen_model.objects.filter(suppressed=False, cid=cid)
            except pathogen_model.DoesNotExist:
                # If cid did not exist, return error
                response.errors[cid] = response.NOT_FOUND
                return Response(response.data, status=status.HTTP_404_NOT_FOUND)

            # Suppress and save
            instance.suppressed = True
            instance.save(update_fields=["suppressed"])

            # Just to double check
            instance = get_object_or_404(pathogen_model, cid=cid)

            response = APIResponse()
            response.results.append({"cid": cid, "suppressed": instance.suppressed})

            # Return the details
            return Response(
                response.data,
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            response.errors[(type(e)).__name__] = str(e)
            return Response(response.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeletePathogenView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pathogen_code, cid):
        """
        Use the provided `pathogen_code` and `cid` to permanently delete a record.
        """
        response = APIResponse()

        try:
            # Get the corresponding model. The base class Pathogen is accepted when deleting data
            pathogen_model = get_pathogen_model_or_404(pathogen_code, accept_base=True)

            # If pathogen model does not exist, return error
            if pathogen_model is None:
                response.errors[pathogen_code] = response.NOT_FOUND
                return Response(response.data, status=status.HTTP_404_NOT_FOUND)

            try:
                # Attempt to delete object with the provided cid
                pathogen_model.objects.get(cid=cid).delete()
            except pathogen_model.DoesNotExist:
                # If cid did not exist, return error
                response.errors[cid] = response.NOT_FOUND
                return Response(response.data, status=status.HTTP_404_NOT_FOUND)

            deleted = not pathogen_model.objects.filter(cid=cid).exists()
            response.results.append({"cid": cid, "deleted": deleted})
            return Response(response.data, status=status.HTTP_200_OK)

        except Exception as e:
            response.errors[(type(e)).__name__] = str(e)
            return Response(response.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)