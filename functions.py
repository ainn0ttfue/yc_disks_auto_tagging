import requests

from vars import GET_IAM_TOKEN_URL, GET_INSTANCE_LIST_URL, GET_DISKS_LIST_URL, GET_INSTANCE_BY_ID_URL, UPDATE_DISK_URL


def get_iam_token(oauth_token: str) -> str:
    r = requests.post(GET_IAM_TOKEN_URL, json={"yandexPassportOauthToken": oauth_token})

    if r.status_code == 200:
        response_data = r.json()
        if "iamToken" in response_data:
            return response_data['iamToken']
        else:
            raise Exception('IAM токен отсутствует в ответе')
    else:
        raise Exception(f'Ошибка получения iamToken: {r.status_code, r.text}')


def get_instance_list(input_iam_token: str, yc_cloud_id: str) -> list:
    r = requests.get(GET_INSTANCE_LIST_URL,
                     headers={"Authorization": f"Bearer {input_iam_token}"},
                     params={"folderId": yc_cloud_id})

    if r.status_code == 200:
        response_data = r.json()
        # print(json.dumps(response_data))
        if "instances" in response_data:
            return response_data['instances']
        else:
            raise Exception('Нет instances в ответе на запрос списка ВМ')
    else:
        raise Exception(f'Ошибка получения списка ВМ: {r.status_code, r.text}')


def get_disk_list(input_iam_token: str, yc_cloud_id: str) -> list:
    r = requests.get(GET_DISKS_LIST_URL,
                     headers={"Authorization": f"Bearer {input_iam_token}"},
                     params={"folderId": yc_cloud_id})

    if r.status_code == 200:
        response_data = r.json()
        # print(json.dumps(response_data))
        if "disks" in response_data:
            return response_data['disks']
        else:
            raise Exception('Нет disks в ответе на запрос списка дисков')
    else:
        raise Exception(f'Ошибка получения списка дисков: {r.status_code, r.text}')


def get_instance_by_id(input_iam_token: str, id: str) -> dict:
    r = requests.get(f"{GET_INSTANCE_BY_ID_URL}{id}",
                     headers={"Authorization": f"Bearer {input_iam_token}"},
                     params={"view": "BASIC"})

    if r.status_code == 200:
        response_data = r.json()
        # print(response_data)
        try:
            labels = response_data["labels"]
        except KeyError:
            labels = {}

        return {"id": response_data["id"], "labels": labels}
    else:
        raise Exception(f'Ошибка получения информации о ВМ: {r.status_code, r.text}')


def parse_disk_dict(disks: list) -> list:
    """
    Проверяет, что диск привязан к ВМ (а также, что лишь к одной ВМ), и возвращает словарь:
    Возвращяет словарь correct=True с id диска и ВМ, иначе словарь с  correct=False с описанием ошибки след. вида:
    [{'correct': True, 'disk_id': '<DISK_ID>', 'instance_id': '<INSTANSE_ID>', 'old_labels': {'key1': 'val1', 'key2': 'val'}}, {...}]
    """
    result_arr = []
    for disk in disks:
        disk_id = disk["id"]
        if "instanceIds" in disk:
            if len(disk["instanceIds"]) >= 2:
                result_arr.append({"correct": False, "disk_id": disk_id, "comment": "Диск привязан более чем к 1 ВМ"})
            else:
                disk_labels = {}
                if "labels" in disk:
                    disk_labels = disk["labels"]
                result_arr.append({"correct": True, "disk_id": disk_id, "instance_id": disk["instanceIds"][0],
                                   "old_labels": disk_labels})
        else:
            result_arr.append({"correct": False, "disk_id": disk_id, "comment": "Диск НЕ привязан к ВМ"})
    return result_arr


def update_disk_labels(input_iam_token: str, disk_id: str, new_labels: dict) -> dict:
    r = requests.patch(f"{UPDATE_DISK_URL}{disk_id}",
                       headers={"Authorization": f"Bearer {input_iam_token}"},
                       json={"updateMask": "labels", "labels": new_labels})

    if r.status_code == 200:
        response_data = r.json()
        # print(json.dumps(response_data))
        try:
            labels = response_data["response"]["labels"]
        except KeyError:
            labels = {}

        return {"done": response_data["done"], "labels": labels}
    else:
        raise Exception(f'Ошибка обновления меток диска: {r.status_code, r.text}')
