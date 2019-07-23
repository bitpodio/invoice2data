import requests
import logging as logger
import json
import os
from requests_aws4auth import AWS4Auth

attachmentsUrl = os.environ['attachmentsUrl']
if not attachmentsUrl.endswith('/'):
    attachmentsUrl = attachmentsUrl + '/'
accessKeyId = os.environ['accessKeyId']
secretAccessKey = os.environ['secretAccessKey']
auth = AWS4Auth(accessKeyId, secretAccessKey, 'eu-west-1', 's3')

def uploadFile(filePath):
    '''Uploads the file to the attachment model and returns the attachment id'''    
    global attachmentsUrl
    global auth
    files = {'file': open(filePath, 'rb')}
    response = requests.post(attachmentsUrl, files=files, auth=auth)
    contentJson = response.json()
    logger.debug(f'fn uploadFile: {contentJson}')
    return contentJson['id']

def downloadFile( attachmentId, download_path, fileExt ):
    '''download the file from the attachments model for given id.'''
    global attachmentsUrl
    global auth
    # add / in the end of download path
    if not download_path.endswith('/'):
        download_path = download_path + '/'
    # add . in the begining of file extention
    if not fileExt.startswith('.'):
        fileExt = '.' + fileExt
    # create folder if does not exits
    if not os.path.exists(download_path):
        os.makedirs(download_path) 
    # complete local file name       
    local_filename = download_path + attachmentId + fileExt
    # url of the attachment to be downloaded
    downloadAttchmentUrl = attachmentsUrl+ 'download/' +attachmentId
    # download and save the file
    with requests.get(downloadAttchmentUrl, stream=True, auth=auth) as r:
        print(local_filename)
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush()
    return local_filename

def writeToModel(api, data):
    '''Insert data into model.'''
    global auth
