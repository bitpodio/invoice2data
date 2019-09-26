import yaml
import subprocess
import glob
import re 
import logging
from template import Template

#Creating an object 
logger=logging.getLogger('__main__') 
  

class TemplateCreator:

    def __init__(self):
        self._nonTableValueRegexes = {}
        self._tableValueRegexes = {}
        self._startLineRegexes = []
        self._endLineRegexes = []
        self._lineGroupRegexes = []
        self._currentLineRegex = []
        self._finalLineRegexes = []
        self._template = Template()
        self._fileText = ''
        self._fileTextArr = []
        self._tableBodyArr = []
    
    @property
    def fileText(self):
        return self._fileText
    @fileText.setter
    def fileText(self, value):
        if isinstance(value, str):
            self._fileTextArr = value.split('\n')
            self._fileText = value
        else:
            raise ValueError('File text must be a string.')

    @property
    def nonTableValueRegexes(self):
        return self._nonTableValueRegexes
    @nonTableValueRegexes.setter
    def nonTableValueRegexes(self, value):
        if isinstance(value, dict):
            self._nonTableValueRegexes = value
        else:
            raise ValueError('File text must be a dict.')

    def readFile(self, filePath):
        '''Takes filePath as input and returns the text of the file.'''
        txt = ''
        fileName = filePath.split('/')[-1]
        logger.debug(f'Reading file {fileName}.')
        with open(filePath, 'r') as f1:
            txt = f1.read()
        return txt

    def readYML(self, filePath):
        with open(filePath, 'r') as f2:
            ymalAsDictionary = yaml.load(f2)
        return ymalAsDictionary

    def getBorderTuples(self, line):
        '''
        This function takes a line as an input and returns the an array of tuples of column orders.
        E.g.
        line = "abc    xyz   pqr"
        return [(0,2), (6,9), (12,15)]
        '''
        borders = []
        if line.strip() == '':
            return borders
        # 1. split line by 2 or more spaces e.g. - "abc    xyz   pqr" 
        iterator = re.finditer("\\s{2}([^\\s]+\\s?[^\\s]+\\s?)+", line) 
        for match in iterator:
            #2. get the starting and the ending index of "xyz" & "pqr" in above example
            startingIndex = match.span()[0] + 2
            endingIndex = match.span()[1] if line[match.span()[1]-1] != " " else match.span()[1] - 1
            borders.append((startingIndex, endingIndex))
        # 3. check if there is a first column without any preceeding spaces
        mayBeFirstColumn = line[:borders[0][0]]
        if mayBeFirstColumn.strip() != "":
            # 4. get the starting and ending index for the first column
            borders = [(0, len(mayBeFirstColumn.strip()))] + borders
        return borders

    def isValidHeaderLine(self, borders, lineText):
        '''
        Tries to predict if the the given line is a header line or not.
        Returns True if line is a header line otherwise False.
        '''
        # 1 match regex
        if not re.search('^[A-Za-z\\/. ]+$', lineText):
            return False
        # 2 check length
        for t in borders: # t stands for tuple
            if t[0] - t[1] > 15:
                return False 
        return True

    def getFinalHeader(self, header, lineAbove, lineMiddle, lineBelow):
        '''
        This function calculates the borders of the headers and returns a tuple of borders and header text arrays.
        
        Parameters
        -----------------------
        header - a dict of possible header line's column's border values as tuples - "selected", "above" and "below". \n
        lineAbove, lineMiddle, lineBelow - are the lines actual lines of possible haders.

        Note: We are considering these above and below lines maybe part of header. We will test it in this function. 
        '''
        finalHeaderArr = []
        finalHeaderTuple = []
        estimatedNoOfColumns = len(header["selected"])
        extraColumnsAdded = 0
        # 1. merge with above header
        if header["above"] != [] and self.isValidHeaderLine(header["above"], lineAbove):
            lastColumnCount = 0
            for aboveColumnBorder in header["above"]: # hear t1 and t2 are column text border tuples
                addedToHeader = False
                aboveColumn = lineAbove[aboveColumnBorder[0]:aboveColumnBorder[1]]
                for i in range(lastColumnCount, estimatedNoOfColumns): # the loop should only start from last column which was added 
                    middleColumnBorder = header["selected"][i - extraColumnsAdded]
                    middleColumn = lineMiddle[middleColumnBorder[0]:middleColumnBorder[1]]
                    if (aboveColumnBorder[0] - middleColumnBorder[0] == 0) or (abs(aboveColumnBorder[0] - middleColumnBorder[0]) <= 4 and len(aboveColumn) - len(lineMiddle) < 3):
                        # starting of the column above is at most the 3 chars far from the current columns starting 
                        # the ending of the column above should be with in the 3 chars from the current columns ending
                        finalHeaderArr.append(middleColumn + " " + aboveColumn)
                        ft0 = aboveColumnBorder[0] if aboveColumnBorder[0] < middleColumnBorder[0] else middleColumnBorder[0]
                        ft1 = aboveColumnBorder[1] if aboveColumnBorder[1] > middleColumnBorder[1] else middleColumnBorder[1]
                        finalHeaderTuple.append((ft0, ft1))
                        addedToHeader = True
                        lastColumnCount += 1
                        break
                    elif middleColumnBorder[0] - aboveColumnBorder[1] >= 4: 
                        # this is to handle the case when middle column has missing field/column name
                        # we are finding missing field by checking right border of the above column is 4 or more char left from left border of the column in middle 
                        # because this means that the above column if at least 4 or more chars away from it's nearest columns in middle line
                        # so we also need to increase the noOfColumns
                        finalHeaderArr.append(aboveColumn)
                        finalHeaderTuple.append((aboveColumnBorder[0], aboveColumnBorder[1]))
                        lastColumnCount += 1
                        estimatedNoOfColumns += 1
                        extraColumnsAdded += 1
                        addedToHeader = True
                        break
                    else:
                        # When there is no above column for corresponding column
                        finalHeaderArr.append(middleColumn)
                        finalHeaderTuple.append((middleColumnBorder[0], middleColumnBorder[1]))
                        lastColumnCount += 1
                if not addedToHeader:
                    logger.warning(f'Looks like "{aboveColumn}" is not part of any header text.')

        # 2. merge with below header
        if header["below"] != [] and self.isValidHeaderLine(header["below"], lineBelow):
            lastColumnCount = 0
            logger.debug("Updating start line regex.")
            self._startLineRegexes = [lineBelow] + self._startLineRegexes
            for belowColumnBorder in header["below"]: # hear t1 and t2 are column text border tuples
                addedToHeader = False
                belowColumn = lineBelow[belowColumnBorder[0]:belowColumnBorder[1]]
                for i in range(lastColumnCount, estimatedNoOfColumns): # the loop should only start from last column which was added 
                    if extraColumnsAdded > 0 :
                        middleColumnBorder = finalHeaderTuple[i]
                    else:
                        middleColumnBorder = header["selected"][i - extraColumnsAdded]
                    middleColumn = lineMiddle[middleColumnBorder[0]:middleColumnBorder[1]]
                    newHeader = ""
                    newHeaderTuple = ()
                    if (belowColumnBorder[0] - middleColumnBorder[0] == 0) or (abs(belowColumnBorder[0] - middleColumnBorder[0]) <= 4 and len(belowColumn) - len(lineMiddle) < 3):
                        # starting of the column below is at most the 3 chars far from the current columns starting 
                        # the ending of the column below should be with in the 3 chars from the current columns ending
                        newHeader = middleColumn + " " + belowColumn if middleColumn.strip() != "" else belowColumn
                        ft0 = belowColumnBorder[0] if belowColumnBorder[0] < middleColumnBorder[0] else middleColumnBorder[0]
                        ft1 = belowColumnBorder[1] if belowColumnBorder[1] > middleColumnBorder[1] else middleColumnBorder[1]
                        newHeaderTuple = (ft0, ft1)
                        addedToHeader = True
                    elif middleColumnBorder[0] - belowColumnBorder[1] >= 4: 
                        # this is to handle the case when middle column has missing field/column name
                        # so we will increase the noOfColumns
                        newHeader = belowColumn
                        newHeaderTuple = (belowColumnBorder[0], belowColumnBorder[1])
                        estimatedNoOfColumns += 1
                        extraColumnsAdded += 1
                        addedToHeader = True
                    elif len(finalHeaderArr) <= i:
                        # When there is no above column for corresponding column
                        newHeader = middleColumn
                        newHeaderTuple = (middleColumnBorder[0], middleColumnBorder[1])
                    
                    if newHeader:
                        if len(finalHeaderArr) <= i:
                            finalHeaderArr.append(newHeader)
                            finalHeaderTuple.append(newHeaderTuple)
                            lastColumnCount += 1
                        else:
                            finalHeaderArr[i] = finalHeaderArr[i] + ' ' + newHeader
                            finalHeaderTuple[i] = newHeaderTuple
                            lastColumnCount += 1
                    
                    if addedToHeader:
                        break

                if not addedToHeader:
                    logger.warning(f'Looks like "{belowColumn}" is not part of any header text.')
        
        # 3 add remaining columns. This will only be case when the middle line have missing header fields e.g.
        #                                                                                             Start    End        Hours/
        # Date          Support Item Ref      Description                                                                             Rate        Total
        #                                                                                             Time     Time        Units
        if len(finalHeaderArr) < estimatedNoOfColumns:
            for i in range(len(finalHeaderArr), estimatedNoOfColumns): # the loop should only start from last column which was added 
                middleColumnBorder = header["selected"][i - extraColumnsAdded]
                middleColumn = lineMiddle[middleColumnBorder[0]:middleColumnBorder[1]]
                finalHeaderArr.append(middleColumn)
                finalHeaderTuple.append((middleColumnBorder[0], middleColumnBorder[1]))
        return (finalHeaderTuple, finalHeaderArr)

    def getTableStartEnd(self):
        '''
        This function does two things:
        1. Updates the table body "_tableBodyArr"
        2. Return start and end regex of the table
        '''
        assert self._fileText != '', 'FileText must not be empty.'
        for startRegex in self._startLineRegexes:
            start = re.search(startRegex, self._fileText)
            if start:
                logger.debug(f'Table start regex found; {startRegex}')
                break

        for endRegex in self._endLineRegexes:
            end = re.search(endRegex, self._fileText)
            if end:
                logger.debug(f'Table end regex found; {endRegex}')
                break

        assert end, "Unablet to find end of the table."
        assert start, "Unable to find start of the table."
        tableText = self._fileText[start.end(): end.start()]
        assert tableText, "Unable to find table body b/w start and end regex. One of the regex could be wrong."
        self._tableBodyArr = tableText.split('\n')
        return (start, end)

    def findTableHeader(self):
        '''
        This function tries to find the table header and returns an array of header line(s).
        Note : Headers can also be multiline.
        '''
        (start, end) = self.getTableStartEnd()
        headerLine = self._fileText[start.start():start.end()]
        index = self._fileTextArr.index(headerLine)
        lineSeleted = self._fileTextArr[index]
        lineAbove = self._fileTextArr[index-1]
        lineBelow = self._fileTextArr[index+1]
        header = {
            "above": [],
            "selected": [],
            "below": []
        }
        header["above"] = self.getBorderTuples(lineAbove)
        header["selected"] = self.getBorderTuples(lineSeleted)
        header["below"] = self.getBorderTuples(lineBelow)
        logger.debug(f'Tuples for possible header lines : {header}')
        (finalHeaderTuple, finalHeaderArr) = self.getFinalHeader(header, lineAbove, lineSeleted, lineBelow)
        assert len(finalHeaderTuple) == len(finalHeaderArr), "Header values and tuples don't match."
        logger.debug(f'The final list headers is : {finalHeaderArr}')

        # just updating the table body text. we do not need header index now.
        self.getTableStartEnd()
        return (finalHeaderTuple, finalHeaderArr)

    def prepareRegexForNonTableValue(self):
        '''
        This function tries to find the non table fields that we extract like Invoice Number.
        If any of the fields found, their regex is added to template's field regex.
        '''
        assert self._fileText != '', 'FileText must not be empty.'
        assert self._nonTableValueRegexes != {}, 'nonTableValueRegexes must not be empty.'

        for fieldName, fieldRegexes in self._nonTableValueRegexes.items():
            found = False
            for fieldRegex in fieldRegexes:
                output = re.findall(fieldRegex, self._fileText)
                outputLength = len(output)
                if outputLength == 1:
                    found = True
                    logger.debug(f'Found regex "{fieldRegex}" for field "{fieldName}".')
                    self._template.fields[fieldName] = fieldRegex
                    break
                elif outputLength > 1:
                    txtOutput = ', '.join(output)
                    logger.warning(f'For field "{fieldName}", {outputLength} values matched - {txtOutput}. Trying another regexes.')
            if not found:
                logger.warning(f'Field "{fieldName}" is not found in the pdf.')

    def getColumnTypes(self, headers):
        '''
        Returns an array of keys, one for each column.\n
        These keys are used to search the regex for the values of each column. e.g.\n
        If the header is "Support Item Ref" then the key that you might get is "Item".\n
        Using that you can search all the regexes of Item column, which propabaly is appropriate type to be searched for "Support Item Ref".\n
        '''
        columnTypes = []
        allColumnTypes = list(self._tableValueRegexes.keys())
        for header in headers:
            foundColumnType = False
            for columnType in allColumnTypes:
                if columnType in header:
                    columnTypes.append(columnType)
                    foundColumnType = True
                    break
            assert foundColumnType, f'Unable to find column type for header {header}.'
        return columnTypes

    def getTableMatrix(self, finalHeaderTuple, possibleColumnTypes):
        '''
        This function processes each row of the table and tries to predict how many columns does that row have.
        and tries to find appropriate regex for that column
        '''
        # 1 remove the blank lines
        for index, line in enumerate(self._tableBodyArr):
            if line.strip() == "":
                del self._tableBodyArr[index]
        
        for i in self._tableBodyArr:
            print(i)
        
