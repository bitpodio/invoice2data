import argparse
import os
import sys

input_mapping = {
    'pdftotext',
    'tesseract',
    'tesseract4',
    'pdfminer',
    'gvision',
}

output_mapping = {'csv', 'json', 'xml', 'none'}

settings = {}

def create_parser():
    """Returns argument parser """

    parser = argparse.ArgumentParser(
        description='Extract structured data from PDF files and save to CSV or JSON.'
    )

    parser.add_argument(
        '--input-reader',
        choices=input_mapping,
        default='pdftotext',
        help='Choose text extraction function. Default: pdftotext',
    )

    parser.add_argument(
        '--output-format',
        choices=output_mapping,
        default='json',
        help='Choose output format. Default: json',
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

def getSettings(args=None):
    # Parse args
    if settings:
        return settings
        
    if args is None:
            parser = create_parser()
            args = parser.parse_args()

    settings['templates'] = []
    # 1st arg is always the file path, 2nd argument could be --debug, that is why using condition > 2
    if not len(sys.argv) > 2: 
        settings['isK8sJob'] = True
        settings['outputModleApi'] = os.environ['outputModelAPI']
        settings['outputColumn'] = os.environ['outputColumn']
        settings['accessKeyId'] = os.environ['accessKeyId']
        settings['secretAccessKey'] = os.environ['secretAccessKey']
        settings['templateIds'] = os.environ['templateIds'].split(',')
        settings['pdfIds'] = os.environ['pdfId'].split(',')
        settings['inputReader'] = os.environ['inputReader'] if os.getenv('inputReader') else 'pdftotext'
        settings['logLevelDebug'] = True if os.getenv('logLevel') else False
        settings['template_folder'] = os.path.abspath(os.environ['templateFolder'] if 'templateFolder' in os.environ else 'downloads/templates')
        settings['pdf_folder'] = os.path.abspath(os.environ['pdfFolder'] if 'pdfFolder' in os.environ else 'downloads/pdfs')
        settings['include_built_in_templates'] =  'include_built_in_templates' in os.environ
        settings['input_files'] = []
    else:
        settings['isK8sJob'] = False
        assert args.template_folder, 'Please specify template folder using command line arg "--template-folder" or provide attachment ids for template in the env variable "templates"'
        assert args.input_files, 'Please specify input file location  using command line arg "--input-files" or provide attachment ids of the pdf in the env variable "pdfId"'
        settings['inputReader'] = args.input_reader
        settings['output_format'] = args.output_format
        settings['logLevelDebug'] = args.debug
        settings['input_files'] = args.input_files
        settings['template_folder'] = os.path.abspath(args.template_folder)
        settings['include_built_in_templates'] =  args.include_built_in_templates
        settings['outputFileName'] = args.output_name
    
    return settings