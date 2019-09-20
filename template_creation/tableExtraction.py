import yaml
import subprocess
import glob
import re 

def prepareHeaderTemplate(template, fileText):
    with open('/Developer/bitpod/invoice2data/playground/db.yml', 'r') as f2:
        fieldRegex = yaml.load(f2)
    for invoice_number in fieldRegex['invoice_numbers']:
        output = re.findall(invoice_number, fileText)
        if len(output) == 1:
            print(f'{len(output)} matched: {invoice_number}\n')
            template['fields']['invoice_number'] = invoice_number


    for provider_id in fieldRegex['provider_ids']:
        output = re.findall(provider_id, fileText)
        if len(output) == 1:
            print(f'{len(output)} matched: {provider_id}\n')
            template['fields']['provider_id'] = provider_id


    for amount in fieldRegex['amounts']:
        output = re.findall(amount, fileText)
        if len(output) == 1:
            print(f'{len(output)} matched: {amount}\n')
            template['fields']['amount'] = amount


    for date in fieldRegex['dates']:
        output = re.findall(date, fileText)
        if len(output) == 1:
            print(f'{len(output)} matched: {date}\n')
            template['fields']['date'] = date
    return template

def spaceBeforeLines(line):
    spaces = 0
    for ch in line:
        if ch == " ":
            spaces += 1
        else:
            break
    return spaces

def getBorderForLines(lines, leadingSpaces, fuzzyColumBorders=[]):
    for line in lines:
        if line.strip() == '\n': # skip blank lines
            continue
        line = line[leadingSpaces:] # removing leading spaces to avoid false first column detection because
        # the below regex considers 2 spaces as column border.
        iterator = re.finditer("\\s{2}[^\\s]+", line)
        fuzzyBorders = [0]
        for match in iterator:
            fuzzyBorders.append(match.span()[0]+ 2 + leadingSpaces)
        fuzzyColumBorders.append(fuzzyBorders)
        return fuzzyColumBorders

def getColumnBorders(lines, headers, spacesBeforeHeader, fuzzyColumBorders=[]):
    noOfColumns = len(headers)
    # fuzzyColumBordersArrayForEachLine 
    finalColumnBoundries = [0]
    # check if first line is alligned with headers or not
    # if it is not alligned then either the first line is part of header 
    # or the text in the table is alligned in center which we can not processes.
    leadingSpaces = spaceBeforeLines(lines[0])
    if leadingSpaces not in range(spacesBeforeHeader-3,spacesBeforeHeader+3):
        print(f'Skipping line {lines[0]}.')
        del lines[0]
        leadingSpaces = spaceBeforeLines(lines[0])
    # leadingSpaces are the spaces that we expect every line will have.
    fuzzyColumBorders += getBorderForLines(lines, leadingSpaces)

    assert noOfColumns == len(fuzzyColumBorders[0]), "Header length does not match with column length. Unable to process."
    finalColumnBoundries = fuzzyColumBorders[0]

    # approch explanation. 
    # for all the lines
    # 1. we will ignore the first value (i.e. left border of the first column) because it will always be zero.
    # 2. for all the other values, we will take minimum value for that index from all the lines. 
    # 3. if the index is missing i.e. the next line doesn't have that column then we will ignore that.
    for fuzzyBorders in fuzzyColumBorders:
        for i in range(1, len(fuzzyBorders)):
            if finalColumnBoundries[i] > fuzzyBorders[i]:
                finalColumnBoundries[i] = fuzzyBorders[i]
    print(finalColumnBoundries)
    return finalColumnBoundries

def matchCurrentRow(line, rowNo, lineRegex, lastFieldRegex):
    tempLineRegex = '\\s+'.join(lineRegex)
    if tempLineRegex != '':
        tempLineRegex = tempLineRegex + '\\s+' + lastFieldRegex
    else:
        tempLineRegex = lastFieldRegex
    tempLineRegex = '^\\s*' + tempLineRegex + '\\s*$'
    tempLine = ''.join(line[i] for i in range(rowNo + 1))
    match = re.search(tempLineRegex, tempLine)
    return True if match else False

