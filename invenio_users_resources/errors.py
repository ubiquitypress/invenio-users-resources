# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Ubiquity Press.
#
# Invenio-Users-Resources is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Group errors."""


class ForeignKeyIntegrityError(Exception):
    """Error for failed requests to delete a group."""
