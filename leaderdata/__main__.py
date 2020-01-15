"""
LeaderData SDK CLI
"""
import argparse
import json
import sys

import httpx
from leaderdata.conf import DSN, OPENAPI_PATH, SPEC_PATH


def update(args: argparse.ArgumentParser):
    """Command `update`"""
    sys.stdout.write(f'Updating openapi.json from {DSN}{SPEC_PATH}\n')
    response = httpx.get(f'{DSN}{SPEC_PATH}')
    if response.status_code != 200:
        sys.stderr.write(
            'Cannot update openapi.json, server response is not OK, try again later\n'
        )
        exit(1)

    with open(OPENAPI_PATH, 'wt') as fh:
        fh.write(response.text)

    data = json.loads(response.text)
    sys.stdout.write(f'openapi.json updated to {data["info"]["version"]}\n')


def main():
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser(
        usage='python -m leaderdata COMMAND', description='LeaderData SDK CLI'
    )
    sub_parsers = parser.add_subparsers(dest='command', required=True)
    sub_parsers.add_parser('update')
    args = parser.parse_args()

    if args.command == 'update':
        update(args)


main()
