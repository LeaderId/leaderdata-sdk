import os
import sys

DIR = os.path.dirname(__file__)
DSN = os.environ.get('DSN', 'https://data.leader-id.ru')
SPEC_PATH = os.environ.get('SPEC_PATH', '/api/openapi.json')
OPENAPI_PATH = os.path.join(DIR, 'openapi.json')


def ensure_openapi_exists():
    """Проверка существования файла openapi.json"""
    if not os.path.exists(OPENAPI_PATH):
        sys.stderr.write(
            'File openapi.json does not exists.\n\n'
            'Run command:\npython -m leaderdata update'
        )
