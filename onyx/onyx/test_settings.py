from .settings import *

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "knox.auth.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "accounts.permissions.IsAdminUser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "internal.renderers.OnyxJSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_PAGINATION_CLASS": None,
    "PAGE_SIZE": 25,
}
