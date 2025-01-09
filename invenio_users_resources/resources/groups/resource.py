# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 TU Wien.
# Copyright (C) 2022 CERN.
# Copyright (C) 2022 European Union.
# Copyright (C) 2024 Ubiquity Press.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""User groups resource."""


from flask import g, send_file
from flask_resources import resource_requestctx, response_handler, route
from invenio_records_resources.resources import RecordResource
from invenio_records_resources.resources.records.resource import (
    request_data,
    request_extra_args,
    request_search_args,
    request_view_args,
)
from invenio_records_resources.resources.records.utils import search_preference


#
# Resource
#
class GroupsResource(RecordResource):
    """Resource for user groups."""

    def create_url_rules(self):
        """Create the URL rules for the user groups resource."""
        routes = self.config.routes
        return [
            route("GET", routes["list"], self.search),
            route("POST", routes["list"], self.create),
            route("GET", routes["item"], self.read),
            route("PUT", routes["item"], self.update),
            route("GET", routes["item-avatar"], self.avatar),
            route("PUT", routes["manage-user"], self.add_user),
            route("DELETE", routes["manage-user"], self.remove_user),
            route("GET", routes["users"], self.users),
        ]

    @request_search_args
    @request_view_args
    @response_handler(many=True)
    def search(self):
        """Perform a search over the groups."""
        hits = self.service.search(
            identity=g.identity,
            params=resource_requestctx.args,
            search_preference=search_preference(),
        )
        return hits.to_dict(), 200

    @request_view_args
    @response_handler()
    def read(self):
        """Read a group."""
        item = self.service.read(
            id_=resource_requestctx.view_args["id"],
            identity=g.identity,
        )
        return item.to_dict(), 200

    @request_view_args
    def avatar(self):
        """Get a groups's avatar."""
        avatar = self.service.read_avatar(
            name_=resource_requestctx.view_args["id"],
            identity=g.identity,
        )
        return send_file(
            avatar.bytes_io,
            mimetype=avatar.mimetype,
            as_attachment=False,
            download_name=avatar.name,
            etag=avatar.etag,
            last_modified=avatar.last_modified,
            max_age=86400 * 7,
        )

    @request_extra_args
    @request_data
    @response_handler()
    def create(self):
        """Create a group."""
        item = self.service.create(
            g.identity,
            resource_requestctx.data or {},
        )
        return item.to_dict(), 201

    @request_extra_args
    @request_view_args
    @request_data
    @response_handler()
    def update(self):
        """Update a group."""
        item = self.service.update(
            g.identity,
            id_=resource_requestctx.view_args["id"],
            data=resource_requestctx.data or {},
        )
        return item.to_dict(), 200

    @request_view_args
    def add_user(self):
        """Add Admin user to group."""
        self.service.add_user(
            id_=resource_requestctx.view_args["id"],
            identity=g.identity,
            user_id=resource_requestctx.view_args["user_id"],
        )
        return "", 200

    @request_view_args
    def remove_user(self):
        """Remove Admin user from group."""
        self.service.remove_user(
            id_=resource_requestctx.view_args["id"],
            identity=g.identity,
            user_id=resource_requestctx.view_args["user_id"],
        )
        return "", 200

    @request_view_args
    def users(self):
        """Read group users."""
        users = self.service.list_users(
            id_=resource_requestctx.view_args["id"],
            identity=g.identity,
        )
        return users, 200
