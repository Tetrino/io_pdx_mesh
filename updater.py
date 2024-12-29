"""
IO PDX Mesh Python module.
This is designed to allow tools to check if they are out of date or not and supply a download link to the latest.

author : ross-g
"""

import json
import logging
from datetime import date, datetime
from os.path import splitext
from time import perf_counter
from urllib.request import Request, URLError, urlopen

from . import IO_PDX_INFO, IO_PDX_SETTINGS

UPDATER_LOG = logging.getLogger("io_pdx.updater")


""" ====================================================================================================================
    Helper functions.
==================================================================================================================== """


class Github_API(object):
    """
    Handles connection to Githubs API to get some data on releases for this repository.
    """

    API_URL = "https://api.github.com"

    def __init__(self, owner, repo):
        self.api = self.API_URL
        self.owner = owner
        self.repo = repo
        self.args = {"owner": self.owner, "repo": self.repo, "api": self.api}

        self.AT_LATEST = False
        self.LATEST_VERSION = 0.0
        self.LATEST_RELEASE = "https://github.com/{owner}/{repo}/releases/latest".format(**self.args)
        self.LATEST_NOTES = ""
        self.LATEST_URL = ""
        self.CURRENT_VERSION = IO_PDX_INFO["current_git_tag"]
        self.refresh()

    @staticmethod
    def get_data(url, time=1.0):
        req = Request(url)
        result = urlopen(req, timeout=time)
        result_str = result.read()
        result.close()

        return json.JSONDecoder().decode(result_str.decode())

    def refresh(self, force=False):
        recheck = True

        # only check for updates once per day
        last_check_date = IO_PDX_SETTINGS.last_update_check
        if last_check_date is not None:
            recheck = date.today() > datetime.strptime(last_check_date, "%Y-%m-%d").date()

        if recheck or force:
            start = perf_counter()

            # get latest release data
            releases_url = "{api}/repos/{owner}/{repo}/releases".format(**self.args)

            try:
                release_list = self.get_data(releases_url)
                self.LATEST_RELEASE = release_list[0]
            except URLError as err:
                UPDATER_LOG.warning(f"Unable to check for update. ({err.reason})")
                return
            except IndexError as err:
                UPDATER_LOG.warning(f"Found no releases during update check. ({err})")
            except Exception as err:
                UPDATER_LOG.error(f"Failed during update check. ({err})")
                return

            latest = release_list[0]

            # store data
            self.LATEST_VERSION = float(latest["tag_name"])
            self.LATEST_URL = {
                splitext(asset["name"])[0].split("-")[0]: asset["browser_download_url"] for asset in latest["assets"]
            }
            self.LATEST_NOTES = (
                f"{latest['published_at'].split('T')[0]}\r\n"
                f"Release version: {latest['tag_name']}\r\n"
                f"{latest['body']}"
            )

            # cache data to settings
            IO_PDX_SETTINGS.github_latest_version = self.LATEST_VERSION
            IO_PDX_SETTINGS.github_latest_url = self.LATEST_URL
            IO_PDX_SETTINGS.github_latest_notes = self.LATEST_NOTES

            IO_PDX_SETTINGS.last_update_check = f"{date.today()}"
            UPDATER_LOG.info(f"Checked for update. ({perf_counter() - start:0.4f} sec)")

        else:
            # used cached release data in settings
            self.LATEST_VERSION = IO_PDX_SETTINGS.github_latest_version
            self.LATEST_URL = IO_PDX_SETTINGS.github_latest_url
            self.LATEST_NOTES = IO_PDX_SETTINGS.github_latest_notes

            UPDATER_LOG.info("Skipped update check. (already ran today)")

        self.AT_LATEST = self.CURRENT_VERSION == self.LATEST_VERSION


github = Github_API(owner=IO_PDX_INFO["maintainer"], repo=IO_PDX_INFO["id"])
