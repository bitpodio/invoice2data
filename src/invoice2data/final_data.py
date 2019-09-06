import logging
logger = logging.getLogger('__main__')
from .prepare_input import getSettings
from .output import to_model
import sys

class FinalData:
    __instance = None

    @staticmethod 
    def getInstance():
       """ Static access method. """
       if FinalData.__instance == None:
           FinalData()
       return FinalData.__instance

    def __init__(self):
       """ Virtually private constructor. """
       if FinalData.__instance != None:
           raise Exception("This class is a singlton class, please call the getInstance method to get the object!")
       else:
           self._runningStatus = 'NOT_YET_STARTED'
           self._statusCode = None
           self._status = None
           self._extractedJson = {}
           self._passNumber = 0
           self._pdfId = ''
           self._rawData = ''
           self._selectedTemplate = ''
           self._isCommited = False
           self.__settings = getSettings()
           FinalData.__instance = self

    def reset(self):
        self._runningStatus = 'NOT_YET_STARTED'
        self._statusCode = None
        self._status = None
        self._extractedJson = {}
        self._passNumber = 0
        self._pdfId = ''
        self._rawData = ''
        self._selectedTemplate = ''
        self._isCommited = False

    def __repr__(self):
        return {
            "runningStatus": self._runningStatus,
            "passNumber": self._passNumber,
            "statusCode": self._statusCode,
            "status": self._status,
            "extractedJson": self._extractedJson,
            "pdfId": self._pdfId,
            "rawData": self._rawData,
            "selectedTemplate": self._selectedTemplate
        }

    def __str__(self):
        return self.__repr__().__str__()
        
    @property
    def runningStatus(self):
        return self._runningStatus
    @runningStatus.setter
    def runningStatus(self, value):
        assert (value in ['PREPARING_INPUTS', 'DOWNLOADING_FILES', 'LOADING_TEMPLATES', 'STARTING_PDF_PROCESSING', 'READING_PDF', 'EXTRACTING_DATA', 'RETRYING', 'COMMITING_FINAL_DATA', 'PDF_PROCESSING_COMPLETED']), 'Unknown running status!'
        self._runningStatus = value

    @property
    def passNumber(self):
        return self._passNumber
    @passNumber.setter
    def passNumber(self, value):
        self._passNumber = value

    @property
    def statusCode(self):
        return self._statusCode
    @statusCode.setter
    def statusCode(self, value):
        if  self._statusCode == None or (self._statusCode > value and self.passNumber > 1):
            self._statusCode = value
        else:
            raise Exception(f'Incorrect status update from {self._statusCode} to {value} in the pass - {self.passNumber}.!')

    @property    
    def status(self):
        return self._status
    @status.setter
    def status(self, value):
        self._status = value

    @property
    def extractedJson(self):
        return self._extractedJson
    @extractedJson.setter
    def extractedJson(self, value):
        self._extractedJson = value

    @property
    def pdfId(self):
        return self._pdfId
    @pdfId.setter
    def pdfId(self, value):
        self._pdfId = value
    
    @property
    def rawData(self):
        return self._rawData
    @rawData.setter
    def rawData(self, value):
        if self._passNumber > 1:
            logger.debug('Skipping direct raw data update to prevent unwanted overwrite. \
             \nRaw data will be updated by function updateFinalDataFromPdfData if this pass gives batter results then previous pass.')
        else:
            self._rawData = value

    @property
    def selectedTemplate(self):
        return self._selectedTemplate
    @selectedTemplate.setter
    def selectedTemplate(self, value):
        self._selectedTemplate = value

    def getFinalData(self):
        return {
            "statusCode": self._statusCode,
            "status": self._status,
            "extractedJson": self._extractedJson,
            "pdfId": self._pdfId,
            "rawData": self._rawData,
            "selectedTemplate": self._selectedTemplate
        }

    def updateStatus(self, exception=None, dbStatusCode=400, dbStatus=None, commitToDB=True):
        '''
        update finalData status and commit finalData if required.
        Parameters
        ----------------------
        exception    : exception that occured
        dbStatusCode : status code to be saved in DB (default: 400)
        dbStatus     : description of the status code or the actual error that occured.
        commitToDB   : If True processing will exit after writing finalData to DB otherwise only the finalData is updated but not commited to DB. This will be ignored when running the tool vai command line.
        '''
        assert exception or (dbStatusCode != 400 and dbStatus),'Please call function with correct params.'
        logger.debug('Updating status in finalData.') 
        self._statusCode = dbStatusCode
        dbStatus = dbStatus or f'Exception occurred while processing the request {exception.args[0]}'
        self._status = dbStatus if not self._status else self._status + ', "' + dbStatus + '"'
        if self.__settings['isK8sJob'] and commitToDB:
            self.commitToDB()
        if exception:
            logger.error(exception, exc_info= logger.getEffectiveLevel() <= logging.DEBUG)
        if commitToDB:
            sys.exit(1)


    def updateFinalDataFromPdfData(self, extractionDetails, optimized_str, selectedTemplate):
        if (self._passNumber > 1) and self._statusCode and self._statusCode <= extractionDetails['dbStatusCode'] :
            if (self._statusCode == extractionDetails['dbStatusCode'] 
                and self._statusCode == 320 # Processed with one or more missing lines.
                and 'lines' in extractionDetails['output'].keys() 
                and len(self._extractedJson['lines']) < len(extractionDetails['output']['lines']) # check which pass has more lines.
                ):
                logger.debug('This pass extracted more lines then previous pass so overwriting results of previous pass.')
                self._status = ''
            else:
                logger.debug('Skipping the results of this pass. Because the last pass has given better results.')
                logger.debug(extractionDetails['warnings'])
                return True

        else:
            logger.debug('Clearing the status from previous pass.')
            self._status = ''

        self._rawData = optimized_str
        self._selectedTemplate = selectedTemplate
        if len(extractionDetails['warnings']) > 1:
            # prepare comma seperated list of warnings
            processingWarnings = '", "'.join(extractionDetails['warnings'])
            processingWarnings = '"'+processingWarnings+'"'  
        elif len(extractionDetails['warnings']) == 1:
            processingWarnings = extractionDetails['warnings'][0]

        if extractionDetails['output']:
            self._extractedJson = extractionDetails['output']
        
        if ((self._extractedJson == None or self._extractedJson == {}) and self._statusCode < 400):
            self.updateStatus(dbStatusCode=404, dbStatus='Unknown error, no data was extracted.', commitToDB=False)
        elif(extractionDetails['dbStatusCode'] == 200):
            self.updateStatus(dbStatusCode=200, dbStatus='Successfully processed the PDF.', commitToDB=False)    
        else:
            self.updateStatus(dbStatusCode=extractionDetails['dbStatusCode'], dbStatus=processingWarnings, commitToDB=False)

        return True
    
    def commitToDB(self):
        if not self._isCommited:
            self._runningStatus = 'COMMITING_FINAL_DATA'
            to_model.write_to_model(self.getFinalData(), self.__settings['outputModleApi'], self.__settings['outputColumn'])
            self._isCommited = True
            return
        logger.error('Already committed data to db.')
        raise Exception('Already committed data to db.')
    