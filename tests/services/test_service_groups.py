# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
# Copyright (C) 2024 Ubiquity Press.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Group service tests."""

import copy

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


def test_groups_search(
    database,
    app,
    groups,
    group_service,
    user_pub,
    anon_identity,
    user_admin,
    user_moderator,
):
    """Test group search."""

    # System can retrieve all groups.
    res = group_service.search(system_identity).to_dict()
    assert res["hits"]["total"] == 5

    # # Authenticated user can retrieve unmanaged groups
    res = group_service.search(user_pub.identity).to_dict()
    assert res["hits"]["total"] == len([g for g in groups if not g.is_managed])

    # Super Admin can see everything
    res = group_service.search(user_admin.identity).to_dict()
    assert res["hits"]["total"] == 5

    # User Admin can see everything but admin groups
    res = group_service.search(user_moderator.identity).to_dict()
    assert res["hits"]["total"] == 4

    # Anon does not have permission to search
    with pytest.raises(PermissionDeniedError):
        group_service.search(anon_identity).to_dict()


def test_groups_read(
    app, groups, group_service, user_admin, user_moderator, user_pub, anon_identity
):
    """Test group read."""

    from invenio_accounts.models import Role

    for g in groups:
        # System can retrieve all groups.
        group_service.read(system_identity, g.name).to_dict()
        # Authenticated user can retrieve unmanaged groups
        if g.is_managed:
            group_service.read(user_admin.identity, g.name).to_dict()
            group_service.read(user_moderator.identity, g.name).to_dict()
            with pytest.raises(PermissionDeniedError):
                group_service.read(user_pub.identity, g.name).to_dict()
        else:
            group_service.read(user_pub.identity, g.name).to_dict()
            group_service.read(user_admin.identity, g.name).to_dict()
            group_service.read(user_moderator.identity, g.name).to_dict()

        # Anon does not have permission to search
        with pytest.raises(PermissionDeniedError):
            group_service.read(anon_identity, g.name).to_dict()

    gac = group_service.record_cls
    ga = gac.get_record_by_name("admin")
    # System user
    group_service.read(system_identity, g.name).to_dict()
    # Super user
    group_service.read(user_admin.identity, ga.id)
    # Authenicated user
    with pytest.raises(PermissionDeniedError):
        group_service.read(user_pub.identity, ga.id)
    with pytest.raises(PermissionDeniedError):
        group_service.read(anon_identity, ga.id)


def test_admin_group_create(
    app, db, group_service, user_moderator, user_res, clear_cache, search_clear
):
    """Test user create."""
    data = {
        "created": "",
        "description": "title formatting and disciplines api added.",
        "id": "",
        "is_managed": False,
        "name": "Jake1",
        "provider": "",
        "revision_id": "",
        "updated": "",
    }

    res = group_service.create(user_moderator.identity, data).to_dict()
    assert res["name"] == "Jake1"
    gr = group_service.read(user_moderator.identity, res["id"])
    # Make sure id matches name and is managed
    assert gr.data["name"] == "Jake1"
    assert gr.data["description"] == "title formatting and disciplines api added."
    assert gr.data["is_managed"] == True


def test_create_update_and_delete(
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
    # Make sure id matches name and is managed
    assert gr.data["name"] == "newgroup"
    assert gr.data["description"] == "newgroup description"
    assert gr.data["is_managed"] == True

    # Update group
    updated_data = copy.deepcopy(data)
    updated_data["description"] = "newgroup description updated"
    res = group_service.update(
        user_moderator.identity, gr.data["id"], updated_data
    ).to_dict()
    assert res["name"] == "newgroup"
    assert res["description"] == "newgroup description updated"

    gr = group_service.read(user_moderator.identity, res["id"])
    assert gr.data["name"] == "newgroup"
    assert gr.data["description"] == "newgroup description updated"

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
    assert gr.data["name"] == "newgroup1"

    # Invalid as no name
    with pytest.raises(ValidationError) as exc_info:
        group_service.create(
            user_moderator.identity,
            {
                "description": "newgroup description",
            },
        )
    assert exc_info.value.messages == ["Unexpected Issue: 'name'"]

    # Check group cannot be deleted by non user moderator user.
    with pytest.raises(PermissionDeniedError):
        group_service.delete(user_res.identity, res["id"])

    # Delete Group.
    group_service.delete(
        user_moderator.identity,
        res["id"],
    )
    # Check group is deleted.
    with pytest.raises(PermissionDeniedError):
        group_service.read(user_moderator.identity, res["id"])


def test_update_and_attempted_delete_of_super_admin_group(
    app, db, group_service, user_moderator, user_admin, clear_cache, search_clear
):
    """Test user can update super admin if has super_admin role, else is denied permission"""
    gac = group_service.record_cls
    ga = gac.get_record_by_name("admin")
    gr = group_service.read(user_admin.identity, ga.id)
    # Update group
    updated_data = copy.deepcopy(gr.data)
    updated_data["description"] = "Changing the description of the super admin group"
    # Fail update as group is superuser
    with pytest.raises(PermissionDeniedError):
        group_service.update(user_moderator.identity, gr.data["id"], updated_data)
    res = group_service.update(
        user_admin.identity, gr.data["id"], updated_data
    ).to_dict()
    # Make sure the description has been updated
    assert res["description"] == "Changing the description of the super admin group"

    # Permission denied for user_moderator as has no super admin role
    updated_data = copy.deepcopy(gr.data)
    updated_data["description"] = "Failed Change"

    with pytest.raises(PermissionDeniedError):
        group_service.update(user_moderator.identity, gr.data["id"], updated_data)

    with pytest.raises(PermissionDeniedError):
        group_service.delete(user_moderator.identity, gr.data["id"])


def test_add_user_to_role(
    app,
    db,
    group_service,
    user_admin,
    user_moderator,
    user_res,
    clear_cache,
    search_clear,
):
    """Test adding and removing user to group."""
    data = {
        "name": "newgroup",
        "description": "newgroup description",
    }
    res = group_service.create(user_moderator.identity, data).to_dict()
    assert res["name"] == "newgroup"

    gr = group_service.read(user_moderator.identity, res["id"])
    # Make sure id matches name and is managed
    assert gr.data["name"] == "newgroup"
    assert gr.data["description"] == "newgroup description"
    assert gr.data["is_managed"] == True

    # Add user to group
    gr = group_service.add_user(
        user_moderator.identity,
        res["id"],
        user_res.id,
    )

    gr = group_service.list_users(user_moderator.identity, res["id"])
    assert gr == {
        "hits": {
            "hits": [
                {
                    "email": user_res.email,
                    "id": int(user_res.id),
                    "username": user_res.username,
                }
            ]
        }
    }

    # Remove user from group
    gr = group_service.remove_user(
        user_moderator.identity,
        res["id"],
        user_res.id,
    )

    gr = group_service.list_users(user_moderator.identity, res["id"])
    assert gr == {"hits": {"hits": []}}

    gac = group_service.record_cls
    ga = gac.get_record_by_name("admin")

    with pytest.raises(PermissionDeniedError):
        group_service.add_user(user_moderator.identity, ga.id, user_res.id)