def matchAndUpdateCurrentRegex(numberOfColumns, regexArray, regexRowToTest, dataArr, rowNo, tableRegex, columnTypes, linesDataArr):
    doesRowMatch = True
    for columnNo in range(numberOfColumns):
        regex = regexArray[regexRowToTest][columnNo]
        if dataArr[rowNo][columnNo].strip() == "": # if current column value is blank
            assert (rowNo != 0 or columnNo != 0), 'We do not support auto template creation if first column of first row is blank.'
            if regex != '':
                endOfNamedGroup = regex.rfind(')') + 1
                if endOfNamedGroup == -1:
                    print('Unable to find regex boundries.')
                elif len(regex) - 1 >= endOfNamedGroup and regex[endOfNamedGroup] == '?':
                    continue
                else:
                    regexArray[regexRowToTest][columnNo] = regex[:endOfNamedGroup] + '?' + regex[endOfNamedGroup:]
            continue
        elif regexRowToTest == 0:
            # If the value is not blank
            match = re.search(regex + "\\s*", dataArr[rowNo][columnNo])
            if not match:
                # find another one that fits all
                newRegex = ''
                for regex2 in tableRegex[columnTypes[columnNo]]:
                    count = 0
                    for line in linesDataArr:
                        isMatch = re.search(regex2, line[columnNo])
                        if isMatch:
                            count += 1
                    if count == len(linesDataArr):
                        newRegex = regex2
                        break
                if newRegex == '':
                    print(f'Unable to find regex for {dataArr[rowNo][columnNo]}, column type {columnTypes[columnNo]}.')
                    doesRowMatch = False
                    break
                else:
                    #check if previous regex was optional
                    endOfNamedGroup = regex.rfind(')') + 1
                    if endOfNamedGroup == -1:
                        print('Unable to find regex boundries.')
                        continue
                    elif len(regex) - 1 >= endOfNamedGroup and regex[endOfNamedGroup] == '?':
                        endOfNamedGroup = newRegex.rfind(')') + 1
                        regexArray[regexRowToTest][columnNo] = newRegex[:endOfNamedGroup] + '?' + newRegex[endOfNamedGroup:]
                    else:
                        regexArray[regexRowToTest][columnNo] = newRegex
            if doesRowMatch:
                continue
            else:
                break
        else:
            match = re.search(regex + "\\s*", dataArr[rowNo][columnNo])
            if not match:
                print(f'Unable to find regex for {dataArr[rowNo][columnNo]}, column type {columnTypes[columnNo]}.')
                doesRowMatch = False
                break
            continue
    return doesRowMatch

def prepareTableTemplate(template, fileText):
    print('Finding table ...')

    with open('/Developer/bitpod/invoice2data/playground/tabledb.yml', 'r') as f2:
        tableRegex = yaml.load(f2)

    for startRegex in tableRegex['Table_Start']:
        start = re.search(startRegex, fileText)
        if start:
            print(f'Table start regex found; {startRegex}')
            template['multilines']['start'] = startRegex

    for endRegex in tableRegex['Table_End']:
        end = re.search(endRegex, fileText)
        if end:
            print(f'Table end regex found; {endRegex}')
            template['multilines']['end'] = endRegex

    tableText = fileText[start.end(): end.start()]
    assert tableText, "Unable to find table body b/w start and end regex. One of the regex could be wrong."
    
    allColumnTypes = list(tableRegex.keys())
    allColumnTypes.remove('Table_Start')
    allColumnTypes.remove('Table_End')

    # Get all the non empty lines
    lines = re.split("\\n", tableText)
    for i in range(len(lines)):
        lines[i] = lines[i]
    lines = list(filter(None, lines))

    print(f'{len(lines)} individual line(s) found in table.')
    headerLine = fileText[start.start():start.end()]
    spacesBeforeHeader = spaceBeforeLines(headerLine)
    fuzzyColumBorders = getBorderForLines([headerLine], spacesBeforeHeader)
    headerLine =  headerLine.strip()
    headers = re.split(" \\s+", headerLine) # Task-1 cases where haders are saperated with one space need to be handled.
    numberOfColumns = len(headers)
    print(f'{numberOfColumns} columns detected in table.')
    print(headers)

    finalColumnBoundries = getColumnBorders(lines, headers, spacesBeforeHeader, fuzzyColumBorders)

    # find all the column type to run regex for each column
    columnTypes = []
    for header in headers:
        foundColumnType = False
        for columnType in allColumnTypes:
            if columnType in header:
                columnTypes.append(columnType)
                foundColumnType = True
                break
        assert foundColumnType, f'Unable to find column type for header {header}.'
        

    dataArr = []
    lineArr = []
    for line in lines:
        last = 0
        for i in range(len(finalColumnBoundries)-1):
            lineArr.append(line[finalColumnBoundries[i]:finalColumnBoundries[i+1]])
            last = i+1
        lineArr.append(line[finalColumnBoundries[last]:])
        dataArr.append(lineArr)
        lineArr = []
    for line in dataArr:
        print(line)

    # We will not prepare regex for each column and append them together in order.
    # Note that regex of the first column or the first row will not change in all the itaration.
    # other column's regexs can be improved 

    regexArray = []
    isFirstLine = False
    firstLineArr = []
    otherLineArr = []
    for rowNo in range(len(dataArr)):
        currentLineRegex = []
        match = False
        if rowNo == 0:
            for columnNo in range(numberOfColumns):
                if dataArr[rowNo][columnNo].strip() == "": # if current column value is blank
                    assert columnNo == 0, 'We do not support auto template creation if first column of first row is blank.'
                    currentLineRegex.append('')
                    continue
                for regex in tableRegex[columnTypes[columnNo]]: # search regex for current column type based on table header
                    match = re.search(regex + "\\s*", dataArr[rowNo][columnNo])
                    if match:
                        if matchCurrentRow(dataArr[rowNo], columnNo, currentLineRegex, regex):
                            break
                        else:
                            match = False
                            continue
                if match:
                    currentLineRegex.append(regex)
                else:
                    raise Exception(f'Unable to find regex for {dataArr[rowNo][columnNo]}')
        elif rowNo != 0 and re.search(regexArray[0][0], dataArr[rowNo][0]): 
            firstLineArr.append(dataArr[rowNo])
            isMatch = matchAndUpdateCurrentRegex(numberOfColumns, regexArray, 0, dataArr, rowNo, tableRegex, columnTypes, firstLineArr)
            assert isMatch, 'Unable to find regex for first line.'
        else:
            otherLineArr.append(dataArr[rowNo])
            isMatch = False
            if regexArray[1:] != []:
                for i in range(1,len(regexArray)):
                    isMatch = matchAndUpdateCurrentRegex(numberOfColumns, regexArray, i, dataArr, rowNo, tableRegex, columnTypes, otherLineArr)
                    if isMatch:
                        break
                if isMatch:
                    continue
                
            for columnNo in range(numberOfColumns):
                if dataArr[rowNo][columnNo].strip() == "": # if current column value is blank
                    currentLineRegex.append('')
                    continue
                for regex in tableRegex[columnTypes[columnNo]]: # search regex for current column type based on table header
                    match = re.search(regex + "\\s*", dataArr[rowNo][columnNo])
                    if match:
                        if matchCurrentRow(dataArr[rowNo], columnNo, currentLineRegex, regex):
                            break
                        else:
                            match = False
                            continue
                if match:
                    currentLineRegex.append(regex)
                else:
                    print(f'Unable to find regex for {dataArr[rowNo][columnNo]}, so skipping this value.')
                    currentLineRegex.append(regex)
                
            print(dataArr[rowNo][columnNo])
        regexArray.append(currentLineRegex)
    firstLine = True
    template['multilines']['line'] = []
    for lineRegex in regexArray:
        lineRegex = list(filter(None, lineRegex))
        if lineRegex == []:
            continue
        if firstLine:
            tempLineRegex = '\\s+'.join(lineRegex)
            tempLineRegex = '^\\s*' + tempLineRegex + '$'
            template['multilines']['first_line'] = tempLineRegex
            firstLine = False
        else:
            tempLineRegex = '\\s+'.join(lineRegex)
            tempLineRegex = '^\\s*' + tempLineRegex + '$'
            template['multilines']['line'].append(tempLineRegex)
    print(template)






