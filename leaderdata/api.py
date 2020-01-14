import json
import logging
from functools import partial
from typing import Any, Optional, Tuple

import httpx
from leaderdata.conf import DSN, OPENAPI_PATH, ensure_openapi_exists
from leaderdata.exceptions import (
    APIServerError,
    BadRequestError,
    MissingRequiredParam,
    OperationNotFoundError,
)

logger = logging.getLogger(__name__)


class Spec:
    """Интерфейс для работы со спецификацией API"""

    _spec: dict = None
    _paths: dict = None

    @classmethod
    def ensure_spec_loaded(cls):
        """Загрузка спецификации при необходимости"""
        if cls._spec is None:
            logger.debug('loading API specification')
            ensure_openapi_exists()
            with open(OPENAPI_PATH, 'r') as fh:
                cls._spec = json.load(fh)
                logger.debug('API specification loaded')

    @classmethod
    def _init_paths(cls):
        """Инициализация маппинга операций"""
        cls._paths = dict()
        for path, operation in cls._spec['paths'].items():
            for method, spec in operation.items():
                cls._paths[spec['operationId']] = (path, method, spec)

    @classmethod
    def get_operation(cls, operation_id: str) -> Tuple[str, str, dict]:
        """Чтение HTTP метода и спецификации операции"""
        if cls._paths is None:
            cls._init_paths()

        if operation_id not in cls._paths:
            raise OperationNotFoundError(operation_id)

        return cls._paths[operation_id]


class Client:
    """Клиент LeaderData API"""

    client_id: str
    client_secret: str
    token: Optional[str] = None

    def __init__(self, client_id: str, client_secret: str):
        self.token = None
        self.client_id = client_id
        self.client_secret = client_secret
        Spec.ensure_spec_loaded()

    def __getattr__(self, name: str):
        if not name.startswith('_'):
            path, method, spec = Spec.get_operation(name)
            return partial(self._request, name, path, method, spec)
        return super().__getattr__(name)

    def _request(
        self,
        operation_id: str,
        path: str,
        method: str,
        spec: dict,
        body: Any = None,
        is_auth: bool = False,
        try_auth: bool = True,
        **kwargs,
    ):
        """Запрос в API LeaderData"""
        margs = {}

        if body:
            margs['json'] = body

        if self.token:
            margs.setdefault('headers', {})['Authorization'] = f'Bearer {self.token}'

        for param in spec.get('parameters', []):
            name = param.get('name')

            if name in kwargs:
                if param['in'] == 'query':
                    margs.setdefault('params', {})[name] = kwargs[name]
                elif param['in'] == 'path':
                    path = path.replace(f'{{{name}}}', str(kwargs[name]))

            elif param['required'] is True:
                raise MissingRequiredParam(name, operation_id)

        response: httpx.Response = getattr(httpx, method)(f'{DSN}{path}', **margs)

        if 400 <= response.status_code < 500:
            if response.status_code == 403 and try_auth:
                # Попытка авторизации
                logger.debug('Not authenticated error, try auth..')
                try:
                    self.auth__application_authentication(
                        is_auth=True,
                        try_auth=False,
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                    )
                except BadRequestError:
                    # fail =(
                    logger.debug('Authentication failed')
                    raise
                else:
                    # Успешная авторизация, повтор оригинального запроса.
                    logger.debug('Authentication success, retry request')
                    return self._request(
                        operation_id=operation_id,
                        path=path,
                        method=method,
                        spec=spec,
                        body=body,
                        try_auth=False,
                        **kwargs,
                    )
            raise BadRequestError(response=response)

        elif response.status_code >= 500:
            raise APIServerError(response=response)

        if is_auth:
            self.token = response.json().get('access_token')

        return response.json()
