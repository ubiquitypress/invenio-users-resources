# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Groups resource tests."""


def test_group_avatar(app, client, group, not_managed_group, user_pub):
    res = client.get(f"/groups/{not_managed_group.name}/avatar.svg")
    assert res.status_code == 403

    user_pub.login(client)

    # unmanaged group can be retrieved
    res = client.get(f"/groups/{not_managed_group.name}/avatar.svg")
    assert res.status_code == 200
    assert res.mimetype == "image/svg+xml"
    data = res.get_data()

    # managed group can *not* be retrieved
    res = client.get(f"/groups/{group.name}/avatar.svg")
    assert res.status_code == 403


#
# Management / moderation
#
def test_create_and_update_group(client, headers, user_moderator, db, search_clear):
    """Tests approve user endpoint."""
    client = user_moderator.login(client)
    res = client.post(
        "/groups",
        json={
            "name": "newgroup",
            "description": "New group description",
            "is_managed": True,
        },
        headers=headers,
    )
    assert res.status_code == 201

    res = client.get(f"/groups/{res.json['id']}")
    assert res.status_code == 200
    assert res.json["name"] == "newgroup"
    assert res.json["description"] == "New group description"
    assert res.json["is_managed"] == True

    res = client.put(
        f"/groups/{res.json['id']}",
        json={
            "name": "newgroup",
            "description": "New group description updated",
            "is_managed": True,
        },
        headers=headers,
    )
    assert res.status_code == 200

    res = client.get(f"/groups/{res.json['id']}")
    assert res.status_code == 200
    assert res.json["name"] == "newgroup"
    assert res.json["description"] == "New group description updated"
    assert res.json["is_managed"] == True

    # Deleting group
    id_to_delete = res.json["id"]
    res = client.delete(f"/groups/{id_to_delete}")
    assert res.status_code == 204

    res = client.get(f"/groups/{id_to_delete}")
    assert res.status_code == 403


# TODO: test conditional requests
# TODO: test caching headers
# TODO: test invalid identifiers
