# LeaderData API SDK

Python SDK для работы с API LeaderData.


## Установка

```console
pip install leaderdata-sdk
```

После этого необходимо получить файл `openapi.json`:

```console
python -m leaderdata update
```

API периодически меняется и файл `openapi.json` нужно обновлять для актулизации SDK.


## Конфигурация

И импортируемый модуль и интерфейс командной строки для запросов обращаются к API по
адресу `https://data.leader-id.ru`, этот адрес можно изменить переменными окружения
`DSN` и `SPEC_PATH`; где первая задает адрес хоста: проткол, домен, порт; а вторая
путь относительно хоста до `openapi.json`.


## Использование

Методы клиента соответствуют операциям API, и состоят из:

- имя метода – идентификатор операции;
- позиционный аргумент – может быть только один и используется для задания тела запроса;
- именованные аргументы - используются для передачи параметров строки запроса и
подстановки переменных в пути, где они необходимы; клиент SDK сам определит какие
аргументы чем являются.

Опциональность / обязательность аргументов можно определить из документации.

Идентификатор операции можно получить из [документации API LeaderData](https://data.leader-id.ru/api/redoc).
Для этого нужно выбрать необходимую операцию и обратить внимание на адресную строку, к
примеру ссылка документации на операцию по чтению коллекций будет такой:

```
https://data.leader-id.ru/api/redoc#operation/collections__list_collections
```

Где идентификатор операции это: `collections__list_collections`.


### Примеры

Инициализация клиента

```python
from leaderdata.api import Client


client = Client(client_id='APP_ID', client_secret='APP_SECRET')
```

Чтение списка принадлежащих приложению коллекций:

```python
for collection in client.collections__list_collections(is_own=True):
    print(f'collection id: {collection["id"]}, name: {collection["name"]}')
```

Создание новой коллекции:

```python
collection = client.collections__create_collection({
  'access_type': 'private',
  'name': 'Very simple collection',
  'description': 'From SDK README.md'
})

print(f'new collection id: {collection["id"]}')
```

Чтение созданной только что коллекции:

```python
actual_collection_data = client.collections__read_collection(
  collection_id=collection["id"]
)

print(f'collection current name: {actual_collection_data["name"]}')
```
