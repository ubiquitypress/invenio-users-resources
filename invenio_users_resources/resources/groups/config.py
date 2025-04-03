# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 TU Wien.
# Copyright (C) 2022 CERN.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""User roles/groups resource config."""


import marshmallow as ma
from flask_resources import HTTPJSONException, create_error_handler
from invenio_i18n import lazy_gettext as _
from invenio_records_resources.resources import (
    RecordResourceConfig,
    SearchRequestArgsSchema,
)
from invenio_records_resources.resources.errors import ErrorHandlersMixin

from invenio_users_resources.errors import ForeignKeyIntegrityError


#
# Request args
#
class GroupSearchRequestArgsSchema(SearchRequestArgsSchema):
    """Add parameter to parse tags."""

    title = ma.fields.String()


#
# Resource config
#
class GroupsResourceConfig(RecordResourceConfig):
    """User groups resource configuration."""

    blueprint_name = "groups"
    url_prefix = "/groups"
    routes = {
        "list": "",
        "item": "/<id>",
        "item-avatar": "/<id>/avatar.svg",
        "manage-user": "/<id>/users/<user_id>",
        "users": "/<id>/users",
    }

    error_handlers = {
        **ErrorHandlersMixin.error_handlers,
        ForeignKeyIntegrityError: create_error_handler(
            lambda e: (
                HTTPJSONException(
                    code=403,
                    description=_(
                        "You're deleing a group that might be used elsewhere."
                    ),
                )
            )
        ),
    }

    request_view_args = {
        "id": ma.fields.Str(),
        "user_id": ma.fields.Str(),
    }

    request_search_args = GroupSearchRequestArgsSchema

    response_handlers = {
        "application/vnd.inveniordm.v1+json": RecordResourceConfig.response_handlers[
            "application/json"
        ],
        **RecordResourceConfig.response_handlers,
    }
