from future import standard_library
standard_library.install_aliases()
import configparser

from lib.logger import get_logger

logger = get_logger(__name__)


def get_config_var(filepath, section, key):
    print(filepath)

    config = configparser.RawConfigParser()
    config.read(filepath)
    section_dict = dict(config.items('live'))

    return section_dict[key]
