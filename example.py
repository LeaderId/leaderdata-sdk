import logging
from pprint import pprint

from leaderdata.api import Client

CLIENT_ID = '340e65be56c933b8c757660d62210992'
CLIENT_SECRET = 'bdd2df1814050b40f7d8ba3943348aa5'


def main():
    logging.basicConfig()
    logger = logging.getLogger('leaderdata')
    logger.setLevel(logging.DEBUG)

    # Инициализация клиента
    client = Client(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

    # Список его личных коллекций
    collection = None
    for collection in client.collections__list_collections(is_own=True):
        pprint(collection)

    if collection:
        # При наличии хотя бы одной чтение её отдельно
        read_collection = client.collections__read_collection(
            collection_id=collection.id
        )
        pprint(read_collection)
        breakpoint()


main()
