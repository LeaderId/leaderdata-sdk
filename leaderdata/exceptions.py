import httpx


class ResponseError(Exception):
    """API вернула ошибку"""

    resp: httpx.Response

    def __init__(self, response: httpx.Response):
        super().__init__()
        self.resp = response

    def __repr__(self) -> str:
        return (
            '<ResponseError'
            f' status_code={self.resp.status_code}'
            f' text={self.resp.text}'
            f' url={self.resp.url}'
            '>'
        )

    def __str__(self) -> str:
        return repr(self)


class BadRequestError(ResponseError):
    """API вернула ошибку 4XX"""

    def __repr__(self) -> str:
        return (
            '<BadRequestError'
            f' status_code={self.resp.status_code}'
            f' json={self.resp.json()}'
            f' url={self.resp.url}'
            '>'
        )


class APIServerError(ResponseError):
    """API вернула ошибку 5XX"""


class MissingRequiredParam(Exception):
    """Не указан обязательный для операции параметр"""

    operation_id: str
    name: str

    def __init__(self, operation_id: str, name: str):
        super().__init__()
        self.operation_id = operation_id
        self.name = name


class OperationNotFoundError(Exception):
    """Операция не найдена в спецификации API"""

    operation_id: str

    def __init__(self, operation_id: str):
        super().__init__()
        self.operation_id = operation_id
