import requests
import logging as logger
import json
import os
from requests_aws4auth import AWS4Auth
import sys
import yaml

try:
    attachmentsAPI = os.environ['attachmentsApi']
    templatesAPI = os.environ['templatesApi']
    if not attachmentsAPI.endswith('/'):
        attachmentsAPI = attachmentsAPI + '/'
    accessKeyId = os.environ['accessKeyId']
    secretAccessKey = os.environ['secretAccessKey']
    templateFieldName = os.environ['templateFieldName']
    auth = AWS4Auth(accessKeyId, secretAccessKey, 'eu-west-1', 's3')
except KeyError as e:
    logger.error(f'Please set env variable {e.args[0]}')
    sys.exit(1)

def uploadFile(filePath):
    '''Uploads the file to the attachment model and returns the attachment id'''    
    global attachmentsAPI
    global auth
    files = {'file': open(filePath, 'rb')}
    response = requests.post(attachmentsAPI, files=files, auth=auth)
    contentJson = response.json()
    logger.debug(f'fn uploadFile: {contentJson}')
    return contentJson['id']

def downloadFile( attachmentId, download_path, fileExt ):
    '''download the file from the attachments model for given id.'''
    global attachmentsAPI
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
    downloadAttchmentUrl = attachmentsAPI+ 'download/' +attachmentId
    # download and save the file
    try:
        with requests.get(downloadAttchmentUrl, stream=True, auth=auth) as r:
            logger.debug(local_filename)
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
                        # f.flush()
        return local_filename
    except requests.exceptions.HTTPError:
        raise requests.exceptions.HTTPError(f'Error while downloading attachment id - {attachmentId}.')

def getTemplateFile(tempalteId, template_folder):
    global auth
    global templatesAPI
    global templateFieldName
     # add / in the end of download path
    if not template_folder.endswith('/'):
        template_folder = template_folder + '/'
    # create folder if does not exits
    if not os.path.exists(template_folder):
        os.makedirs(template_folder) 
    # complete local file name       
    local_filename = template_folder + tempalteId + '.yml'
    logger.debug(local_filename)
    # API to get template
    getTemplateAPI = templatesAPI + tempalteId
    # download, convert to yml and save in file
    try:
        response = requests.get(getTemplateAPI, auth=auth)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise requests.exceptions.HTTPError(f'Error while downloading template id - {tempalteId}.')
    responseJson = response.json()
    with open(local_filename, 'w') as f:
        f.write(responseJson[templateFieldName])
    return local_filename