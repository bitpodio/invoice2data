#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import shutil
import os
from os.path import join
import logging
import json
logger = logging.getLogger(__name__)
if __package__ is None or __package__ == '':
    # uses current directory visibility
    from input import pdftotext
    from input import pdfminer_wrapper
    from input import tesseract
    from input import tesseract4
    from input import gvision

    from extract.loader import read_templates

    from output import to_csv
    from output import to_json
    from output import to_xml
else:
    # uses current package visibility
    from .input import pdftotext
    from .input import pdfminer_wrapper
    from .input import tesseract
    from .input import tesseract4
    from .input import gvision

    from invoice2data.extract.loader import read_templates

    from .output import to_csv
    from .output import to_json
    from .output import to_xml
try:
    envOutputModleApi = os.environ['outputModelAPI']
    envOutputColumn = os.environ['outputColumn']
    envTemplateIds = os.environ['templateIds'].split(',')
    envPdfIds = os.environ['pdfId'].split(',')
    if __package__ is None or __package__ == '':
        from output import to_model
        import file_transfer
    else:
        from .output import to_model
        from . import file_transfer
except KeyError as e:
    logger.warning(f'Warning: Envionment variable "{e.args[0]}" not found!')
    envOutputModleApi = None
    envOutputColumn = None
    envTemplateIds = None
    envPdfIds = None
    pass

input_mapping = {
    'pdftotext': pdftotext,
    'tesseract': tesseract,
    'tesseract4': tesseract4,
    'pdfminer': pdfminer_wrapper,
    'gvision': gvision,
}

output_mapping = {'csv': to_csv, 'json': to_json, 'xml': to_xml, 'none': None}

def get_parsed_data(templates, extracted_str, partiallyExtracted):    
    logger.debug('START pdftotext result ===========================')
    logger.debug(extracted_str)
    logger.debug('END pdftotext result =============================')

    if templates is None:
        templates = read_templates()
        
    logger.debug('Testing {} template files'.format(len(templates)))
    for t in templates:
        optimized_str = t.prepare_input(extracted_str)

        if t.matches_input(optimized_str):
            return t.extract(optimized_str, partiallyExtracted)

    return {}


def extract_data(invoicefile, templates=None, input_module=pdftotext):
    """Extracts structured data from PDF/image invoices.

    This function uses the text extracted from a PDF file or image and
    pre-defined regex templates to find structured data.

    Reads template if no template assigned
    Required fields are matches from templates

    Parameters
    ----------
    invoicefile : str
        path of electronic invoice file in PDF,JPEG,PNG (example: "/home/duskybomb/pdf/invoice.pdf")
    templates : list of instances of class `InvoiceTemplate`, optional
        Templates are loaded using `read_template` function in `loader.py`
    input_module : {'pdftotext', 'pdfminer', 'tesseract'}, optional
        library to be used to extract text from given `invoicefile`,

    Returns
    -------
    dict or False
        extracted and matched fields or False if no template matches

    Notes
    -----
    Import required `input_module` when using invoice2data as a library

    See Also
    --------
    read_template : Function where templates are loaded
    InvoiceTemplate : Class representing single template files that live as .yml files on the disk

    Examples
    --------
    When using `invoice2data` as an library

    >>> from invoice2data.input import pdftotext
    >>> extract_data("invoice2data/test/pdfs/oyo.pdf", None, pdftotext)
    {'issuer': 'OYO', 'amount': 1939.0, 'date': datetime.datetime(2017, 12, 31, 0, 0), 'invoice_number': 'IBZY2087',
     'currency': 'INR', 'desc': 'Invoice IBZY2087 from OYO'}

    """
    partiallyExtracted = False
    # TRY 1
    # extract data with given input_module
    extracted_str = input_module.to_text(invoicefile).decode('utf-8')
    parsed_data = get_parsed_data(templates, extracted_str, partiallyExtracted)

    if (parsed_data != {} and 'multilines' in parsed_data) or input_module != tesseract4:
        parsed_data['rawData'] = extracted_str
        return parsed_data
    logger.error('No template for %s.', invoicefile)

    # TRY 2
    if input_module == tesseract4:
        logger.debug('Retrying with psm value of 3.')
        extracted_str = input_module.to_text(invoicefile, psm='3').decode('utf-8')
        parsed_data = get_parsed_data(templates, extracted_str, partiallyExtracted)
        parsed_data['rawData'] = extracted_str
        return parsed_data
    


