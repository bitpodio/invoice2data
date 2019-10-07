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
        self._tableLinesArr = []
        self._noisyLineNumber = []
        self._multiValueTyes = ['Description', 'Item']
    
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
        match = None
        if line.strip() == '':
            return borders
        # 1. split line by 2 or more spaces e.g. - "abc    xyz   pqr" 
        iterator = re.finditer("\\s{2}([^\\s]+\\s?[^\\s]+\\s?)+", line) 
        for match in iterator:
            #2. get the starting and the ending index of "xyz" & "pqr" in above example
            startingIndex = match.span()[0] + 2 # +2 is for counting two spaces that we are using as seperator
            endingIndex = match.span()[1] if line[match.span()[1]-1] != " " else match.span()[1] - 1
            borders.append((startingIndex, endingIndex))
        if not match:
            return None # this means the line is not a header line.
        # 3. check if there is a first column without any preceeding spaces
        mayBeFirstColumn = line[:borders[0][0]]
        if mayBeFirstColumn.strip() != "": # if this is true that means there is no space of the left of the first column or only one space.
            # 4. get the starting and ending index for the first column
            if line[0] == " ":
                columnStarting = 1
            else:
                columnStarting = 0
            borders = [(columnStarting, len(mayBeFirstColumn.strip()) + columnStarting)] + borders
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
        1. Updates the table body "_tableLinesArr"
        2. Return start and end regex of the table
        '''
        assert self._fileText != '', 'FileText must not be empty.'
        for startRegex in self._startLineRegexes:
            start = re.search(startRegex, self._fileText)
            if start:
                self._template.tableStart = startRegex
                logger.debug(f'Table start regex found; {startRegex}')
                break

        indexOfTableEnding = 99999999
        for endRegex in self._endLineRegexes:
            tempEnd = re.search(endRegex, self._fileText)
            if tempEnd and indexOfTableEnding > tempEnd.start():
                indexOfTableEnding = tempEnd.start()
                end = tempEnd
                self._template.tableEnd = endRegex
                logger.debug(f'Table end regex found; {endRegex}')

        assert end, "Unablet to find end of the table."
        assert start, "Unable to find start of the table."
        tableText = self._fileText[start.end(): end.start()]
        assert tableText, "Unable to find table body b/w start and end regex. One of the regex could be wrong."
        self._tableLinesArr = tableText.split('\n')
        return (start, end)

    def findTableHeader(self):
        '''
        This function tries to find the table header and returns a two things 
        1. an array of colum header. 
        2. the start and end border of each column header for each column.
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
        self._finalHeaderArr = finalHeaderArr
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
        self._columnTypes = columnTypes
        return columnTypes

    def spaceBeforeLines(self, line):
        spaces = 0
        for ch in line:
            if ch == " ":
                spaces += 1
            else:
                break
        return spaces

    def getLeftMostIndex(self, lineText, currentIndex):
        for i in range(currentIndex, 0, -1):
            if lineText[i] == " ":
                if i == currentIndex:
                    # This to handle cases like this e.g.
                    #  Column1   Column2
                    #     2.00 EACH
                    #      2.10  EACH
                    #
                    return currentIndex
                return i + 1
        raise Exception(f'Huh, this is too complex. Trying to find borders of this line "{lineText}". \n Note: there could be line_group_header in the table whoses regex in not in db.')
    
    def findNoisyLinesInTable(self, finalColumnBoundries, fuzzyBorders):
        '''
        This function creates an array of noisy lines using below rules:
        1. Remove lines where column values are spaning accross more than two fields.
        '''
        # TO-DO
        return True

    def getColumnBorders(self, finalHeaderTuple):
        noOfColumns = len(finalHeaderTuple)
        # fuzzyColumBordersArrayForEachLine 
        fuzzyColumBorders = []
        finalColumnBoundries = []
        leadingSpaces = self.spaceBeforeLines(self._tableLinesArr[0])
        logger.debug('******* fix me ********')
        # TO-DO -> if the spaces croses the border of the 2nd column header then we should assume that the first column is empty.

        # leadingSpaces are the spaces that we expect every line will have.
        for line in self._tableLinesArr:
            line = line[leadingSpaces:] # removing leading spaces to avoid false first column detection because
            # the below regex considers 2 spaces as column border.
            iterator = re.finditer("\\s{2}[^\\s]+", line)
            fuzzyBorders = [0]
            for match in iterator:
                fuzzyBorders.append(match.span()[0]+ 2 + leadingSpaces)
            fuzzyColumBorders.append(fuzzyBorders)

        # set initial values for column boundries based on header boundries
        # the left most border of the header will act as the starting of a header
        # if the columns values are extending towards left then we will extend the order to the left.
        for headerTuple in finalHeaderTuple:
            finalColumnBoundries.append(headerTuple[0])
        finalColumnBoundries[0] = 0

        # TO-DO --> self.findNoisyLinesInTable(finalColumnBoundries, fuzzyBorders) 

        # approch explanation. 
        # for all the lines
        # 1. we will ignore the first value (i.e. left border of the first column) because it will always be zero.
        # 2. for all the other values, we will take minimum value index for that column from all the lines.
        # 3. if the there is text on the left of the border then move towards the left until you encounter a space. 
        # 4. if the index is missing i.e. the next line doesn't have that column then we will ignore that.
        for lineIndex, fuzzyBorders in enumerate(fuzzyColumBorders):
            logger.debug(f"Processing : {self._tableLinesArr[lineIndex]}")
            skipFuzzyBorderCheck = False
            if noOfColumns < len(fuzzyBorders):
                logger.warning(f'There are extra columns detected in some rows.')
                skipFuzzyBorderCheck = True
            if not skipFuzzyBorderCheck:
                for i in range(1, len(fuzzyBorders)):
                    if finalColumnBoundries[i] > fuzzyBorders[i]:
                        finalColumnBoundries[i] = fuzzyBorders[i]
        
        #check if there is text on the immediate left side of of the column border.
        for lineText in self._tableLinesArr:
            for i in range(1, len(finalColumnBoundries)):
                if finalColumnBoundries[i] <= len(lineText) and lineText[finalColumnBoundries[i] - 1] != " ":
                    finalColumnBoundries[i] = self.getLeftMostIndex(lineText,finalColumnBoundries[i])
                    
        return finalColumnBoundries

    def getTableMatrix(self, finalHeaderTuple, columnTypes):
        '''
        This function processes each row of the table and tries to predict how many columns does that row have.
        and tries to find appropriate regex for that column
        '''
        # 1 remove the blank lines
        self._tableLinesArr = list(filter(None, self._tableLinesArr))
        # 2 remove table lines if the regex matches with line_group_header
        line_group_regex = ''
        for line in self._tableLinesArr:
            for regex in self._tableValueRegexes["line_group_header"]:
                if re.match(regex, line):
                    line_group_regex = regex
                    break
        if line_group_regex != '':
            regex = re.compile(line_group_regex)
            lines_without_line_group_regex = [x for x in self._tableLinesArr if not regex.match(x)]
            self._tableLinesArr = lines_without_line_group_regex
            self._template.line_group_header = line_group_regex

        # 3 prepare table matrix based on spaces
        columnBorderArr = self.getColumnBorders(finalHeaderTuple)

        # start matching dataTypes with columns values.
        # We will not check dataTypes for types like Items and Description because they are mixed
        # types and can have multiple values. (Let's call them multi-value types.)
        startingPositionOfLeftOverText = None
        tableMatrix = []
        lineArr = []
        for line in self._tableLinesArr:
            last = 0
            for i in range(len(columnBorderArr)-1):
                # 1. check if there is some leftover text from last column 
                #    and adjust the column starting according to that.
                if startingPositionOfLeftOverText:
                    columnStart = startingPositionOfLeftOverText
                else:
                    columnStart = columnBorderArr[i]
                currentColumnText = line[columnStart:columnBorderArr[i+1]]
                leadingSpaces = self.spaceBeforeLines(currentColumnText)
                currentColumnText = currentColumnText.strip()
                # 2. If the current column text is empty then add blank to the line array and move to next column
                if currentColumnText == '':
                    lineArr.append(currentColumnText)
                    startingPositionOfLeftOverText = None
                    continue
                # 3. Selected match is the longest regex match for the given data type.
                selectedMatch = None
                for regex in self._tableValueRegexes[columnTypes[i]]:
                    match = re.match(regex,currentColumnText)
                    if match:
                        if not selectedMatch:
                            selectedMatch = match
                        else:
                            seletedMatchLength = selectedMatch.span()[1] - selectedMatch.span()[0]
                            currentMatchLength = match.span()[1] - match.span()[0]
                            if seletedMatchLength < currentMatchLength:
                                selectedMatch = match
                        continue
                assert selectedMatch, f'No matching regex found for value - "{currentColumnText}" column type - "{columnTypes[i]}".'
                # 4. if there is some left over text after regex match then update
                #    leftOverTextFromLastColumn otherwise set it to None
                columnEnd = columnStart + selectedMatch.span()[1] + leadingSpaces
                if line[columnEnd:columnBorderArr[i+1]].strip() != '':
                    currentColumnText = line[columnStart:columnEnd]
                    startingPositionOfLeftOverText = columnEnd
                else:
                    currentColumnText = line[columnStart:columnBorderArr[i+1]]
                    startingPositionOfLeftOverText = None

                # 5. Add selected text to the lineArr
                lineArr.append(currentColumnText)
                last = i+1
            lineArr.append(line[columnBorderArr[last]:])
            tableMatrix.append(lineArr)
            lineArr = []        
        if logging.DEBUG >= logger.level:
            for line in tableMatrix:
                logger.debug(line)
        return tableMatrix


    def matchCurrentRow(self, line, rowNo, lineRegex, lastFieldRegex):
        tempLineRegex = ''
        for value in lineRegex:
            if value != '':
                if tempLineRegex == '':
                    tempLineRegex = value
                else:
                    tempLineRegex =  tempLineRegex + '\\s+' + value
        if tempLineRegex != '' and lastFieldRegex != '':
            tempLineRegex = tempLineRegex + '\\s+' + lastFieldRegex
        elif lastFieldRegex != '':
            tempLineRegex = lastFieldRegex
        tempLineRegex = '^\\s*' + tempLineRegex + '\\s*$'
        tempLine = ''.join(line[i] for i in range(rowNo + 1))
        match = re.search(tempLineRegex, tempLine)
        return True if match else False


    def matchAndUpdateCurrentRegex(self, numberOfColumns, lineRegexArray, regexRowToTest, tableMatrix, rowNo, columnTypes, linestableMatrix):
        '''
        Given data and regex with data row number. This function check if there is already a matching regex line entry for that line or not.
        **** parameters ****
        ----------------------------------------------------------
        numberOfColumns -  nnumber of columns in the table.
        lineRegexArray -  the current array of regex to match the with given row.
        regexRowToTest - row number of the regex to test.
        tableMatrix -  data array to test the regex against
        '''
        doesRowMatch = True
        for columnNo in range(numberOfColumns):
            regex = lineRegexArray[regexRowToTest][columnNo]
            if tableMatrix[rowNo][columnNo].strip() == "": # if current column value is blank
                assert (rowNo != 0 or columnNo != 0), 'We do not support auto template creation if first column of first row is blank.'
                if regex != '':
                    endOfNamedGroup = regex.rfind(')') + 1
                    if endOfNamedGroup in [-1, 0]:
                        doesRowMatch = False
                        logger.debug('Unable to find regex boundries.')
                    elif len(regex) - 1 >= endOfNamedGroup and regex[endOfNamedGroup] == '?':
                        continue
                    else:
                        lineRegexArray[regexRowToTest][columnNo] = regex[:endOfNamedGroup] + '?' + regex[endOfNamedGroup:]
                continue
            elif regexRowToTest == 0:
                # If the value is not blank
                if regex == '':
                    # find new regex for this column
                    for regex2 in self._tableValueRegexes[columnTypes[columnNo]]: # search regex for current column type based on table header
                        match = re.search(regex2 + "\\s*", tableMatrix[rowNo][columnNo])
                        if match:
                            currentLineRegex = []
                            for i in range(columnNo):
                                currentLineRegex.append(lineRegexArray[regexRowToTest][i])
                            if self.matchCurrentRow(tableMatrix[rowNo], columnNo, currentLineRegex, regex2):
                                break
                            else:
                                match = False
                                continue
                    if match:
                        endOfNamedGroup = regex2.rfind(')') + 1
                        if endOfNamedGroup in [-1, 0]:
                            doesRowMatch = False
                            logger.debug('Unable to find regex boundries.')
                        elif len(regex2) - 1 >= endOfNamedGroup and regex2[endOfNamedGroup] == '?':
                            lineRegexArray[regexRowToTest][columnNo] = regex2
                        else:
                            lineRegexArray[regexRowToTest][columnNo] = regex2[:endOfNamedGroup] + '?' + regex2[endOfNamedGroup:]
                    else:

                        raise Exception(f'First Line: Unable to find regex for {tableMatrix[rowNo][columnNo]}, column type {columnTypes[columnNo]}.')
                else:
                    match = re.search(regex + "\\s*", tableMatrix[rowNo][columnNo])
                    if match:
                        currentLineRegex = []
                        for i in range(columnNo):
                            currentLineRegex.append(lineRegexArray[regexRowToTest][i])
                        match = self.matchCurrentRow(tableMatrix[rowNo], columnNo, currentLineRegex, '')
                    if not match:
                        # find another one that fits all
                        newRegex = ''
                        for regex2 in self._tableValueRegexes[columnTypes[columnNo]]:
                            count = 0
                            for line in linestableMatrix:
                                isMatch = re.search(regex2, line[columnNo])
                                if isMatch:
                                    currentLineRegex = []
                                    for i in range(columnNo):
                                        currentLineRegex.append(lineRegexArray[regexRowToTest][i])
                                    if self.matchCurrentRow(tableMatrix[rowNo], columnNo, currentLineRegex, regex2):
                                        count += 1
                                        continue
                                    else:
                                        isMatch = False
                                        continue
                            if count == len(linestableMatrix):
                                newRegex = regex2
                                break
                        if newRegex == '':
                            logger.error(f'First Line: Unable to find regex for {tableMatrix[rowNo][columnNo]}, column type {columnTypes[columnNo]}.')
                            raise Exception(f'First Line: Unable to find regex for {tableMatrix[rowNo][columnNo]}, column type {columnTypes[columnNo]}.')
                        else:
                            #check if previous regex was optional
                            endOfNamedGroup = regex.rfind(')') + 1
                            if endOfNamedGroup in [-1, 0]:
                                logger.debug('Unable to find regex boundries.')
                                doesRowMatch = False
                                continue
                            elif len(regex) - 1 >= endOfNamedGroup and regex[endOfNamedGroup] == '?':
                                endOfNamedGroup = newRegex.rfind(')') + 1
                                lineRegexArray[regexRowToTest][columnNo] = newRegex[:endOfNamedGroup] + '?' + newRegex[endOfNamedGroup:]
                            else:
                                lineRegexArray[regexRowToTest][columnNo] = newRegex
                    if doesRowMatch:
                        continue
                    else:
                        break
            else:
                match = re.search(regex + "\\s*", tableMatrix[rowNo][columnNo])
                if match:
                    currentLineRegex = []
                    for i in range(columnNo+1):
                        currentLineRegex.append(lineRegexArray[regexRowToTest][i])
                    match = self.matchCurrentRow(tableMatrix[rowNo], columnNo, currentLineRegex, '')
                if not match:
                    logger.error(f'Unable to find regex for {tableMatrix[rowNo][columnNo]}, column type {columnTypes[columnNo]}, regex {regex}.')
                    doesRowMatch = False
                    break
                continue
        return doesRowMatch

    def createTemplate(self, tableMatrix, columnTypes):
        # 3 find regex by type for each column
        # 3.1 column is description or item. look for following items:
        #     Start: time am/pm
        #     End: time am/pm
        #     Date: date
        #     NDIS No. : number
        #     Rate: \d+\.\d{2}\s*per hour
        #     etc.
        # 
        # 3.2 while scaning column if there is some left over text check then
        #     check the type of the next column and merge it with the next column if needed.
        #
        # 3.3 if there is some unknown value that does not fit any regex of the
        #     corresponding column type and the column type is not item or description then 
        #     skip that text and log an error but continoue the process.
        #
        # 3.4 if for some column no value is found then throw an error.
        logger.debug('********* Started preparing template **********')
        numberOfColumns = len(columnTypes)
        lineRegexArray = []
        firstLineArr = []
        otherLineArr = []
        for rowNo in range(len(tableMatrix)):
            logger.debug(f'Preparing template for line - "{tableMatrix[rowNo]}".')
            currentLineRegex = []
            match = False
            # If this is first row of the table then we simply keep appending the regexs to current regex array for each column for first row in order.
            if rowNo == 0:
                firstLineArr.append(tableMatrix[rowNo])
                for columnNo in range(numberOfColumns):
                    if tableMatrix[rowNo][columnNo].strip() == "": # if current column value is blank
                        assert columnNo != 0, 'We do not support auto template creation if first column of first row is blank.'
                        currentLineRegex.append('')
                        continue
                    for regex in self._tableValueRegexes[columnTypes[columnNo]]: # search regex for current column type based on table header
                        match = re.search(regex + "\\s*", tableMatrix[rowNo][columnNo])
                        if match:
                            if self.matchCurrentRow(tableMatrix[rowNo], columnNo, currentLineRegex, regex):
                                break
                            else:
                                match = False
                                continue
                    if match:
                        currentLineRegex.append(regex)
                    else:
                        raise Exception(f'Unable to find regex for {tableMatrix[rowNo][columnNo]}. Column type - {columnTypes[columnNo]}')
            # If this is not first row of the tables but the first row of a multiline entry.
            # We simply match it with first row. If something is missing we make that optional in first_row regex.
            # If there is any column which does not match with corresponding first row column then throw an error.  
            elif rowNo != 0 and re.search(lineRegexArray[0][0], tableMatrix[rowNo][0]): 
                firstLineArr.append(tableMatrix[rowNo])
                isMatch = self.matchAndUpdateCurrentRegex(numberOfColumns, lineRegexArray, 0, tableMatrix, rowNo, columnTypes, firstLineArr)
                assert isMatch, 'Unable to find regex for first line.'
            else:
                otherLineArr.append(tableMatrix[rowNo])
                isMatch = False
                if lineRegexArray[1:] != []:
                    for i in range(1,len(lineRegexArray)):
                        if lineRegexArray[i] == []:
                            continue
                        isMatch = self.matchAndUpdateCurrentRegex(numberOfColumns, lineRegexArray, i, tableMatrix, rowNo, columnTypes, otherLineArr)
                        if isMatch:
                            break
                    if isMatch:
                        continue
                logger.debug(f'No previously matching regex lines found for *{tableMatrix[rowNo]}*')

                if isMatch:
                    continue

                for columnNo in range(numberOfColumns):
                    if tableMatrix[rowNo][columnNo].strip() == "": # if current column value is blank
                        currentLineRegex.append('')
                        continue
                    for regex in self._tableValueRegexes[columnTypes[columnNo]]: # search regex for current column type based on table header
                        match = re.search(regex + "\\s*", tableMatrix[rowNo][columnNo])
                        if match:
                            if self.matchCurrentRow(tableMatrix[rowNo], columnNo, currentLineRegex, regex):
                                break
                            else:
                                match = False
                                continue
                    if match:
                        currentLineRegex.append(regex)
                    else:
                        logger.warning(f'Unable to find regex for {tableMatrix[rowNo][columnNo]}, so skipping this value.')
                        currentLineRegex.append(tableMatrix[rowNo][columnNo])
                    
                logger.debug(tableMatrix[rowNo][columnNo])
            lineRegexArray.append(currentLineRegex)
        
        firstLine = True
        self._template.line = []
        for lineRegex in lineRegexArray:
            lineRegex = list(filter(None, lineRegex))
            if lineRegex == []:
                continue
            if firstLine:
                tempLineRegex = '\\s+'.join(lineRegex)
                tempLineRegex = '^\\s*' + tempLineRegex + '$'
                self._template.tableFirstLine = tempLineRegex
                firstLine = False
            else:
                tempLineRegex = '\\s+'.join(lineRegex)
                tempLineRegex = '^\\s*' + tempLineRegex + '$'
                self._template.line.append(tempLineRegex)
        
        return self._template.getTemplateDict()