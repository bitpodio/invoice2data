"""
This module abstracts templates for invoice providers.

Templates are initially read from .yml files and then kept as class.
"""

import re
import dateparser
from unidecode import unidecode
import logging as logger
from collections import OrderedDict
from .plugins import lines, tables, multilines

OPTIONS_DEFAULT = {
    'remove_whitespace': False,
    'remove_accents': False,
    'lowercase': False,
    'currency': 'EUR',
    'date_formats': [],
    'output_date_format': '%Y-%m-%d',
    'languages': [],
    'decimal_separator': '.',
    'replace': [],  # example: see templates/fr/fr.free.mobile.yml
}

PLUGIN_MAPPING = {'lines': lines, 'tables': tables, 'multilines': multilines}


class InvoiceTemplate(OrderedDict):
    """
    Represents single template files that live as .yml files on the disk.

    Methods
    -------
    prepare_input(extracted_str)
        Input raw string and do transformations, as set in template file.
    matches_input(optimized_str)
        See if string matches keywords set in template file
    parse_number(value)
        Parse number, remove decimal separator and add other options
    parse_date(value)
        Parses date and returns date after parsing
    coerce_type(value, target_type)
        change type of values
    extract(optimized_str)
        Given a template file and a string, extract matching data fields.
    """

    def __init__(self, *args, **kwargs):
        super(InvoiceTemplate, self).__init__(*args, **kwargs)

        # Merge template-specific options with defaults
        self.options = OPTIONS_DEFAULT.copy()

        for lang in self.options['languages']:
            assert len(lang) == 2, 'lang code must have 2 letters'

        if 'options' in self:
            self.options.update(self['options'])

        # Set issuer, if it doesn't exist.
        if 'issuer' not in self.keys() and len(self['keywords']) > 0:
            self['issuer'] = self['keywords'][0]

    def prepare_input(self, extracted_str):
        """
        Input raw string and do transformations, as set in template file.
        """

        # Remove withspace
        if self.options['remove_whitespace']:
            optimized_str = re.sub(' +', '', extracted_str)
        else:
            optimized_str = extracted_str

        # Remove accents
        if self.options['remove_accents']:
            optimized_str = unidecode(optimized_str)

        # convert to lower case
        if self.options['lowercase']:
            optimized_str = optimized_str.lower()

        # specific replace
        for replace in self.options['replace']:
            assert len(replace) == 2, 'A replace should be a list of 2 items'
            optimized_str = optimized_str.replace(replace[0], replace[1])

        return optimized_str

    def matches_input(self, optimized_str):
        """See if string matches keywords set in template file"""
        if len(self['keywords']) == 0:
            logger.debug('No keywords are specified. Will try all templates.')
            return True
        elif all([keyword in optimized_str for keyword in self['keywords']]):
            logger.debug('Matched template %s', self['template_name'])
            return True

    def parse_number(self, value):
        assert (
            value.count(self.options['decimal_separator']) < 2
        ), 'Decimal separator cannot be present several times'
        # replace decimal separator by a |
        amount_pipe = value.replace(self.options['decimal_separator'], '|')
        # remove all possible thousands separators
        amount_pipe_no_thousand_sep = re.sub(r'[.,\s]', '', amount_pipe)
        # put dot as decimal sep
        return float(amount_pipe_no_thousand_sep.replace('|', '.'))

    def parse_date(self, value):
        """Parses date and returns date after parsing"""
        res = dateparser.parse(
            value, date_formats=self.options['date_formats'], languages=self.options['languages']
        )
        stringDate = res.strftime(self.options['output_date_format'])
        logger.debug("result of date parsing=%s", stringDate)
        return stringDate

    def coerce_type(self, value, target_type):
        if target_type == 'int':
            if not value.strip():
                return 0
            return int(self.parse_number(value))
        elif target_type == 'float':
            if not value.strip():
                return 0.0
            return float(self.parse_number(value))
        elif target_type == 'date':
            return self.parse_date(value)
        assert False, 'Unknown type'

    def extract(self, optimized_str):
        """
        Given a template file and a string, extract matching data fields.
        """
        #status of PDF processing
        logger.debug('START optimized_str ========================')
        logger.debug(optimized_str)
        logger.debug('END optimized_str ==========================')
        logger.debug(
            'Date parsing: languages=%s date_formats=%s',
            self.options['languages'],
            self.options['date_formats'],
        )
        logger.debug('Float parsing: decimal separator=%s', self.options['decimal_separator'])
        logger.debug("keywords=%s", self['keywords'])
        logger.debug(self.options)

        # create references for each 
        # do not reassign these variable. Because they hold reference to dict. values.
        pdfStatus = {'dbStatusCode':200, 'warnings': [], 'output': {}}
        warnings = pdfStatus['warnings']
        output = pdfStatus['output']   

        # Try to find data for each field.
        output['issuer'] = self['issuer']

        for k, v in self['fields'].items():
            if k.startswith('static_'):
                logger.debug("field=%s | static value=%s", k, v)
                output[k.replace('static_', '')] = v
            else:
                logger.debug("field=%s | regexp=%s", k, v)

                sum_field = False
                if k.startswith('sum_amount') and type(v) is list:
                    k = k[4:]  # remove 'sum_' prefix
                    sum_field = True
                # Fields can have multiple expressions
                if type(v) is list:
                    res_find = []
                    for v_option in v:
                        res_val = re.findall(v_option, optimized_str)
                        if res_val:
                            if sum_field:
                                res_find += res_val
                            else:
                                res_find.extend(res_val)
                else:
                    res_find = re.findall(v, optimized_str)
                if res_find:
                    logger.debug("res_find=%s", res_find)
                    if k.startswith('date') or k.endswith('date'):
                        output[k] = self.parse_date(res_find[0])
                        if not output[k]:
                            warnings.append(f'Date parsing failed on date {res_find[0]}')
                            pdfStatus['dbStatusCode'] = 300 if pdfStatus['dbStatusCode'] <300 else pdfStatus['dbStatusCode']
                            output[k] = res_find[0]
                    elif k.startswith('amount'):
                        if sum_field:
                            output[k] = 0
                            for amount_to_parse in res_find:
                                output[k] += self.parse_number(amount_to_parse)
                        else:
                            output[k] = self.parse_number(res_find[0])
                    else:
                        res_find = list(set(res_find))
                        if len(res_find) == 1:
                            output[k] = res_find[0]
                        else:
                            output[k] = res_find
                else:
                    pdfStatus['dbStatusCode'] = 310 if pdfStatus['dbStatusCode'] <310 else pdfStatus['dbStatusCode']
                    warnings.append(f'regexp for field for "{k}" didn\'t match')

        output['currency'] = self.options['currency']

        # Run plugins:
        for plugin_keyword, plugin_func in PLUGIN_MAPPING.items():
            if plugin_keyword in self.keys():
                plugin_func.extract(self, optimized_str, pdfStatus)

        # If required fields were found, return output, else log error.
        required_fields = []
        if 'required_fields' in self.keys():
            for v in self['required_fields']:
                required_fields.append(v)

        if set(required_fields).issubset(output.keys()):
            output['desc'] = 'Invoice from %s' % (self['issuer'])
            logger.debug(output)
            return pdfStatus
        else:
            fields = list(set(output.keys()))
            warnings.append(f'Unable to match all required fields. \n \
                The required fields are: {required_fields}. \n \
                Output contains the following fields: {fields}.')
            return pdfStatus 
