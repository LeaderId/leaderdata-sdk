import json
import logging
from datetime import datetime
from functools import partial
from typing import Any, List, Optional, Tuple, Type, Union
from uuid import UUID

import httpx
from leaderdata.conf import DSN, OPENAPI_PATH, ensure_openapi_exists
from leaderdata.exceptions import (
    APIServerError,
    BadRequestError,
    MissingRequiredParam,
    OperationNotFoundError,
)

EMPTY = {}
logger = logging.getLogger(__name__)


class GenericModel:
    """Базовый класс для создания моделей"""

    _required_fields: List[str]

    def __repr__(self):
        params = ' '.join(
            [
                f'{key}={str(getattr(self, key))}'
                for key in self._required_fields
                if getattr(self, key) is not None
            ]
        )
        return ''.join(['<', str(type(self)), (f' {params}' if params else ''), '>'])


class Spec:
    """Интерфейс для работы со спецификацией API"""

    _spec: dict = None
    _paths: dict = None
    _models: dict = dict()
    _components: dict = None

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
    def _init_components(cls):
        """Инициализация маппинга компонентов"""
        cls._components = dict()
        for key, schema in cls._spec['components']['schemas'].items():
            schema['_original_title'] = key
            cls._components[f'#/components/schemas/{key}'] = schema

    @classmethod
    def _init_model(cls, schema: dict, component_id: str) -> Type[GenericModel]:
        """Генерация модели для компонента"""
        required = schema.get('required', [])
        attrs = {key: None for key in required}
        attrs['_required_fields'] = required
        model = type(schema['_original_title'], (GenericModel,), attrs,)
        cls._models[component_id] = model
        return model

    @classmethod
    def get_component(
        cls, component_id: str
    ) -> Optional[Tuple[dict, Type[GenericModel]]]:
        """Чтение спецификации компонента"""
        if cls._components is None:
            cls._init_components()

        component = cls._components[component_id]
        if component_id not in cls._models:
            cls._init_model(component, component_id)

        return (component, cls._models[component_id])

    @classmethod
    def get_operation(cls, operation_id: str) -> Tuple[str, str, dict]:
        """Чтение HTTP метода и спецификации операции"""
        if cls._paths is None:
            cls._init_paths()

        if operation_id not in cls._paths:
            raise OperationNotFoundError(operation_id)

        return cls._paths[operation_id]


def _post_process_json(
    data: Any, schema: dict, model: Optional[Type[GenericModel]] = None
) -> Any:
    """Рекурсивная пост-обработка данных полученных из JSON"""
    if data is None:
        return

    if 'anyOf' in schema:
        for fmt in schema.get('anyOf', []):
            try:
                return _post_process_json(data, fmt)
            except (TypeError, ValueError):
                pass
        raise ValueError(f'Not anyOf {schema["anyOf"]} return value')

    if 'allOf' in schema:
        for fmt in schema.get('allOf', []):
            data = _post_process_json(data, fmt)

    if 'type' in schema:
        if schema['type'] == 'array':
            for idx, item in enumerate(data):
                data[idx] = _post_process_json(item, schema['items'])

        elif schema['type'] == 'string':
            if 'format' in schema:
                if schema['format'] in ('uuid', 'uuid4'):
                    return UUID(data)
                elif schema['format'] == 'date-time':
                    return datetime.fromisoformat(data)

        elif schema['type'] == 'object':
            if model:
                instance = model()

            for key, value in data.items():
                if model:
                    setattr(
                        instance,
                        key,
                        _post_process_json(value, schema['properties'][key]),
                    )
                else:
                    data[key] = _post_process_json(value, schema['properties'][key])

            if model:
                return instance

    if '$ref' in schema:
        return _post_process_json(data, *Spec.get_component(schema['$ref']))
    return data


def _post_process_response(method: str, spec: dict, response: httpx.Response) -> Any:
    """
    Пост-обработка ответа API с конвертацией данных в типы Python отсутствующие в JSON
    """
    schema = spec.get('responses', EMPTY).get(str(response.status_code))
    if schema and 'content' in schema:
        content_type = response.headers.get('content-type')
        schema = schema.get('content', EMPTY).get(content_type, EMPTY).get('schema')
        if schema:
            return _post_process_json(response.json(), schema)
    return response.json()


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
        raise AttributeError(
            f'{self.__class__.__name__} instance has no attribute \'{name}\''
        )

    def _request(
        self,
        operation_id: str,
        path: str,
        method: str,
        spec: dict,
        body: Any = None,
        *,
        _is_auth: bool = False,
        _try_auth: bool = True,
        _timeout: Optional[Union[httpx.Timeout, int]] = None,
        **kwargs,
    ):
        """Запрос в API LeaderData"""
        margs = {}

        if body is not None:
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

        if _timeout is not None:
            margs['timeout'] = _timeout

        response: httpx.Response = getattr(httpx, method)(f'{DSN}{path}', **margs)

        if 400 <= response.status_code < 500:
            if response.status_code == 403 and _try_auth:
                # Попытка авторизации
                logger.debug('Not authenticated error, try auth..')
                try:
                    self.auth__application_authentication(
                        _is_auth=True,
                        _try_auth=False,
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
                        _try_auth=False,
                        **kwargs,
                    )
            raise BadRequestError(response=response)

        elif response.status_code >= 500:
            raise APIServerError(response=response)

        if _is_auth:
            self.token = response.json().get('access_token')

        return _post_process_response(method=method, spec=spec, response=response)
