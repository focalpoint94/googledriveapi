import os
import sys
import argparse
import asyncio
import json
from collections import defaultdict

import aiohttp
from aiohttp import web
import aiofiles

from googleapiclient.discovery import build

from httplib2 import Http
from oauth2client import file, client, tools
from tqdm import tqdm


DEFAULT_CONCUR_REQ = 30
MAX_CONCUR_REQ = 50


class UploadError(Exception):
    def __init__(self, file_path, folder_id):
        self.file_path = file_path
        self.folder_id = folder_id


def create_drive():
    '''
    * authorize access to user's google drive
    * access information is stored as 'storage.json'
    '''
    SCOPES = 'https://www.googleapis.com/auth/drive.file'
    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        print("Access Grant Needed")
        flow = client.flow_from_clientsecrets('client_secret_drive.json', SCOPES)
        creds = tools.run_flow(flow, store)
    DRIVE = build('drive', 'v3', http=creds.authorize(Http()))
    return DRIVE


def get_token():
    '''
    * returns access token
    '''
    with open('storage.json', 'r') as f:
        creds = json.load(f)
        token = creds["access_token"]
    return token


async def post_file(session, file_path, folder_id):
    '''
    * posts a single file to the designated folder
    * args:
    - session: aiohttp session
    - file_path : absolute path of a file (e.g.) C:\Git\GoogleDriveAPI\test2.jpg
    - folder_id: folder id of the designated folder in google drive (e.g.) '1Q6gaU4kHaLRN5psS4S_2Yx_*******'
    '''
    global token
    file_name = file_path.split(os.path.sep)[-1]
    url = "https://www.googleapis.com/upload/drive/v3/files"
    file_metadata = {"name": file_name,
                     "parents": [folder_id],
                     }
    data = aiohttp.FormData()
    data.add_field(
        "metadata",
        json.dumps(file_metadata),
        content_type="application/json; charset=UTF-8",
    )
    async with aiofiles.open(file_path, mode='rb') as f:
        chuck = await f.read()
    data.add_field("file", chuck)
    headers = {"Authorization": "Bearer {}".format(token)}
    params = {"uploadType": "multipart"}
    async with session.post(url, data=data, params=params, headers=headers) as resp:
        if resp.status == 200:
            return
        else:
            raise aiohttp.web.HTTPException(headers=resp.headers, reason=resp.reason, text=resp.text)


async def upload_file(session, semaphore, file_path, folder_id):
    '''
    * uploads a file to the designated folder in google drive
    * args:
    - session: aiohttp session
    - semaphore: aiohttp Semaphore object
    - file_path : absolute path of a file (e.g.) C:\Git\GoogleDriveAPI\test2.jpg
    - folder_id: folder id of the designated folder in google drive (e.g.) '1Q6gaU4kHaLRN5psS4S_2Yx_*******'
    '''
    async with semaphore:
        try:
            await post_file(session, file_path, folder_id)
        except Exception as exc:
            raise UploadError(file_path, folder_id) from exc


async def upload_files(file_paths, folder_name, folder_id, concur_req=DEFAULT_CONCUR_REQ):
    '''
    * uploads files to google drive
    * returns list of tuples (path of file, folder_id) that failed to be uploaded
    * args:
    - file_paths: list of local file names, (e.g.) ['C:\Git\GoogleDriveAPI\hello.txt', ...]
    - folder_name: local folder name, (e.g.) 'train2014'
    - folder_id: target folder's id in google drive, (e.g.) '1FzI5QChbh4Q-nEQGRu8D-********'
    - concur_req: maximum concurrent connections allowed
    '''
    print('Uploading {} files to {}...'.format(len(file_paths), folder_name))
    sys.stdout.flush()
    failed = []
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(concur_req)
        jobs = [upload_file(session, semaphore, file_path, folder_id) for file_path in file_paths]
        jobs = asyncio.as_completed(jobs)
        jobs = tqdm(jobs, total=len(file_paths))
        for job in jobs:
            try:
                await job
            except UploadError as exc:
                print(exc)
                failed.append((exc.file_path, exc.folder_id))
    return failed


def upload_folder(folder_path, folder_id, concur_req=DEFAULT_CONCUR_REQ, retry=True):
    '''
    * uploads folder to google drive
    * stores dictionary (folder_id: [file_path, ...]) that failed to be uploaded as 'failed.json'
    * args:
    - fold_path: target folder's path (e.g.) 'C:\Git\GoogleDriveAPI\test'
    - folder_id: target folder's id in google drive, (e.g.) '1FzI5QChbh4Q-nEQGRu8D-********'
    - concur_req: maximum concurrent connections allowed
    - retry: retries uploading failed uploads if set to True
    '''
    global drive
    loop = asyncio.get_event_loop()
    dic = {folder_path: folder_id}
    failed = defaultdict(list)
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
        folder_name = path.split(os.path.sep)[-1]
        files = [os.path.join(path, file) for file in files]
        fails = loop.run_until_complete(upload_files(files, folder_name, current_folder_id, concur_req))
        for key, val in fails:
            failed[val].append(key)

    with open('failed.json', 'w') as f:
        json.dump(failed, f)

    if retry:
        with open('failed.json', 'r') as f:
            failed = json.load(f)
        if failed:
            print('Retrying to upload failed ones...')
            sys.stdout.flush()
            new_failed = defaultdict(list)
            for key, files in failed.items():
                if files:
                    folder_name = files[0].split(os.path.sep)[-2]
                    fails = loop.run_until_complete(upload_files(files, folder_name, key, concur_req))
                    for new_key, new_val in fails:
                        new_failed[new_val].append(new_key)
            with open('failed.json', 'w') as f:
                json.dump(new_failed, f)

    loop.close()


if __name__ == '__main__':
    '''
    python googledriveapi_async.py C:\Git\PytorchBasic\caption\data_dir 1CwX9S8mJSL_43oJgLdoiNoF55yU7Vj**
    '''
    # parser = argparse.ArgumentParser(
    #     description='Upload folder including all sub-folders to google drive.')
    # parser.add_argument('folder_path',
    #                     help='folder_path: local folder path to upload'
    #                          '(e.g.) C:\Git\PytorchBasic')
    # parser.add_argument('folder_id',
    #                     help='folder_id: target folder\'s id in google drive'
    #                          '(e.g.) 1FzI5QChbh4Q-nEQGRu8D-********')
    # parser.add_argument('concur_req', nargs='?', default=DEFAULT_CONCUR_REQ, type=int,
    #                     help='concur_req: maximum number of concurrent connections'
    #                          '(Default) DEFAULT_CONCUR_REQ')
    # parser.add_argument('enable_retry', nargs='?', default=True, type=bool,
    #                     help='retry uploading failed uploads if set to True'
    #                          '(Default) True')
    # args = parser.parse_args()
    # if not os.path.isdir(args.folder_path):
    #     print('*** Folder path error: invalid path')
    #     parser.print_usage()
    #     sys.exit(1)
    # folder_path = args.folder_path
    # folder_id = args.folder_id
    # concur_req = args.concur_req
    # enable_retry = args.enable_retry

    folder_path = r'C:\Users\chsze\Desktop\Georgia Tech\Second Semester\Deep Learning\Project\DATASET'
    folder_id = '1oHa63uLxPcdBkSVixbv_skMt-nOJ7z**'
    concur_req = DEFAULT_CONCUR_REQ
    enable_retry = True

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    drive = create_drive()
    token = get_token()
    upload_folder(folder_path, folder_id, concur_req, enable_retry)

