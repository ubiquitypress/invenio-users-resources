# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Group service tests."""

import pytest
from invenio_access.permissions import system_identity
from invenio_records_resources.resources.errors import PermissionDeniedError
from marshmallow import ValidationError


def test_groups_sort(app, groups, group_service):
    # default sort by name
    res = group_service.search(system_identity).to_dict()
    assert res["sortBy"] == "name"
    assert res["hits"]["total"] > 0
    hits = res["hits"]["hits"]
    assert hits[0]["id"] == "hr-dep"
    assert hits[1]["id"] == "it-dep"


def test_groups_no_facets(app, group, group_service):
    """Make sure certain fields ARE searchable."""
    res = group_service.search(system_identity)
    # if facets were enabled but not configured the value would be {}
    assert res.aggregations is None


def test_groups_fixed_pagination(app, groups, group_service):
    res = group_service.search(system_identity, params={"size": 1, "page": 2})
    assert res.pagination.page == 1
    assert res.pagination.size == 10


@pytest.mark.parametrize(
    "query",
    [
        # cannot search on title because is never set
        # see TODO in parse_role_data
        "id:it-dep",
        "name:IT Department",
        "+name:it",
        "IT",
    ],
)
def test_groups_search_field(app, group, group_service, query):
    """Make sure certain fields ARE searchable."""
    res = group_service.search(system_identity, q=query)
    assert res.total > 0


def test_groups_search(app, groups, group_service, user_pub, anon_identity):
    """Test group search."""

    # System can retrieve all groups.
    res = group_service.search(system_identity).to_dict()
    assert res["hits"]["total"] == len(groups)

    # Authenticated user can retrieve unmanaged groups
    res = group_service.search(user_pub.identity).to_dict()
    assert res["hits"]["total"] == len([g for g in groups if not g.is_managed])

    # Anon does not have permission to search
    with pytest.raises(PermissionDeniedError):
        group_service.search(anon_identity).to_dict()


def test_groups_read(app, groups, group_service, user_pub, anon_identity):
    """Test group read."""

    from invenio_accounts.models import Role

    for g in groups:
        # System can retrieve all groups.
        group_service.read(system_identity, g.name).to_dict()

        # Authenticated user can retrieve unmanaged groups
        if g.is_managed:
            with pytest.raises(PermissionDeniedError):
                group_service.read(user_pub.identity, g.name).to_dict()
        else:
            group_service.read(user_pub.identity, g.name).to_dict()

        # Anon does not have permission to search
        with pytest.raises(PermissionDeniedError):
            group_service.read(anon_identity, g.name).to_dict()


def test_create(
    app, db, group_service, user_moderator, user_res, clear_cache, search_clear
):
    """Test user create."""
    data = {
        "name": "newgroup",
        "description": "newgroup description",
    }

    with pytest.raises(PermissionDeniedError):
        group_service.create(user_res.identity, data)

    res = group_service.create(user_moderator.identity, data).to_dict()
    assert res["name"] == "newgroup"

    gr = group_service.read(user_moderator.identity, res["id"])
    # # Make sure new user is active and verified
    assert gr.data["id"] == "newgroup"
    assert gr.data["name"] == "newgroup"
    assert gr.data["description"] == "newgroup description"
    assert gr.data["is_managed"] == True

    # Cannot re-add same details for new group
    with pytest.raises(ValidationError) as exc_info:
        group_service.create(user_moderator.identity, data)

    assert exc_info.value.messages == {
        "name": ["Name already used by another group."],
    }

    # With just a name
    res = group_service.create(
        user_moderator.identity,
        {
            "name": "newgroup1",
        },
    ).to_dict()
    assert res["name"] == "newgroup1"

    gr = group_service.read(user_moderator.identity, res["id"])
    # # Make sure new user is active and verified
    assert gr.data["id"] == "newgroup1"

    # Invalid as no name
    with pytest.raises(ValidationError) as exc_info:
        group_service.create(
            user_moderator.identity,
            {
                "description": "newgroup description",
            },
        )
    assert exc_info.value.messages == ["Unexpected Issue: 'name'"]
