from requests.auth import AuthBase
from urllib3.util import Timeout as TimeoutSauce

from Config import Config


class TestTimeout(TimeoutSauce):
    """Attaches Timers to the given Request object"""

    def __init__(self, **kwargs):
        config = Config().host
        connect = kwargs.get('connect') or config.wait_conn
        read = kwargs.get('read') or config.wait_read
        super().__init__(connect=connect, read=read)


class ApiKey(AuthBase):
    """Attaches HTTP ApiKey Authentication to the given Request object"""

    def __init__(self, apikey):
        """- setup any auth-related data"""
        self.apikey = apikey

    def __call__(self, r):
        """- modify and return the request"""
        r.headers['api_key'] = self.apikey
        return r
