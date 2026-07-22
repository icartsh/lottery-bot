import logging
import time

import requests

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 2


class HttpClient:
    def __init__(self):
        self.session = requests.Session()

    def __del__(self):
        self.session.close()

    def post(self, url: str, headers: dict = None, data: dict = None, retries: int = 1) -> requests.Response:
        return self._request_with_retry("POST", url, headers=headers, data=data, retries=retries)

    def get(self, url: str, headers: dict = None, params: dict = None, retries: int = 1) -> requests.Response:
        return self._request_with_retry("GET", url, headers=headers, params=params, retries=retries)

    def _request_with_retry(self, method: str, url: str, headers: dict = None,
                            data: dict = None, params: dict = None, retries: int = 1) -> requests.Response:
        session_headers = self.session.headers.copy()
        if headers:
            session_headers.update(headers)

        for attempt in range(retries):
            try:
                res = self.session.request(
                    method, url,
                    headers=session_headers, data=data, params=params,
                    timeout=30, allow_redirects=True,
                )
                res.raise_for_status()
                return res
            except requests.RequestException as e:
                if attempt < retries - 1:
                    logger.warning(f"[Retry] {method} {url} failed ({attempt + 1}/{retries}): {e}. Retrying in {RETRY_DELAY_SECONDS}s...")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    if retries > 1:
                        logger.error(f"[Error] {method} {url} failed after {retries} attempts: {e}")
                    raise


class HttpClientSingleton:
    _instance = None

    @staticmethod
    def get_instance():
        if HttpClientSingleton._instance is None:
            HttpClientSingleton._instance = HttpClient()
        return HttpClientSingleton._instance
