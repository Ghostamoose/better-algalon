import os
import sys
import time
import json
import httpx
import logging

from .config import CacheConfig, FETCH_INTERVAL

logger = logging.getLogger("discord.cdn.cache")


class CDNCache:
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    PLATFORM = sys.platform
    CONFIG = CacheConfig()

    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.data_path = os.path.join(self.cache_path, self.CONFIG.CACHE_FILE_NAME)

        load_watchlist = True

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_json()

        if load_watchlist:
            self.watchlist, self.channels = self.load_watchlist()
            self.save_watchlist()
        else:
            self.watchlist = self.CONFIG.defaults.WATCHLIST
            self.save_watchlist()

    def init_json(self):
        """Populates the `cdn.json` file with default values if it does not exist."""
        with open(self.data_path, "w") as file:
            template = {
                self.CONFIG.indices.BUILDINFO: {},
                self.CONFIG.indices.WATCHLIST: {
                    857764832542851092: self.CONFIG.defaults.WATCHLIST
                },
                self.CONFIG.indices.LAST_UPDATED_BY: self.PLATFORM,
                self.CONFIG.indices.LAST_UPDATED_AT: time.time(),
            }

            json.dump(template, file, indent=4)

    def init_watchlist(self, key: int):
        """Creates the watchlist with default values."""
        self.add_to_watchlist("wow", key)

    def add_to_watchlist(self, branch: str, guild_id: int):
        """Adds a specific `branch` to the watchlist for guild `guild_id`."""
        if branch not in self.CONFIG.PRODUCTS.keys():
            return self.CONFIG.strings.BRANCH_NOT_VALID
        else:
            if guild_id in self.watchlist.keys():
                if branch in self.watchlist[guild_id]:
                    return self.CONFIG.strings.BRANCH_ALREADY_IN_WATCHLIST
                else:
                    self.watchlist[guild_id].append(branch)
                    self.save_watchlist()
                    return True
            else:
                self.watchlist[guild_id] = [branch]
                self.save_watchlist()
                return True

    def remove_from_watchlist(self, branch: str, guild_id: int):
        """Removes specified `branch` from watchlist for guild `guild_id`."""
        if guild_id in self.watchlist.keys():
            if branch not in self.watchlist[guild_id]:
                raise ValueError(self.CONFIG.strings.ARG_BRANCH_NOT_ON_WATCHLIST)
            else:
                self.watchlist.remove(branch)
                self.save_watchlist()
        else:
            return False

    def load_watchlist(self):
        """Loads the watchlist from the `cdn.json` file."""
        logger.debug("Loading existing watchlist from file...")
        with open(self.data_path, "r") as file:
            file = json.load(file)
            if not self.CONFIG.indices.LAST_UPDATED_BY in file:
                file[self.CONFIG.indices.LAST_UPDATED_BY] = self.PLATFORM

            if not self.CONFIG.indices.LAST_UPDATED_AT in file:
                file[self.CONFIG.indices.LAST_UPDATED_AT] = time.time()

            if not self.CONFIG.indices.CHANNELS in file:
                file[self.CONFIG.indices.CHANNELS] = {}

            return (
                file[self.CONFIG.indices.WATCHLIST],
                file[self.CONFIG.indices.CHANNELS],
            )

    def save_watchlist(self):
        """Saves the watchlist to the `cdn.json` file."""
        logger.info("Saving configuration...")

        with open(self.data_path, "r+") as file:
            file_json = json.load(file)
            file_json[self.CONFIG.indices.WATCHLIST] = self.watchlist
            file_json[self.CONFIG.indices.CHANNELS] = self.channels
            file_json[self.CONFIG.indices.LAST_UPDATED_BY] = self.PLATFORM
            file_json[self.CONFIG.indices.LAST_UPDATED_AT] = time.time()

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def set_channel(self, channel_id: int, guild_id: int):
        """Sets the notification channel to `channel_id` for the guild `guild_id`."""
        logger.info(f"Setting notification channel for {guild_id} to {channel_id}.")
        self.channels[str(guild_id)] = channel_id
        self.save_watchlist()

    def get_channel(self, guild_id: int):
        """Returns the `channel_id` for the notification channel of guild `guild_id`."""
        logger.info(f"Getting notification channel for {guild_id}.")
        if str(guild_id) in self.channels.keys():
            return self.channels[str(guild_id)]
        else:
            return False

    def compare_builds(self, branch: str, newBuild: dict) -> bool:
        """
        Compares two builds.

        Returns `True` if the build is new, else `False`.
        """
        with open(self.data_path, "r") as file:
            file_json = json.load(file)

            if file_json[self.CONFIG.indices.LAST_UPDATED_BY] != self.PLATFORM and (
                time.time() - file_json[self.CONFIG.indices.LAST_UPDATED_AT]
            ) < (FETCH_INTERVAL * 60):
                logger.info("Skipping build comparison, data is outdated")
                return False

            for area in self.CONFIG.AREAS_TO_CHECK_FOR_UPDATES:
                if branch in file_json[self.CONFIG.indices.BUILDINFO]:
                    if (
                        file_json[self.CONFIG.indices.BUILDINFO][branch][area]
                        != newBuild[area]
                    ):
                        return True
                    else:
                        return False
                else:
                    file_json[self.CONFIG.indices.BUILDINFO][branch][area] = newBuild[
                        area
                    ]
                    return True
            return False

    def save_build_data(self, branch: str, data: dict):
        """Saves new build data to the `cdn.json` file."""
        with open(self.data_path, "r+") as file:
            file_json = json.load(file)
            file_json[self.CONFIG.indices.BUILDINFO][branch] = data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def load_build_data(self, branch: str):
        """Loads existing build data from the `cdn.json` file."""
        with open(self.data_path, "r") as file:
            file_json = json.load(file)
            if branch in file_json[self.CONFIG.indices.BUILDINFO]:
                return file_json[self.CONFIG.indices.BUILDINFO][branch]
            else:
                file_json[self.CONFIG.indices.BUILDINFO][branch] = {
                    self.CONFIG.indices.REGION: self.CONFIG.defaults.REGION,
                    self.CONFIG.indices.BUILD: self.CONFIG.defaults.BUILD,
                    self.CONFIG.indices.BUILDTEXT: self.CONFIG.defaults.BUILDTEXT,
                }
                return False

    async def fetch_cdn(self):
        """This is a disaster."""
        logger.debug(self.CONFIG.strings.LOG_FETCH_DATA)
        async with httpx.AsyncClient() as client:
            new_data = []
            for branch in self.CONFIG.PRODUCTS:
                try:
                    logger.debug(f"Grabbing data for branch: {branch}")
                    url = self.CONFIG.CDN_URL + branch + "/versions"

                    res = await client.get(url, timeout=20)
                    logger.debug(self.CONFIG.strings.LOG_PARSE_DATA)
                    data = self.parse_response(branch, res.text)

                    if data:
                        logger.debug(f"Comparing build data for {branch}")
                        is_new = self.compare_builds(branch, data)

                        if is_new:
                            output_data = data.copy()

                            old_data = self.load_build_data(branch)

                            if old_data:
                                output_data["old"] = old_data

                            output_data["branch"] = branch
                            new_data.append(output_data)

                        logger.debug(f"Saving build data for {branch}")
                        self.save_build_data(branch, data)
                    else:
                        continue
                except Exception as exc:
                    logger.error(f"Timeout error during CDN check for {branch}")
                    return exc

            return new_data

    def parse_response(self, branch: str, response: str):
        """Parses the API response and attempts to return the new data."""
        try:
            data = response.split("\n")
            if len(data) < 3:
                return False
            data = data[2].split("|")
            region = data[0]
            build_config = data[1]
            cdn_config = data[2]
            build_number = data[4]
            build_text = data[5].replace(build_number, "")[:-1]
            product_config = data[6]

            output = {
                self.CONFIG.indices.REGION: region,
                "build_config": build_config,
                "cdn_config": cdn_config,
                "build": build_number,
                "build_text": build_text,
                "product_config": product_config,
            }

            return output
        except Exception as exc:
            logger.error(
                f"Encountered an error parsing API response for branch: {branch}."
            )
            logger.error(exc)

            return False
