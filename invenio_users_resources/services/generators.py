# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 TU Wien.
# Copyright (C) 2022 CERN.
# Copyright (C) 2023 Graz University of Technology.
# Copyright (C) 2025 Ubiquity Press.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Permission generators for users and groups."""

from abc import abstractmethod
from itertools import chain

from flask import current_app
from invenio_access import Permission, any_user
from invenio_records.dictutils import dict_lookup
from invenio_records_permissions.generators import (
    ConditionalGenerator,
    Generator,
    UserNeed,
)
from invenio_search.engine import dsl

from invenio_users_resources.permissions import SuperUserMixin


class IfPublic(ConditionalGenerator):
    """Generator for different permissions based on the visibility settings."""

    def __init__(self, field_name, then_, else_, **kwargs):
        """Constructor."""
        super().__init__(then_=then_, else_=else_, **kwargs)
        self._field_name = field_name

    def _condition(self, record=None, **kwargs):
        """Condition to choose generators set."""
        if record is None:
            return False

        visibility = record.preferences.get(self._field_name, "restricted")
        is_public = visibility == "public"

        return is_public

    def query_filter(self, **kwargs):
        """Filters for queries."""
        field = f"preferences.{self._field_name}"
        q_public = dsl.Q("match", **{field: "public"})
        q_restricted = dsl.Q("match", **{field: "restricted"})
        then_query = self._make_query(self.then_, **kwargs)
        else_query = self._make_query(self.else_, **kwargs)

        if then_query and else_query:
            return (q_public & then_query) | (q_restricted & else_query)
        elif then_query:
            return q_public & then_query
        elif else_query:
            return q_public | (q_restricted & else_query)
        else:
            return q_public


class IfPublicEmail(IfPublic):
    """Generator checking the 'email_visibility' setting."""

    def __init__(self, then_, else_):
        """Constructor."""
        super().__init__("email_visibility", then_, else_)


class IfPublicUser(IfPublic):
    """Generator checking the 'visibility' setting."""

    def __init__(self, then_, else_):
        """Constructor."""
        super().__init__("visibility", then_, else_)


class Self(Generator):
    """Requires the users themselves."""

    def needs(self, record=None, **kwargs):
        """Set of Needs granting permission."""
        if record is not None:
            return [UserNeed(record.id)]

        return []

    def query_filter(self, identity=None, **kwargs):
        """Filters for the current identity."""
        if identity is not None:
            for need in identity.provides:
                if need.method == "id":
                    return dsl.Q("term", id=need.value)

        return []


class IfGroupNotManaged(ConditionalGenerator):
    """Generator for managed group access."""

    def __init__(self, then_, else_, **kwargs):
        """Constructor."""
        super().__init__(then_=then_, else_=else_, **kwargs)
        self._field_name = "is_managed"

    def _condition(self, record, **kwargs):
        """Condition to choose generators set."""
        if record is None:
            return False

        is_managed = dict_lookup(record, self._field_name)
        return not is_managed

    def query_filter(self, **kwargs):
        """Filters for queries."""
        q_not_managed = dsl.Q("match", **{self._field_name: False})
        then_query = self._make_query(self.then_, **kwargs)
        else_query = self._make_query(self.else_, **kwargs)
        identity = kwargs.get("identity", None)
        if identity:
            permission = Permission(*self.needs(**kwargs))
            if permission.allows(identity):
                return else_query

        return q_not_managed & then_query


class IfSuperUser(SuperUserMixin, ConditionalGenerator):
    """Generator for managing access to super group access."""

    def __init__(self, then_, else_, **kwargs):
        """Constructor."""
        super().__init__(then_=then_, else_=else_, **kwargs)
        self._field_name = "name"

    def _condition(self, record, **kwargs):
        """Condition to choose generators set."""
        identity = kwargs.get("identity", None)
        if identity:
            result = self._is_user_superadmin(identity)
            return result
        return False

    def query_filter(self, **kwargs):
        """Filters for queries."""
        then_query = self._make_query(self.then_, **kwargs)
        else_query = self._make_query(self.else_, **kwargs)
        identity = kwargs.get("identity", None)
        if identity and self._is_user_superadmin(identity):
            return then_query
        return else_query


class IfActionRoleMatches(SuperUserMixin, ConditionalGenerator):
    """Generator for managing access to super group access."""

    def _condition(self, record, **kwargs):
        """Condition to choose generators set."""
        return self._should_action_proceed(kwargs.get("identity", None), record)

    def _generators(self, record, **kwargs):
        """Get the "then" or "else" generators.

        This is different from normal ConidtionalGenerator, where if the condition is True,
        then we will select one of the Permissions from the list rather than using the whole list.
        This allows use to control super user and user moderator permissions instead of both.
        """
        result = self._condition(record=record, **kwargs)
        return [self.then_[result[1]]] if result[0] else self.else_

    @abstractmethod
    def _should_action_proceed(self, identity, group):
        """Condition to choose generators set."""
        raise NotImplementedError()


class IfGroupActionRoleMatches(IfActionRoleMatches):
    """Generator for managing access to super group access."""

    def _should_action_proceed(self, identity, group):
        """Check if the user has the superuser role."""
        roles = self._get_superadmin_roles()
        # If no Superuser roles
        if not roles:
            return (True, 1)
        # Get all roles with superuser access action role.
        is_user_super, is_group_super = False, False
        if identity:
            is_user_super = self._is_user_superadmin(identity, roles=roles)
        if group is not None:
            is_group_super = self._is_group_superadmin(group.id, roles)
        if not identity or group is None:
            if identity:
                return (True, 0) if is_user_super else (True, 1)
            if group is not None:
                return (False, None) if is_group_super else (True, 1)
            return (True, 1)

        # Check if user and group are superadmin
        options = {
            (True, True): (True, 0),  # Both are superadmins
            (True, False): (True, 1),  # Only user is superadmin
            (False, True): (False, None),  # Only group is superadmin
            (False, False): (True, 1),  # Only group is superadmin
        }
        return options[(is_user_super, is_group_super)]


class IfUserActionRoleMatches(IfActionRoleMatches):
    """Generator for managing access to super group access."""

    def _should_action_proceed(self, identity, group):
        """Check if the user has the superuser role."""
        roles = self._get_superadmin_roles()
        # If no Superuser roles
        if not roles:
            return (True, 1)
        # Get all roles with superuser access action role.
        is_user_super = False
        if identity:
            is_user_super = self._is_user_superadmin(identity, roles=roles)
            return (True, 0) if is_user_super else (True, 1)
        return (False, None)

    def query_filter(self, **kwargs):
        """Filters for queries."""
        identity = kwargs.get("identity", None)
        if identity:
            then_query = self._make_query(
                (
                    [self.then_[0]]
                    if self._is_user_superadmin(identity)
                    else [self.then_[1]]
                ),
                **kwargs,
            )
            return then_query

        return self._make_query(self.else_, **kwargs)


class GroupsEnabled(Generator):
    """Generator to restrict if the groups are not enabled.

    If the groups are not enabled, exclude any user for adding members of the
    param member type.

    A system process is allowed to do anything.
    """

    def __init__(self, *need_groups_enabled_types):
        """Types that need the groups enabled."""
        self.need_groups_enabled_types = need_groups_enabled_types

    def excludes(self, member_types=None, **kwargs):
        """Preventing needs."""
        member_types = member_types or {"group"}
        for m in member_types:
            if (
                m in self.need_groups_enabled_types
                and not current_app.config["USERS_RESOURCES_GROUPS_ENABLED"]
            ):
                return [any_user]
        return []
