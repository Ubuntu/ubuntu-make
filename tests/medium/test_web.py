# -*- coding: utf-8 -*-
# Copyright (C) 2015 Canonical
#
# Authors:
#  Didier Roche
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Tests for web category"""

from . import ContainerTests
import os
import pexpect
from ..large import test_web
from ..tools import get_data_dir, swap_file_and_restore, UMAKE


class FirefoxDevContainer(ContainerTests, test_web.FirefoxDevTests):
    """This will test the Firefox dev integration inside a container"""

    TIMEOUT_START = 20
    TIMEOUT_STOP = 10

    def setUp(self):
        self.hostname = "www.mozilla.org"
        self.port = "443"
        super().setUp()
        # override with container path
        self.installed_path = os.path.expanduser("/home/{}/tools/web/firefox-dev".format(self.DOCKER_USER))

    def test_install_with_changed_download_page(self):
        """Installing firefox developer should fail if download page has significantly changed"""
        download_page_file_path = os.path.join(get_data_dir(), "server-content", "www.mozilla.org", "en-US",
                                               "firefox", "developer", "all")
        fake_content = "<html></html>"
        with swap_file_and_restore(download_page_file_path):
            with open(download_page_file_path, "w") as newfile:
                newfile.write(fake_content)
            self.child = pexpect.spawnu(self.command('{} web firefox-dev'.format(UMAKE)))
            self.expect_and_no_warn("Choose installation path: {}".format(self.installed_path))
            self.child.sendline("")
            self.expect_and_no_warn("Download page changed its syntax or is not parsable", expect_warn=True)
            self.wait_and_close(exit_status=1)

            self.assertFalse(self.launcher_exists_and_is_pinned(self.desktop_filename))


class VisualStudioCodeContainer(ContainerTests, test_web.VisualStudioCodeTest):
    """This will test the Visual Studio Code integration inside a container"""

    TIMEOUT_START = 20
    TIMEOUT_STOP = 10

    def setUp(self):
        self.hostname = "code.visualstudio.com"
        self.port = "443"
        self.apt_repo_override_path = os.path.join(self.APT_FAKE_REPO_PATH, 'vscode')
        super().setUp()
        # override with container path
        self.installed_path = os.path.expanduser("/home/{}/tools/web/visual-studio-code".format(self.DOCKER_USER))

    def test_install_with_changed_download_page(self):
        """Installing visual studio code should fail if download page has significantly changed"""
        download_page_file_path = os.path.join(get_data_dir(), "server-content", "code.visualstudio.com", "Download")
        fake_content = "<html></html>"
        with swap_file_and_restore(download_page_file_path):
            with open(download_page_file_path, "w") as newfile:
                newfile.write(fake_content)
            self.child = pexpect.spawnu(self.command('{} web visual-studio-code'.format(UMAKE)))
            self.expect_and_no_warn("Choose installation path: {}".format(self.installed_path))
            self.child.sendline("")
            self.expect_and_no_warn("Download page changed its syntax or is not parsable", expect_warn=True)
            self.wait_and_close(exit_status=1)

            self.assertFalse(self.launcher_exists_and_is_pinned(self.desktop_filename))
