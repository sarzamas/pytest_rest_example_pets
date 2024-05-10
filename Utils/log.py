import logging

from settings import DEBUG

logger = logging.getLogger('root')

logging_level = logging.DEBUG if DEBUG else logging.INFO
logging_level_setup_teardown = logging.DEBUG if DEBUG else logging.WARNING

logger.setLevel(logging_level)
