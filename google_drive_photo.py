import os

import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from auth_file import token


def create_folder(service, name, parent_folder_id):
    response = service.files().list(
        q=f"name='{name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
        spaces='drive',
        fields='files(id, name)').execute()

    if response.get('files'):
        return response.get('files')[0].get('id')
    else:

        file_metadata = {
            'name': str(name),
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        file = service.files().create(body=file_metadata, fields='id').execute()
        return file['id']


def upload_photo_pdf(file_info, apartment_number):
    credentials = Credentials.from_service_account_file('credentials.json')
    drive_service = build('drive', 'v3', credentials=credentials)
    folder_id = create_folder(drive_service, apartment_number, '1WMbP-CMpcsr8znKxMQzDz74UW95V0A4I')

    file = requests.get(f'https://api.telegram.org/file/bot{token}/{file_info.file_path}')

    dir_name = "files/"
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    local_file_path = os.path.join(dir_name, file_info.file_path.split('/')[-1])
    with open(local_file_path, 'wb') as f:
        f.write(file.content)

    mime_type = 'application/pdf' if local_file_path.endswith('.pdf') else 'image/jpeg'

    media = MediaFileUpload(local_file_path, mimetype=mime_type)
    request = drive_service.files().create(media_body=media, body={'name': local_file_path.split('/')[-1], 'parents': [folder_id]})
    request.execute()

    os.remove(local_file_path)
