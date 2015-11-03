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


"""Web module"""

from contextlib import suppress
from functools import partial
from gettext import gettext as _
from io import StringIO
import logging
import os
import platform
import re
import umake.frameworks.baseinstaller
from umake.interactions import Choice, LicenseAgreement, TextWithChoices
from umake.network.download_center import DownloadCenter, DownloadItem
from umake.ui import UI
from umake.tools import create_launcher, get_application_desktop_file, Checksum, MainLoop, strip_tags

logger = logging.getLogger(__name__)

_supported_archs = ['i386', 'amd64']


class WebCategory(umake.frameworks.BaseCategory):

    def __init__(self):
        super().__init__(name="Web", description=_("Web Developer Environment"), logo_path=None)


class FirefoxDev(umake.frameworks.baseinstaller.BaseInstaller):

    def __init__(self, category):
        super().__init__(name="Firefox Dev", description=_("Firefox Developer Edition"),
                         category=category, only_on_archs=_supported_archs,
                         download_page="https://www.mozilla.org/en-US/firefox/developer/all",
                         dir_to_decompress_in_tarball="firefox",
                         desktop_filename="firefox-developer.desktop",
                         required_files_path=["firefox"])
        self.arg_lang = None

    @MainLoop.in_mainloop_thread
    def language_select_callback(self, url):
        url = url.replace("&amp;", "&")
        logger.debug("Found download link for {}".format(url))
        self.download_requests.append(DownloadItem(url, None))
        self.start_download_and_install()

    @MainLoop.in_mainloop_thread
    def get_metadata_and_check_license(self, result):
        """Diverge from the baseinstaller implementation in order to allow language selection"""

        logger.debug("Parse download metadata")
        error_msg = result[self.download_page].error
        if error_msg:
            logger.error("An error occurred while downloading {}: {}".format(self.download_page, error_msg))
            UI.return_main_screen(status_code=1)

        arch = platform.machine()
        arg_lang_url = None
        default_label = ''
        tag_machine = ''
        if arch == 'x86_64':
            tag_machine = '64'

        reg_expression = '<td class="download linux{}"><a href="(.*)" title'.format(tag_machine)
        languages = []
        decoded_page = result[self.download_page].buffer.getvalue().decode()
        for index, p in enumerate(re.finditer(reg_expression, decoded_page)):
            with suppress(AttributeError):
                url = p.group(1)

            m = re.search(r'lang=(.*)', url)
            with suppress(AttributeError):
                lang = m.group(1)

            if self.arg_lang and self.arg_lang.lower() == lang.lower():
                arg_lang_url = url
                break
            else:
                is_default_choice = False
                if lang == "en-US":
                    default_label = "(default: en-US)"
                    is_default_choice = True
                choice = Choice(index, lang, partial(self.language_select_callback, url), is_default=is_default_choice)
                languages.append(choice)

        if self.arg_lang:
            logger.debug("Selecting {} lang".format(self.arg_lang))
            if not arg_lang_url:
                logger.error("Could not find a download url for language {}".format(self.arg_lang))
                UI.return_main_screen(status_code=1)
            self.language_select_callback(arg_lang_url)
        else:
            if not languages:
                logger.error("Download page changed its syntax or is not parsable")
                UI.return_main_screen(status_code=1)
            logger.debug("Check list of installable languages.")
            UI.delayed_display(TextWithChoices(_("Choose language: {}".format(default_label)), languages, True))

    def post_install(self):
        """Create the Firefox Developer launcher"""
        create_launcher(self.desktop_filename, get_application_desktop_file(name=_("Firefox Developer Edition"),
                        icon_path=os.path.join(self.install_path, "browser", "icons", "mozicon128.png"),
                        exec=os.path.join(self.install_path, "firefox"),
                        comment=_("Firefox Aurora with Developer tools"),
                        categories="Development;IDE;"))

    def install_framework_parser(self, parser):
        this_framework_parser = super().install_framework_parser(parser)
        this_framework_parser.add_argument('--lang', dest="lang", action="store",
                                           help=_("Install in given language without prompting"))
        return this_framework_parser

    def run_for(self, args):
        if args.lang:
            self.arg_lang = args.lang
        super().run_for(args)


