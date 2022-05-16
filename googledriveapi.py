from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from tqdm import tqdm
import os, sys
import argparse


def create_drive():
    '''
    creates and returns google driver object

    '''
    SCOPES = 'https://www.googleapis.com/auth/drive.file'
    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        print("make new storage data file ")
        flow = client.flow_from_clientsecrets('client_secret_drive.json', SCOPES)
        tools.run(flow, store)
    DRIVE = build('drive', 'v3', http=creds.authorize(Http()))
    return DRIVE


def upload_files(drive, files, folder_name, folder_id):
    '''
    upload files to a particular folder in google drive

    drive: google drive object
    files: list of local file names, e.g. [('hello.txt'), ('bye.txt'), ]
    folder_name: local folder name, e.g. 'train2014'
    folder_id: target folder's id in google drive, e.g. '1FzI5QChbh4Q-nEQGRu8D-********'

    '''
    print('Uploading {} files to {}...'.format(len(files), folder_name))
    for file in tqdm(files):
        metadata = {'name': file,
                    'parents': [folder_id],
                    'mimeType': None
                    }
        try:
            res = drive.files().create(body=metadata, media_body=file).execute()
        except googleapiclient.errors.UnknownFileType:
            print('Unknown filetype error for {}. Skipping the file.'.format(file))


def upload_folder(drive, folder_path, folder_id):
    '''
    upload folder including all sub folders

    drive: google drive object
    folder_path: local folder path to upload, e.g. r'C:\Git\PytorchBasic\data_dir'
    folder_id: target folder's id in google drive, e.g. '1FzI5QChbh4Q-nEQGRu8D-********'

    '''

    # maps folder_path: folder_id
    dic = {folder_path: folder_id}

    for path, dirs, files in os.walk(folder_path):
        current_folder_id = dic[path]
        for dir in dirs:
            file_metadata = {
                'name': dir,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [current_folder_id],
            }
            file = drive.files().create(body=file_metadata, fields='id').execute()
            dic[os.path.join(path, dir)] = file.get('id')
        folder_name = path.split('\\')[-1]
        files = [os.path.join(path, file) for file in files]
        upload_files(drive, files, folder_name, current_folder_id)


def main(folder_path, folder_id):
    '''
    upload folder including all sub folders

    folder_path: local folder path to upload, e.g. r'C:\Git\PytorchBasic\data_dir'
    folder_id: target folder's id in google drive, e.g. '1FzI5QChbh4Q-nEQGRu8D-********'

    '''
    drive = create_drive()
    upload_folder(drive, folder_path, folder_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Upload folder including all sub-folders to google drive.')
    parser.add_argument('folder_path',
                        help='folder_path: local folder path to upload'
                             'e.g. C:\Git\PytorchBasic')
    parser.add_argument('folder_id',
                        help='folder_id: target folder\'s id in google drive'
                             'e.g. 1FzI5QChbh4Q-nEQGRu8D-********')
    args = parser.parse_args()
    if not os.path.isdir(args.folder_path):
        print('*** Folder path error: invalid path')
        parser.print_usage()
        sys.exit(1)
    folder_path = args.folder_path
    folder_id = args.folder_id
    # folder_path = r'C:\Git\GoogleDriveAPI\test'
    # folder_id = '1wrlqfK2r3qHkgIXLHfKdYFj-b70NgCW7'
    main(folder_path, folder_id)
