import os

## GLOBAL CONFIGURATION

FETCH_INTERVAL = 5
REGION = "us"


class Indices:
    LAST_UPDATED_BY = "last_updated_by"
    LAST_UPDATED_AT = "last_updated_at"
    CHANNELS = "channels"
    WATCHLIST = "watchlist"
    BUILDINFO = "buildInfo"
    REGION = "region"
    BUILD = "build"
    BUILDTEXT = "build_text"


## CACHE CONFIGURATION


class CacheStrings:
    ## STRINGS
    BRANCH_NOT_VALID = "Branch is not a valid product."
    BRANCH_ALREADY_IN_WATCHLIST = "Branch is already on your watchlist."

    ## LOGGING STRINGS
    LOG_FETCH_DATA = "Fetching CDN data..."
    LOG_PARSE_DATA = "Parsing CDN response..."

    ## ARG STRINGS
    ARG_BRANCH_NOT_ON_WATCHLIST = "Argument 'branch' is not on the watchlist."


class CacheDefaults:
    WATCHLIST = ["wow", "wowt", "wow_beta"]
    REGION = REGION
    BUILD = "0.0.0"
    BUILDTEXT = "untracked"


class CacheConfig:
    CDN_URL = "http://us.patch.battle.net:1119/"
    PRODUCTS = {  # wowdev is commented out because the endpoint is broken
        "wow": "Retail",
        "wowt": "Retail PTR",
        "wow_beta": "Beta",
        "wow_classic": "WotLK Classic",
        "wow_classic_ptr": "WotLK Classic PTR",
        "wow_classic_beta": "Classic Beta",
        "wow_classic_era": "Classic Era",
        "wow_classic_era_ptr": "Classic Era PTR",
        "wowz": "Submission",
        "wowlivetest": "Live Test",
        # "wowdev": "Internal"
    }
    AREAS_TO_CHECK_FOR_UPDATES = ["build", "build_text"]
    CACHE_FOLDER_NAME = "cache"
    CACHE_FILE_NAME = "cdn.json"

    strings = CacheStrings()
    indices = Indices()
    defaults = CacheDefaults()


## WATCHER CONFIGURATION


class WatcherStrings:
    EMBED_WOWTOOLS_TITLE = "wow.tools builds page"
    EMBED_WOWTOOLS_URL = "https://wow.tools/builds/"

    EMBED_NAME = "Blizzard CDN Update"
    EMBED_ICON_URL = (
        "https://bnetcmsus-a.akamaihd.net/cms/gallery/D2TTHKAPW9BH1534981363136.png"
    )
    EMBED_FOOTER = "Data provided by the prestigious Algalon 2.0."

    EMBED_UPDATE_TITLE = "Branch Updates"


class WatcherConfig:
    strings = WatcherStrings()
    indices = Indices()
    cache_defaults = CacheDefaults()


## DEBUG CONFIGURATION


class DebugConfig:
    debug_enabled = os.getenv("DEBUG")
    debug_guild_id = os.getenv("DEBUG_GUILD_ID")
    debug_channel_id = os.getenv("DEBUG_CHANNEL_ID")


DebugConfig()
