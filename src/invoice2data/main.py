#!/usr/bin/env python
# -*- coding: utf-8 -*-


import shutil
import os
import logging
import json
import sys
logger = logging.getLogger(__name__)

from .input import pdftotext
from .input import pdfminer_wrapper
from .input import tesseract
from .input import tesseract4
from .input import gvision

from invoice2data.extract.loader import read_templates

from .output import to_csv
from .output import to_json
from .output import to_xml
from .final_data import FinalData
from . import file_transfer
from .prepare_input import getSettings

input_mapping = {
    'pdftotext': pdftotext,
    'tesseract': tesseract,
    'tesseract4': tesseract4,
    'pdfminer': pdfminer_wrapper,
    'gvision': gvision,
}
finalData = FinalData()

output_mapping = {'csv': to_csv, 'json': to_json, 'xml': to_xml, 'none': None}


def parse_data(templates, extracted_str):
    try:    
        logger.debug('START pdftotext result ===========================')
        logger.debug(extracted_str)
        logger.debug('END pdftotext result =============================')
        finalData.runningStatus = 'EXTRACTING_DATA'
        if templates is None:
            templates = read_templates()
            
        logger.debug('Testing {} template files'.format(len(templates)))
        selectedTemplate = ''
        for t in templates:
            optimized_str = t.prepare_input(extracted_str)

            if t.matches_input(optimized_str):
                selectedTemplate = t['template_name'].split('.')[0]
                extractionDetails = t.extract(optimized_str)
                return finalData.updateFinalDataFromPdfData(extractionDetails, optimized_str, selectedTemplate)      
    except Exception as e:
        finalData.updateStatus(e, 402, 'Error while parsing PDF data. Error '+ str(e), False)
        return False
    if (finalData.selectedTemplate == ''):
        logger.error('No matching template found for the PDF.')
        finalData.updateStatus(dbStatusCode=404, dbStatus='No matching template found for the PDF based on the "keywords".', commitToDB=False)    
        return False
    raise Exception('Some unknown error has occured while processing the pdf.') 


def extract_data(invoicefile, templates=None, input_module=pdftotext):
    # TRY 1
    # extract data with given input_module
    doNextPass = True
    finalData.passNumber = 1
    while doNextPass:
        try:
            finalData.runningStatus = 'READING_PDF'
            extracted_str = input_module.to_text(invoicefile).decode('utf-8')
            finalData.rawData = extracted_str # This value will be overwritten but assiging raw data here so we have something to investigate in case anything fails.
        except Exception as e:
            finalData.updateStatus(e, 401, 'Error while extracting the data from PDF.', False)
        isParsed = parse_data(templates, extracted_str)
        (input_module, doNextPass) = setupNextPass(isParsed)

def setupNextPass(isParsed):
    '''
    Checks if the last pass was successful, if not then returns input_module for the next pass and doNextPass as True.
    '''
    if (isParsed and finalData.statusCode == 200):
        return None, False
    finalData.passNumber += 1
    if finalData.passNumber == 2:
        logger.debug('Retrying to extract the data using tesseract4.')
        return input_mapping['tesseract4'], True
    return None, False

def downloadFilesAndUpdatingSettings(settings):
    logger.debug('******* Download Templates ********')
    for templateId in settings['templateIds']:
        file_transfer.getTemplateFile(templateId.strip(), settings['template_folder'])  

    logger.debug('******* Download PDFs ********')
    for pdfId in settings['pdfIds']: 
        downloaded_file = file_transfer.downloadFile(pdfId.strip(), settings['pdf_folder'], '.pdf')
        try:
            settings['input_files'].append(open(downloaded_file, 'r', encoding='utf-8'))
        except OSError:
            logger.fatal('Unable to open downloaded file', exc_info=True)


def main(args=None):
    """Take folder or single file and analyze each."""    
    try:
        finalData = FinalData.getInstance()
        finalData.runningStatus = 'PREPARING_INPUTS'

        settings = getSettings()

        # Set log level based on args
        if settings['logLevelDebug']:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        if settings['isK8sJob']:
            finalData.runningStatus = 'DOWNLOADING_FILES'
            downloadFilesAndUpdatingSettings(settings)

        # *** Template loading start *** #
        finalData.runningStatus = 'LOADING_TEMPLATES'
        settings['templates'] += read_templates(settings['template_folder'])

        if settings['include_built_in_templates']:
            settings['templates'] += read_templates()
        # *** Template loading End *** #

        # starting process PDFs
        finalData.runningStatus = 'STARTING_PDF_PROCESSING'
        outputs = []
        for f in settings['input_files']:
            finalData.pdfId = os.path.basename(f.name).split('.')[0]
            extract_data(f.name, templates=settings['templates'], input_module=input_mapping[settings['inputReader']])
            logger.info(finalData)
            outputs.append(finalData.getFinalData())
            if settings['isK8sJob']:
                finalData.commitToDB()
            f.close()
            # reset the finalData    
            finalData.reset()

        if not settings['isK8sJob']:
            # for command line the output is written after processing all the files unlike in K8s job where 
            # the output of each pdf processing is written right after the processing completes or is errored out.
            output_module = output_mapping[settings['output_format']]
            output_module.write_to_file(outputs, settings['outputFileName'])

        finalData.runningStatus = 'PDF_PROCESSING_COMPLETED'
    except Exception as e:
        finalData.updateStatus(exception=e)
        pass

if __name__ == '__main__':
    main()
