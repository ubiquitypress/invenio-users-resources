# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
# Copyright (C) 2025 Ubiquity Press.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Users resources generic needs and permissions."""

from invenio_access import ActionRoles, Permission, action_factory, superuser_access
from invenio_records_permissions.generators import AdminAction
from invenio_search.engine import dsl

USER_MANAGEMENT_ACTION_NAME = "administration-moderation"

user_management_action = action_factory(USER_MANAGEMENT_ACTION_NAME)


class SuperUserMixin:
    """Mixin for superuser permissions."""

    def _is_group_superadmin(self, group_id, roles):
        groups = {role.role.id for role in roles}
        if group_id in groups:
            return True
        return False

    def _get_superadmin_roles(self):
        """Get all roles with superuser access action role."""
        return ActionRoles.query_by_action(superuser_access).all()

    def _is_user_superadmin(self, identity, roles=None):
        """Check if the user has the superuser role."""
        roles = roles if roles else self._get_superadmin_roles()
        users = {user.id for role in roles for user in role.role.users}
        if identity.id in users:
            return True
        return False

    def _should_action_proceed(self, identity, group):
        """Check if the user has the superuser role."""
        # Get all roles with superuser access action role.
        if not identity or group is None:
            return True
        roles = ActionRoles.query_by_action(superuser_access).all()
        # If no Superuser roles
        if not roles:
            return True
        # Check if user and group are superadmin
        is_user_super = self._is_user_superadmin(identity, roles=roles)
        is_group_super = self._is_group_superadmin(group.id, roles)
        options = {
            (True, True): True,  # Both are superadmins
            (True, False): True,  # Only user is superadmin
            (False, True): False,  # Only group is superadmin
            (False, False): True,  # Both not superadmin
        }
        return options[(is_user_super, is_group_super)]


class AdministratorAction(AdminAction):
    """Generator for user administrator needs.

    This generator's purpose is to be used in cases where administration needs are required.
    The query filter of this generator is quite broad (match_all). Therefore, it must be used with care.
    """

    def query_filter(self, identity, **kwargs):
        """Not implemented at this level."""
        permission = Permission(self.action)
        if permission.allows(identity):
            roles = ActionRoles.query_by_action(superuser_access).all()
            role_names = {role.role.name for role in roles}
            return dsl.Q("match_all") & ~dsl.Q("terms", **{"name": list(role_names)})
        return []
