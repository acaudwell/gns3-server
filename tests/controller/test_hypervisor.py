#!/usr/bin/env python
#
# Copyright (C) 2016 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import pytest
import json
import aiohttp
from unittest.mock import patch, MagicMock

from gns3server.controller.project import Project
from gns3server.controller.hypervisor import Hypervisor, HypervisorError
from gns3server.version import __version__
from tests.utils import asyncio_patch


@pytest.fixture
def hypervisor():
    return Hypervisor("my_hypervisor_id", protocol="https", host="example.com", port=84, user="test", password="secure")


def test_init(hypervisor):
    assert hypervisor.id == "my_hypervisor_id"


def test_hypervisor_local(hypervisor):
    """
    If the hypervisor is local but the hypervisor id is local
    it's a configuration issue
    """

    with patch("gns3server.config.Config.get_section_config", return_value={"local": False}):
        with pytest.raises(HypervisorError):
            s = Hypervisor("local")

    with patch("gns3server.config.Config.get_section_config", return_value={"local": True}):
        s = Hypervisor("test")


def test_hypervisor_httpQuery(hypervisor, async_run):
    response = MagicMock()
    with asyncio_patch("aiohttp.ClientSession.request", return_value=response) as mock:
        response.status = 200

        async_run(hypervisor.post("/projects", {"a": "b"}))
        mock.assert_called_with("POST", "https://example.com:84/v2/hypervisor/projects", data='{"a": "b"}', headers={'content-type': 'application/json'})


def test_hypervisor_httpQueryError(hypervisor, async_run):
    response = MagicMock()
    with asyncio_patch("aiohttp.ClientSession.request", return_value=response) as mock:
        response.status = 409

        with pytest.raises(aiohttp.web.HTTPConflict):
            async_run(hypervisor.post("/projects", {"a": "b"}))


def test_hypervisor_httpQuery_project(hypervisor, async_run):
    response = MagicMock()
    with asyncio_patch("aiohttp.ClientSession.request", return_value=response) as mock:
        response.status = 200

        project = Project()
        async_run(hypervisor.post("/projects", project))
        mock.assert_called_with("POST", "https://example.com:84/v2/hypervisor/projects", data=json.dumps(project.__json__()), headers={'content-type': 'application/json'})


def test_json(hypervisor):
    assert hypervisor.__json__() == {
        "hypervisor_id": "my_hypervisor_id",
        "protocol": "https",
        "host": "example.com",
        "port": 84,
        "user": "test",
        "connected": False,
        "version": __version__
    }