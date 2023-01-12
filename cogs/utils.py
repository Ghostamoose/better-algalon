import os
import time
import logging

from datetime import datetime

logger = logging.getLogger("discord.cdnbot_utils")

def create_directory(path: str):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        return False

def get_self_path():
    return os.path.dirname(os.path.realpath(__file__))


def log_start():
    log_separator()
    logger.info(f"{get_date()} - Starting CDNBot...")
    log_separator()


def log_separator():
    logger.info("-----------------------------------------------------")


def get_discord_timestamp(relative=False):
        """Returns a formatted timestamp for use in Discord embeds or messages."""
        current_time = int(time.time())
        if relative:
            return f"<t:{current_time}:R>"
        else:
            return f"<t:{current_time}:f>"


def get_timestamp(day_only=False):
    if day_only:
        return datetime.now().strftime("%Y-%m-%d")
    else:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_date():
    return datetime.now().strftime("%m-%d-%Y @ %H:%M")


def get_time_delta(start_time: str, end_time: str):
    """Returns the difference between two times in minutes"""
    t1 = datetime.strptime(start_time, "%Y-%m-%d_%H-%M-%S")
    t2 = datetime.strptime(end_time, "%Y-%m-%d_%H-%M-%S")

    delta = t2 - t1

    return int(delta.seconds / 60)


class DictToClass:
    def __init__(self, d, target: object):
        self.d = d
        self.target = target

    def convert(self):
        if isinstance(self.d, dict):
            item = self.target()
            for key in self.d:
                setattr(item, key, self.d[key])
            return item
        elif isinstance(self.d, list):
            objects = []
            for config in self.d:
                item = self.target()
                for key in config:
                    setattr(item, key, config[key])
                objects.append(item)
            return objects


if __name__ == "__main__":
    time = "2022-02-20_21-19-30"
    print(get_time_delta(time, get_timestamp()))
