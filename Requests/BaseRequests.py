import logging
from dataclasses import asdict, is_dataclass
from typing import Any

import requests
from helpers.data_collector import DataCollector
from helpers.report import allure_attach_response
from requests import JSONDecodeError, Response


class BaseRequests:
    """
    Класс обертка для HTTP запросов
    """

    def __init__(self):
        self.headers: dict = {"Content-type": "application/x-www-form-urlencoded"}
        self.cookies: dict = {}
        self.data_collector = DataCollector()
        self.log = logging.getLogger('requests')

    def update_headers(self, headers: dict):
        """update_headers"""
        if headers is not None:
            for key, item in headers.items():
                self.headers[key] = item
        else:
            if self.data_collector.access_token:
                self.headers.update({"Authorization": f"Bearer {self.data_collector.access_token}"})

    def update_cookies(self, cookies: dict):
        """update_cookies"""
        if cookies is not None:
            for key, item in cookies.items():
                self.cookies[key] = item
        else:
            self.cookies = self.data_collector.cookie

    @allure_attach_response
    def send_request(
        self, method: Any,
        url: str,
        headers: Any = None,
        cookies: dict = None,
        json: Any = None,
        data: Any = None,
    ) -> Response:
        """send_request"""
        self.update_headers(headers)
        self.update_cookies(cookies)
        if is_dataclass(data):
            data = asdict(data)
        if is_dataclass(json):
            json = asdict(json)
        response = requests.request(
            method, url, headers=self.headers, data=data, json=json, cookies=self.cookies, verify=False,
            allow_redirects=False,
        )
        self.log.debug(response.text)
        try:
            if response.text:
                data = DataCollector(response.json())
                self.log.debug(data)
        except JSONDecodeError:
            return response
        return response