def create_parser():
    """Returns argument parser """

    parser = argparse.ArgumentParser(
        description='Extract structured data from PDF files and save to CSV or JSON.'
    )

    parser.add_argument(
        '--input-reader',
        choices=input_mapping.keys(),
        default='tesseract4',
        help='Choose text extraction function. Default: tesseract4',
    )

    parser.add_argument(
        '--output-format',
        choices=output_mapping.keys(),
        default='json',
        help='Choose output format. Default: json',
    )

    parser.add_argument(
        '--output-date-format',
        dest='output_date_format',
        default="%Y-%m-%d",
        help='Choose output date format. Default: %Y-%m-%d (ISO 8601 Date)',
    )

    parser.add_argument(
        '--output-name',
        '-o',
        dest='output_name',
        help='Custom path+name for output file. Extension is added based on chosen format.',
    )

    parser.add_argument(
        '--debug', dest='debug', action='store_true', help='Enable debug information.'
    )

    parser.add_argument(
        '--copy', '-c', dest='copy', help='Copy and rename processed PDFs to specified folder.'
    )

    parser.add_argument(
        '--move', '-m', dest='move', help='Move and rename processed PDFs to specified folder.'
    )

    parser.add_argument(
        '--filename-format',
        dest='filename',
        default="{date} {invoice_number} {desc}.pdf",
        help='Filename format to use when moving or copying processed PDFs.'
             'Default: "{date} {invoice_number} {desc}.pdf"',
    )

    parser.add_argument(
        '--template-folder',
        '-t',
        dest='template_folder',
        help='Folder containing invoice templates in yml file. Always adds built-in templates.',
    )

    parser.add_argument(
        '--include-built-in-templates',
        dest='include_built_in_templates',
        help='Include built-in templates.',
        action="store_true",
    )

    parser.add_argument(
        '--input-files', 
        required=False, 
        type=argparse.FileType('r'), 
        nargs='+', 
        help='File or directory to analyze.'
    )
    args = parser.parse_args()
    if args.input_files and not args.output_name:
        parser.error('You must set arg --output-name with arg --input-files')
    return parser


def main(args=None):
    """Take folder or single file and analyze each."""
    if args is None:
        parser = create_parser()
        args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    global envOutputModleApi
    global envOutputColumn
    global envTemplateIds
    global envPdfIds
    logger.debug(f'template_folder : {args.template_folder},  envTemplateIds: {envTemplateIds}, input_files: {args.input_files}, envPdfId: {envPdfIds}')
    assert args.template_folder or envTemplateIds, 'Please specify template folder using command line arg "--template-folder" \
or provide attachment ids for template in the env variable "templates"'
    assert args.input_files or envPdfIds, 'Please specify input file location  using command line arg "--input-files" \
or provide attachment ids of the pdf in the env variable "pdfId"'
    

    input_module = input_mapping[args.input_reader]
    output_module = output_mapping[args.output_format]

    templates = []
    template_folder = ''
    # Load templates from external folder if set.
    if args.template_folder:
        template_folder = os.path.abspath(args.template_folder)
    elif len(envTemplateIds) != 0:
        logger.debug('******* Download Templates ********')
        template_folder = os.path.abspath('downloads/templates')
        for templateId in envTemplateIds:
            file_transfer.downloadFile(templateId, template_folder, '.yml')        
    
    if template_folder:
        templates += read_templates(template_folder)

    # Load internal templates, if enabled.
    if args.include_built_in_templates:
        templates += read_templates()
    
    
    if args.input_files:
        input_files = args.input_files
    if envPdfIds:
        # download PDF
        logger.debug('******* Download PDFs ********')
        input_files = []
        for pdfId in envPdfIds:
            downloadFolder = os.path.abspath('downloads/pdfs') 
            downloaded_file = file_transfer.downloadFile(pdfId, downloadFolder, '.pdf')
            try:
                input_files.append(open(downloaded_file, 'r'))
            except OSError as e:
                logger.fatal('Unable to open downloaded file', exc_info=True)

    # process PDFs
    outputs = []
    for f in input_files:
        res = extract_data(f.name, templates=templates, input_module=input_module)
        if res:
            logger.info(res)
            outputs.append(res)
            if args.copy:
                filename = args.filename.format(
                    date=res['date'].strftime('%Y-%m-%d'),
                    invoice_number=res['invoice_number'],
                    desc=res['desc'],
                )
                shutil.copyfile(f.name, join(args.copy, filename))
            if args.move:
                filename = args.filename.format(
                    date=res['date'].strftime('%Y-%m-%d'),
                    invoice_number=res['invoice_number'],
                    desc=res['desc'],
                )
                shutil.move(f.name, join(args.move, filename))
        f.close()

    if envOutputModleApi and envOutputColumn:
        for output in outputs:
            to_model.write_to_model(outputs, envOutputModleApi, envOutputColumn, args.output_date_format)
    elif output_module is not None:
        output_module.write_to_file(outputs, args.output_name, args.output_date_format)



if __name__ == '__main__':
    main()
