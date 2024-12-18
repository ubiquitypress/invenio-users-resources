# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 KTH Royal Institute of Technology
# Copyright (C) 2022 TU Wien.
# Copyright (C) 2022 CERN.
# Copyright (C) 2022 European Union.
# Copyright (C) 2024 Ubiquity Press.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Groups service."""

from invenio_accounts.models import Role
from invenio_db import db
from invenio_records_resources.resources.errors import PermissionDeniedError
from invenio_records_resources.services import RecordService
from invenio_records_resources.services.uow import RecordCommitOp, unit_of_work

from ...records.api import GroupAggregate
from ..results import AvatarResult


class GroupsService(RecordService):
    """User groups service."""

    def read(self, identity, id_):
        """Retrieve a user group."""
        # resolve and require permission
        group = GroupAggregate.get_record_by_name(id_)
        if group is None:
            # return 403 even on empty resource due to security implications
            raise PermissionDeniedError()

        self.require_permission(identity, "read", record=group)

        # run components
        for component in self.components:
            if hasattr(component, "read"):
                component.read(identity, group=group)

        return self.result_item(self, identity, group, links_tpl=self.links_item_tpl)

    def read_avatar(self, identity, name_):
        """Get a groups's avatar."""
        group = GroupAggregate.get_record_by_name(name_)
        if group is None:
            # return 403 even on empty resource due to security implications
            raise PermissionDeniedError()
        self.require_permission(identity, "read", record=group)
        return AvatarResult(group)

    def rebuild_index(self, identity, uow=None):
        """Reindex all user groups managed by this service."""
        roles = db.session.query(Role.id).yield_per(1000)

        self.indexer.bulk_index([r.id for r in roles])

        return True

    @unit_of_work()
    def create(self, identity, data, raise_errors=True, uow=None):
        """Create a user."""
        self.require_permission(identity, "create")
        # validate data
        data, errors = self.schema.load(
            data,
            context={"identity": identity},
        )

        # create the role with the specified data
        group = self.record_cls.create(data)

        # run components
        self.run_components(
            "create",
            identity,
            data=data,
            group=group,
            errors=errors,
            uow=uow,
        )

        uow.register(RecordCommitOp(group, indexer=self.indexer, index_refresh=True))

        return self.result_item(
            self, identity, group, links_tpl=self.links_item_tpl, errors=errors
        )
