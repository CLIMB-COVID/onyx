from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import CursorPagination
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import Http404
from . import serializers, models
from .models import Pathogen
from accounts.views import IsApproved
from utils.responses import Responses
import inspect


# TODO: Could do with a consistent model for response, no matter errors or not
# Could have status code, errors and results for every response


def get_pathogen_model_or_404(pathogen_code):
    '''
    Returns the model for the given `pathogen_code`, raising a `Http404` if it doesn't exist.
    '''
    members = inspect.getmembers(models, inspect.isclass)
    for name, model in members:
        if pathogen_code.upper() == name.upper():
            return model
    raise Http404


# class PathogenCodeView(APIView):
#     def get(self, request):
#         members = inspect.getmembers(models, inspect.isclass)
#         if 


class CreateGetPathogenView(APIView):
    permission_classes = [IsAuthenticated, IsApproved] # IsAdminUser for delete?

    def post(self, request, pathogen_code):
        # If a cid was provided, tell them no
        if request.data.get("cid"):
            return Responses._403_cannot_provide_cid
        
        # If a pathogen_code was provided in the body, tell them no
        if request.data.get("pathogen_code"):
            return Responses._400_pathogen_code_in_url_only

        # Check if an institute was provided in the body
        institute_code = request.data.get("institute")
        if not institute_code:
            return Responses._400_no_institute

        # Check user is the correct institute
        if request.user.institute.code != institute_code:
            return Responses._403_incorrect_institute_for_user

        # Get the model
        pathogen_model = get_pathogen_model_or_404(pathogen_code)

        # Set the pathogen code
        request.data["pathogen_code"] = pathogen_code.upper()

        # Serializer validates input data
        serializer = getattr(serializers, f"{pathogen_model.__name__}Serializer")(data=request.data)

        # If data is valid, save to the database. If invalid, return errors
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pathogen_code):
        # Get the model
        pathogen_model = get_pathogen_model_or_404(pathogen_code)
        
        # Create queryset of all objects by default
        instances = pathogen_model.objects.all()

        # If an id was provided (or an id__ field) as a query parameter, tell them no
        # TODO: If you want this behaviour truly enforced, might need some more work
        # Do we even care if filtering by primary key?
        query_param_fields = list(request.query_params.keys())
        model_fields = {f.name for f in pathogen_model._meta.get_fields()}
        for field in query_param_fields:
            dunder_split = field.split("__")
            for f in dunder_split:
                if f == "id" or (f.endswith("_id") and f[:-len("_id")] in model_fields):
                    return Responses._403_cannot_query_id

        # For each query param, filter the data
        for field, value in request.query_params.items():
            if field == "cursor":
                continue
            
            if field == "institute":
                # A regrettably hardcoded default that is much more user friendly
                # TODO: if there is any way other than this, I will take it
                field = "institute__code"
            
            try:
                instances = instances.filter(**{field : value})
            except Exception as e:
                return Response({"detail" : repr(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Paginate the response 
        # TODO: Read up exactly how cursor pagination works and how it should be done
        instances = instances.order_by("id")
        paginator = CursorPagination()
        paginator.ordering = "created"
        paginator.page_size = 5000
        result_page = paginator.paginate_queryset(instances, request)

        # Serialize the filtered data and then return it
        serializer = getattr(serializers, f"{pathogen_model.__name__}Serializer")(result_page, many=True)
        
        return paginator.get_paginated_response(serializer.data)


class UpdateDeletePathogenView(APIView):
    def get_permissions(self):
        if self.request.method == "PATCH":
            permission_classes = [IsAuthenticated, IsApproved]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def patch(self, request, pathogen_code, cid):
        # Get the model
        pathogen_model = get_pathogen_model_or_404(pathogen_code)
        
        # Get the instance to be updated
        instance = get_object_or_404(pathogen_model, cid=cid)
        
        # Check user is the correct institute
        if request.user.institute.code != instance.institute.code:
            return Responses._403_incorrect_institute_for_user

        serializer = getattr(serializers, f"{pathogen_model.__name__}Serializer")(instance=instance, data=request.data, partial=True)

        # If data is valid, update existing record in the database. If invalid, return errors
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pathogen_code, cid):
        # Get the model for the given cid
        pathogen_model = get_pathogen_model_or_404(pathogen_code)
        
        # Attempt to delete object with the provided cid, and return response
        response = get_object_or_404(pathogen_model, cid=cid).delete()
        return Response({"detail" : response}, status=status.HTTP_200_OK)