newFile = '/Developer/bitpod/pythonProject/mountedLocation/pdfs/Privider_Invoice_Samples/PROV003887_Hallmark Workplace Solutions/181205_Admin.pdf.txt'
fileText = ''
fileName = newFile.split('/')[-1]
print(f'Preparing template for {fileName}.')
with open(newFile, 'r') as f1:
    fileText = f1.read()

template = {}
template['fields'] = {}
template['multilines'] = {}

template = prepareHeaderTemplate(template, fileText)

prepareTableTemplate(template, fileText)

# rowNumber = 0
# firstLineRegex = ''
# for line in lines:
#     print('*'+line+'*')
#     if (rowNumber == 1 and firstLineRegex != ''):
#         firstLineRegex = currentRegex
#         match = re.search(firstLineRegex, line)
#         if match:
#             tempRow = {
#                         field: value.strip() if value else ''
#                         for field, value in match.groupdict().items()
#                     }
#             print('Found match for this line so skipping template creation. \n Data :')
#             print(tempRow)

#     currentRegex = '^\\s*'
#     currentLineData = {}
#     if 'n' == input('Do you want to write regex for this lines? (y/n)'):
#         continue
#     foundRegxForCurrentColumn = False
#     rowNumber += 1
#     if rowNumber != 1:
#         response = input('Is this a new data row? (y/n)')
#         isNewRow = True if response == 'y' else False
#     for i in range(numberOfColumns):
#         assert i == 0 or foundRegxForCurrentColumn or dataType == 'skip', f'Unable to find regex for {dataType}. Pass this to developer.'
#         dataType = input(f'Enter the type of the column no. {i+1} (type "skip" to skip this column for this line):')
#         if dataType == 'skip':
#             continue
#         assert dataType in tableRegex, f'Unable to find regex for {dataType}. Pass this to developer.'

#         for regex in tableRegex[dataType]:
#             if i == 0:
#                 tempRegex = currentRegex + regex
#             else:
#                 tempRegex = currentRegex + "\\s+" + regex

#             match = re.search(tempRegex, line)
#             foundRegxForCurrentColumn = False
#             if match:
#                 tempRow = {}
#                 for field, value in match.groupdict().items():
#                     lastKey = field
#                     lastValue = value.strip()
#                     tempRow[field] = value.strip() if value else ''
#                 if len(tempRow.keys()) > len(currentLineData.keys()):
#                     if 'n' == input(f'Column name - {lastKey}, column value - {lastValue}. Are the key-value correct? (y/n):'):
#                         continue
#                     currentRegex = tempRegex
#                     currentLineData = tempRow 
#                     if i == numberOfColumns - 1:
#                         currentRegex = currentRegex +'$'
#                     print(f'Found regex for {dataType} - {regex}. \n Current regex is {currentRegex} .')
#                     foundRegxForCurrentColumn = True
#                     break