class VisualStudioCode(umake.frameworks.baseinstaller.BaseInstaller):

    def __init__(self, category):
        super().__init__(name="Visual Studio Code", description=_("Visual Studio focused on modern web and cloud"),
                         category=category, only_on_archs=_supported_archs, expect_license=True,
                         download_page="https://code.visualstudio.com/Docs",
                         desktop_filename="visual-studio-code.desktop",
                         required_files_path=["Code"],
                         dir_to_decompress_in_tarball="VSCode-linux-*",
                         packages_requirements=["libgtk2.0-0"])
        self.license_url = "https://code.visualstudio.com/License"
        # we have to mock headers for visual studio code website to give us an answer
        self.headers = {'User-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu "
                                      "Chromium/41.0.2272.76 Chrome/41.0.2272.76 Safari/537.36"}

    def download_provider_page(self):
        logger.debug("Download application provider page")
        DownloadCenter([DownloadItem(self.download_page, headers=self.headers)], self.get_metadata, download=False)

    @MainLoop.in_mainloop_thread
    def get_metadata(self, result):
        """Download files to download + and download license license and check it"""
        logger.debug("Parse download metadata")

        error_msg = result[self.download_page].error
        if error_msg:
            logger.error("An error occurred while downloading {}: {}".format(self.download_page, error_msg))
            UI.return_main_screen(status_code=1)

        arch = platform.machine()
        download_re = r'\'linux64\': \'([^\']+)\''
        if arch == 'i686':
            download_re = r'\'linux32\': \'([^\']+)\''
        url = None
        for line in result[self.download_page].buffer:
            line = line.decode()
            p = re.search(download_re, line)
            with suppress(AttributeError):
                url = p.group(1)
                logger.debug("Found download link for {}".format(url))

        if url is None:
            logger.error("Download page changed its syntax or is not parsable")
            UI.return_main_screen(status_code=1)
        self.download_requests.append(DownloadItem(url, Checksum(self.checksum_type, None), headers=self.headers))

        if not self.auto_accept_license:
            logger.debug("Downloading License page")
            DownloadCenter([DownloadItem(self.license_url, headers=self.headers)], self.check_external_license,
                           download=False)
        else:
            self.start_download_and_install()

    @MainLoop.in_mainloop_thread
    def check_external_license(self, result):
        """Check external license which is in a separate page (can be factorized in BaseInstaller)"""
        logger.debug("Parse license page")
        error_msg = result[self.license_url].error
        if error_msg:
            logger.error("An error occurred while downloading {}: {}".format(self.license_url, error_msg))
            UI.return_main_screen(status_code=1)

        with StringIO() as license_txt:
            in_license = False
            for line in result[self.license_url].buffer:
                line = line.decode()
                if ('SOFTWARE LICENSE TERMS' in line):
                    in_license = True
                if in_license and "<strong>*   *   *</strong>" in line:
                    in_license = False
                    continue
                if in_license:
                    license_txt.write(line.strip() + "\n")

            if license_txt.getvalue() != "":
                logger.debug("Check license agreement.")
                UI.display(LicenseAgreement(strip_tags(license_txt.getvalue()).strip(),
                                            self.start_download_and_install,
                                            UI.return_main_screen))
            else:
                logger.error("We were expecting to find a license, we didn't.")
                UI.return_main_screen(status_code=1)

    def post_install(self):
        """Create the Visual Studio Code launcher"""
        create_launcher(self.desktop_filename, get_application_desktop_file(name=_("Visual Studio Code"),
                        icon_path=os.path.join(self.install_path, "resources", "app", "vso.png"),
                        exec=os.path.join(self.install_path, "Code"),
                        comment=_("Visual Studio focused on modern web and cloud"),
                        categories="Development;IDE;"))
