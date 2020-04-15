#!/bin/sh
from template_creator import TemplateCreator
import logging
import yaml
import sys

logger=logging.getLogger('__main__') 
#Setting the threshold of logger to DEBUG 
logging.basicConfig(level=logging.DEBUG) 

def main():
    templateCreator = TemplateCreator()
    # Header Selection Testes
    # 1. /Developer/bitpod/pythonProject/mountedLocation/pdfs/Privider_Invoice_Samples/Demo_Samples/Cerebral Palsy Alliance Invoice 237493.txt
    # 2. /Developer/bitpod/pythonProject/mountedLocation/pdfs/Privider_Invoice_Samples/PROV003887_Hallmark Workplace Solutions/181205_Admin.pdf.txt
    # 3. /Developer/bitpod/pythonProject/mountedLocation/pdfs/Privider_Invoice_Samples/Demo_Samples/Invoice164786.txt
    # 4. /Developer/bitpod/pythonProject/mountedLocation/pdfs/Privider_Invoice_Samples/PROV001365_Kids First Occupational Therapy/Invoice INV-14228_Admin.pdf.txt
    if len(sys.argv)>1:
        filePath = sys.argv[1]
        logger.warn(" Test - "+filePath.split('.')[0])
        outputFile = filePath.split('.')[0] + '.yml'
    else:
        filePath = '/Developer/OCR Tests/Invoice INV-86187.txt'
        outputFile = '/Developer/OCR Tests/Invoice INV-86187.yml'
    fileText = templateCreator.readFile(filePath)
    headerRegexYmal = templateCreator.readYML('/Developer/bitpod/invoice2data/playground/db.yml')
    tableRegexYmal = templateCreator.readYML('/Developer/bitpod/invoice2data/playground/tabledb.yml')

    templateCreator.fileText = fileText
    templateCreator.nonTableValueRegexes = headerRegexYmal
    templateCreator._tableValueRegexes = tableRegexYmal
    templateCreator._startLineRegexes = tableRegexYmal['Table_Start']
    templateCreator._endLineRegexes = tableRegexYmal['Table_End']
    
    ######## TO BE REMOVED
    del tableRegexYmal['Table_Start']
    del tableRegexYmal['Table_End']
    ######## 

    (finalHeaderTuple, finalHeaderArr) = templateCreator.findTableHeader()

    templateCreator.prepareRegexForNonTableValue()
    
    possibleColumnTypes = templateCreator.getColumnTypes(finalHeaderArr)

    tableMatrix = templateCreator.getTableMatrix(finalHeaderTuple, possibleColumnTypes)

    template = templateCreator.createTemplate(tableMatrix, possibleColumnTypes)

    with open(outputFile, 'w+') as outfile:
        yaml.dump(template, outfile)

if __name__ == "__main__":
    main()