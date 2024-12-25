from functions import get_iam_token, parse_disk_dict, get_disk_list, get_instance_by_id, update_disk_labels
from vars import TARGET_KEYS_LIST

import os
from dotenv import load_dotenv

"""
План:

1. Получим список дисков определенного каталога (https://yandex.cloud/ru/docs/compute/api-ref/Disk/list) в виде JSON
2. Для дисков, у которых заданна принадлежность к определнной ВМ в поле "instanceIds" лежит ID этой ВМ
3. С помощью API получаем метки этой ВМ (https://yandex.cloud/ru/docs/compute/api-ref/Instance/get), нас интересуют метки департамента, продукта и расположения
4. С пощощью того же API добавляем эти метки диску из шага 2 (https://yandex.cloud/ru/docs/compute/api-ref/Disk/update)

"""

if __name__ == "__main__":
    load_dotenv()
    # получаем iam токен для работы с REST API
    iam_token = get_iam_token(os.getenv("YANDEX_OAUTH_TOKEN"))

    # ID директории yandex cloud
    yc_cloud_id = os.getenv("YANDEX_FOLDER_ID")

    # получаем список дисков и их метки, а также принадлежность к ВМ
    parsed_disks = parse_disk_dict(get_disk_list(iam_token, yc_cloud_id))

    # Создаем словарь, где ключ=id ВМ, а содержимое это метки этой ВМ
    # {'<VM_ID>': {'label_key_1': 'val', 'label_key_2': 'val'}, {..}, {..}}
    instances_labels_dict = {}
    for disk in parsed_disks:
        if not disk["correct"]:
            continue

        instance = get_instance_by_id(iam_token, disk["instance_id"])
        instances_labels_dict.update({instance["id"]: instance["labels"]})

    # Формируем результирующий словрь, где ключ это ID ВМ, а значение это метки которые ему нужно поставить (старые + новые)
    # При этом старые метки ДИСКА не перезаписываются метками ВМ в случае одинаковых ключей
    disk_labels_dict = {}
    for disk in parsed_disks:
        if not disk["correct"]:
            continue

        # фильтруем новые метки, оставляя только нужные: см. константу TARGET_KEYS_LIST
        filtered_vm_labels = {}
        for key in TARGET_KEYS_LIST:
            if instances_labels_dict[disk["instance_id"]].get(key):
                filtered_vm_labels.update({key: instances_labels_dict[disk["instance_id"]].get(key)})

        # новые метки = метки ВМ (только 3 нужных) + старые метки диска
        new_labels = filtered_vm_labels | disk["old_labels"]

        changed_labels = list(set(new_labels) - set(disk["old_labels"]))
        disk_labels_dict.update({disk["disk_id"]: {
            "new_labels": new_labels,
            "changed_labels_keys": changed_labels}
        })

    for disk, val in disk_labels_dict.items():
        if len(val["changed_labels_keys"]):
            print(
                f"Диску {disk} будут назначены след. метки ({len(val["changed_labels_keys"])} новых: {", ".join(val["changed_labels_keys"])}): {val["new_labels"]}.")
        else:
            print(
                f"Диску {disk} будут назначены след. метки (0 новых): {val["new_labels"]}.")

    approve_update = str(input("> Вы подтверждаете данные изменения? (y/n): "))

    if approve_update != "y":
        print("Завершение программы")
        exit()

    print("Вносим изменения")

    for disk_key, val in disk_labels_dict.items():
        status = update_disk_labels(iam_token, disk_key, val["new_labels"])
        if status["done"]:
            print(f"Для диска {disk_key} заданны следующие метки: {status["labels"]}")
        else:
            print(f"Не удалось обносить диск {disk_key}")
