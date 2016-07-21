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


import os
import json
import pytest
import aiohttp
import zipfile

from unittest.mock import patch
from unittest.mock import MagicMock
from tests.utils import AsyncioMagicMock

from gns3server.controller.project import Project
from gns3server.controller.export_project import export_project


@pytest.fixture
def project(controller):
    return Project(controller=controller, name="Test")


@pytest.fixture
def node(controller, project, async_run):
    compute = MagicMock()
    compute.id = "local"

    response = MagicMock()
    response.json = {"console": 2048}
    compute.post = AsyncioMagicMock(return_value=response)

    node = async_run(project.add_node(compute, "test", None, node_type="vpcs", properties={"startup_config": "test.cfg"}))
    return node


def test_export(tmpdir, project):
    path = project.path
    os.makedirs(os.path.join(path, "vm-1", "dynamips"))

    # The .gns3 should be renamed project.gns3 in order to simplify import
    with open(os.path.join(path, "test.gns3"), 'w+') as f:
        f.write("{}")

    with open(os.path.join(path, "vm-1", "dynamips", "test"), 'w+') as f:
        f.write("HELLO")
    with open(os.path.join(path, "vm-1", "dynamips", "test_log.txt"), 'w+') as f:
        f.write("LOG")
    os.makedirs(os.path.join(path, "project-files", "snapshots"))
    with open(os.path.join(path, "project-files", "snapshots", "test"), 'w+') as f:
        f.write("WORLD")

    z = export_project(project)

    with open(str(tmpdir / 'zipfile.zip'), 'wb') as f:
        for data in z:
            f.write(data)

    with zipfile.ZipFile(str(tmpdir / 'zipfile.zip')) as myzip:
        with myzip.open("vm-1/dynamips/test") as myfile:
            content = myfile.read()
            assert content == b"HELLO"

        assert 'test.gns3' not in myzip.namelist()
        assert 'project.gns3' in myzip.namelist()
        assert 'project-files/snapshots/test' not in myzip.namelist()
        assert 'vm-1/dynamips/test_log.txt' not in myzip.namelist()


def test_export_disallow_running(tmpdir, project, node):
    """
    Dissallow export when a node is running
    """

    path = project.path

    topology = {
        "topology": {
            "nodes": [
                    {
                        "node_type": "dynamips"
                    }
            ]
        }
    }

    with open(os.path.join(path, "test.gns3"), 'w+') as f:
        json.dump(topology, f)

    node._status = "started"
    with pytest.raises(aiohttp.web.HTTPConflict):
        z = export_project(project)


def test_export_disallow_some_type(tmpdir, project):
    """
    Dissalow export for some node type
    """

    path = project.path

    topology = {
        "topology": {
            "nodes": [
                    {
                        "node_type": "virtualbox"
                    }
            ]
        }
    }

    with open(os.path.join(path, "test.gns3"), 'w+') as f:
        json.dump(topology, f)

    with pytest.raises(aiohttp.web.HTTPConflict):
        z = export_project(project)


def test_export_fix_path(tmpdir, project):
    """
    Fix absolute image path
    """

    path = project.path

    topology = {
        "topology": {
            "nodes": [
                    {
                        "properties": {
                            "image": "/tmp/c3725-adventerprisek9-mz.124-25d.image"
                        },
                        "node_type": "dynamips"
                    }
            ]
        }
    }

    with open(os.path.join(path, "test.gns3"), 'w+') as f:
        json.dump(topology, f)

    z = export_project(project)
    with open(str(tmpdir / 'zipfile.zip'), 'wb') as f:
        for data in z:
            f.write(data)

    with zipfile.ZipFile(str(tmpdir / 'zipfile.zip')) as myzip:
        with myzip.open("project.gns3") as myfile:
            content = myfile.read().decode()
            topology = json.loads(content)
    assert topology["topology"]["nodes"][0]["properties"]["image"] == "c3725-adventerprisek9-mz.124-25d.image"


def test_export_with_images(tmpdir, project):
    """
    Fix absolute image path
    """
    path = project.path

    os.makedirs(str(tmpdir / "IOS"))
    with open(str(tmpdir / "IOS" / "test.image"), "w+") as f:
        f.write("AAA")

    topology = {
        "topology": {
            "nodes": [
                    {
                        "properties": {
                            "image": "test.image"
                        },
                        "node_type": "dynamips"
                    }
            ]
        }
    }

    with open(os.path.join(path, "test.gns3"), 'w+') as f:
        json.dump(topology, f)

    with patch("gns3server.compute.Dynamips.get_images_directory", return_value=str(tmpdir / "IOS"),):
        z = export_project(project, include_images=True)
        with open(str(tmpdir / 'zipfile.zip'), 'wb') as f:
            for data in z:
                f.write(data)

    with zipfile.ZipFile(str(tmpdir / 'zipfile.zip')) as myzip:
        myzip.getinfo("images/IOS/test.image")
