import json
import datetime
import codecs
import requests
import os
from requests_aws4auth import  AWS4Auth
import logging as logger

def write_to_model(data, api, dataColumn, date_format="%Y-%m-%d"):
    '''Writes the json data to given model. 
    to_json must be called before this function to convert the python datetime to string dates.'''
    accessKeyId = os.environ['accessKeyId']
    secretAccessKey = os.environ['secretAccessKey']
    auth = AWS4Auth(accessKeyId, secretAccessKey, 'eu-west-1', 's3')
    for line in data:
        for k, v in line.items():
            if k.startswith('date') or k.endswith('date'):
                line[k] = v.strftime(date_format)    
    try:
        headers = {'content-type': 'application/json'}
        payload = {dataColumn: data[0]}
        response = requests.post(api, data=json.dumps(payload), headers=headers, auth = auth)
        logger.debug(response.text)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        logger.error(f'Http Error: {errh}')
    except requests.exceptions.ConnectionError as errc:
        logger.error(f'Error Connecting: {errc}')
    except requests.exceptions.Timeout as errt:
        logger.error(f'Timeout Error: {errt}')
    except requests.exceptions.RequestException as err:
        logger.error(f'Oops: Something Else {err}')