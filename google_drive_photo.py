import os

import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from auth_file import token


def create_folder(service, name, parent_folder_id):
    # Проверка существования папки
    response = service.files().list(
        q=f"name='{name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
        spaces='drive',
        fields='files(id, name)').execute()

    # Если папка существует, возвращаем её ID
    if response.get('files'):
        return response.get('files')[0].get('id')
    else:
        # Если папка не существует, создаем новую
        file_metadata = {
            'name': str(name),
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        file = service.files().create(body=file_metadata, fields='id').execute()
        return file['id']


def upload_photo(file_info, apartment_number):
    credentials = Credentials.from_service_account_file('credentials.json')
    drive_service = build('drive', 'v3', credentials=credentials)
    folder_id = create_folder(drive_service, apartment_number, '1WMbP-CMpcsr8znKxMQzDz74UW95V0A4I')

    # Upload a file
    file = requests.get(f'https://api.telegram.org/file/bot{token}/{file_info.file_path}')

    dir_name = "photos/"
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    # Save file locally
    with open(file_info.file_path, 'wb') as f:
        f.write(file.content)

    # Determine the file's path and name
    file_name = file_info.file_path.split('/')[-1]
    file_path = file_info.file_path

    # upload file to Google Drive
    media = MediaFileUpload(file_path, mimetype='image/jpeg')
    request = drive_service.files().create(media_body=media,
                                           body={'name': file_name, 'parents': [folder_id]})
    request.execute()
    os.remove(file_path)