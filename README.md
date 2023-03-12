# GoogleDriveAPI

python program that automatically uploads/downloads files & folders to/from your google drive.

## Uploading API

### googledriveapi.py

uploads a folder to your google drive

First enable the google drive api by following steps of:
https://developers.google.com/drive/api/quickstart/python


command line example

```
python googledriveapi.py folder_name folder_id

python googledriveapi.py C:\Git\GoogleDriveAPI\test 1iBN6SRF5Vu3Q5oiqTFekT9cnsb8eQ_**
```


### googledriveapi_async.py

uploads a folder to your google drive with asyncio

with asyncio, uploading is much faster

command line example

```
python googledriveapi.py folder_name folder_id concur_Req enable_retry

python googledriveapi.py C:\Git\GoogleDriveAPI\test 1iBN6SRF5Vu3Q5oiqTFekT9cnsb8eQ_**
```

#### Arguments

1. folder_name: local folder's name
2. folder_id: folder id of the target folder in your google drive
![image](https://user-images.githubusercontent.com/55021961/174004565-f2a3df88-0e73-4da5-916d-b09bc94270b0.png)
3. concur_req: maximumn allowed number of concurrent connections, default = 100
4. enable_retry: if set true, retry uploading once failed files, default = True



![googledriveapi_async](https://user-images.githubusercontent.com/55021961/174006032-0f5c234c-6198-46e9-9840-ea1c2011baab.gif)




