"""
Application entrypoint.

Creates the FastAPI application, registers routers and exception
handlers, and provides the OpenAPI/Swagger configuration.
"""

import logging

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.error_handlers import register_exception_handlers
from app.api.routers import process, upload
from app.config.settings import get_settings
from app.core.logging import setup_logging


logger = logging.getLogger(__name__)


settings = get_settings()

setup_logging(
    settings.log_level
)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)


register_exception_handlers(
    app
)


app.include_router(
    upload.router
)

app.include_router(
    process.router
)


def custom_openapi() -> dict:
    """
    Generate the OpenAPI schema and patch the multiple-file upload
    definition so Swagger UI displays a real file picker.

    The endpoint remains:

        list[UploadFile]

    Therefore the client can upload multiple files using the same
    multipart/form-data field named "files".
    """

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Enterprise CV Processing Pipeline.\n\n"
            "Upload up to 100 CV files per request. "
            "Each CV is processed independently."
        ),
        routes=app.routes,
    )

    upload_path = (
        openapi_schema
        .get("paths", {})
        .get("/upload")
    )

    if upload_path:

        upload_operation = upload_path.get("post")

        if upload_operation:

            request_body = upload_operation.get(
                "requestBody"
            )

            if request_body:

                content = request_body.get(
                    "content",
                    {},
                )

                multipart = content.get(
                    "multipart/form-data"
                )

                if multipart:

                    schema = multipart.get(
                        "schema"
                    )

                    if schema:

                        if "$ref" in schema:

                            ref = schema["$ref"]

                            prefix = "#/components/schemas/"

                            if ref.startswith(prefix):

                                schema_name = ref[
                                    len(prefix):
                                ]

                                schema = (
                                    openapi_schema
                                    .get("components", {})
                                    .get("schemas", {})
                                    .get(schema_name)
                                )

                        if isinstance(schema, dict):

                            properties = schema.get(
                                "properties",
                                {},
                            )

                            files_schema = properties.get(
                                "files"
                            )

                            if isinstance(files_schema, dict):

                                items = files_schema.get(
                                    "items"
                                )

                                if isinstance(items, dict):

                                    items.pop(
                                        "contentMediaType",
                                        None,
                                    )

                                    items["type"] = "string"
                                    items["format"] = "binary"

                                    logger.info(
                                        "Patched OpenAPI /upload "
                                        "file schema for Swagger UI."
                                    )

    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi


@app.get(
    "/health",
    tags=["health"],
)
def health_check() -> dict:
    """
    Basic application health check.
    """

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }