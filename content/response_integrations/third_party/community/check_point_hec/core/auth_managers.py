import base64
import datetime
import hashlib
import time
import uuid
from abc import ABC, abstractmethod

import requests
from cached_property import cached_property
from jose import jwt

from .constants import SMART_API_VERSION


class AuthManager(ABC):
    api_version = SMART_API_VERSION

    def __init__(self, host: str, client_id: str, client_secret: str):
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = None

    @abstractmethod
    def get_token(self) -> str:
        pass

    @abstractmethod
    def headers(self, request_string: str = None, auth: bool = False) -> dict:
        pass


class CloudInfraAuthManager(AuthManager):

    def get_token(self) -> str:
        if self._should_refresh_token():
            payload = {
                "clientId": self.client_id,
                "accessKey": self.client_secret
            }
            timestamp = time.time()

            res = requests.post(f'https://{self.host}/auth/external', json=payload)
            res.raise_for_status()
            data = res.json()['data']
            self.token = data.get('token')
            self.token_expiry = timestamp + float(data.get('expiresIn'))

        return self.token

    def headers(self, request_string: str = None, auth: bool = False) -> dict:
        request_id = str(uuid.uuid4())
        token = self.get_token()
        return {
            'Authorization': f'Bearer {token}',
            'x-av-req-id': request_id,
        }

    def _should_refresh_token(self) -> bool:
        return not self.token or time.time() >= self.token_expiry


class SmartAPIAuthManager(AuthManager):

    def __init__(self, host: str, client_id: str, client_secret: str):
        super().__init__(host, client_id, client_secret)
        self.token_buffer = 60

    def get_token(self) -> str:
        if not self._should_refresh_token():
            return self.token

        res = requests.get(
            f'https://{self.host}/{self.api_version}/auth',
            headers=self.headers(auth=True)
        )
        res.raise_for_status()
        self.token = res.content.decode('utf-8')
        decoded_token = jwt.decode(self.token, self.public_key)
        self.token_expiry = decoded_token['exp']
        return self.token

    def headers(self, request_string: str = None, auth: bool = False) -> dict:
        request_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
        headers = {
            'x-av-req-id': request_id,
            'x-av-app-id': self.client_id,
            'x-av-date': timestamp,
            'x-av-sig': self._generate_signature(request_id, timestamp, request_string)
        }
        if not auth:
            headers['x-av-token'] = self.get_token()
        return headers

    @cached_property
    def public_key(self) -> dict:
        res = requests.get(f'https://{self.host}/{self.api_version}/public_key')
        res.raise_for_status()
        return res.json()

    def _should_refresh_token(self) -> bool:
        if not self.token:
            return True

        return time.time() + self.token_buffer > self.token_expiry

    def _generate_signature(self, request_id: str, timestamp: str, request_string: str = None) -> str:
        if request_string:
            signature_string = f'{request_id}{self.client_id}{timestamp}{request_string}' \
                               f'{self.client_secret}'
        else:
            signature_string = f'{request_id}{self.client_id}{timestamp}{self.client_secret}'
        signature_bytes = signature_string.encode('utf-8')
        signature_base64_bytes = base64.b64encode(signature_bytes)
        signature_hash = hashlib.sha256(signature_base64_bytes).hexdigest()
        return signature_hash
