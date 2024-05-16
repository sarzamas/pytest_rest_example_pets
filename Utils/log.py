import logging

from Config.settings import DEBUG

logger = logging.getLogger('root')

LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
LOG_LEVEL_SETUP_TEARDOWN = logging.DEBUG if DEBUG else logging.WARNING

logger.setLevel(LOG_LEVEL)
