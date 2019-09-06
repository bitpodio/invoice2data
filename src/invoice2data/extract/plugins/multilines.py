"""
Plugin to extract multiple lines from an invoice.
Initial work and maintenance by Yogeshwar Singh
"""

import re
import logging as logger

DEFAULT_OPTIONS = {'field_separator': r'\s+', 'line_separator': r'\n'}


def extract(self, content, pdfStatus):
    """Try to extract lines from the invoice"""

    # First apply default options.
    plugin_settings = DEFAULT_OPTIONS.copy()
    plugin_settings.update(self['multilines'])
    self['multilines'] = plugin_settings

    # **** do not reassign these variable. Because they hold reference to dict. values.
    warnings = pdfStatus['warnings']
    output = pdfStatus['output']

    # Validate settings
    if 'start' not in self['multilines']:
        warnings.append('Multilines start regex is missing in the template.')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return
    if 'end' not in self['multilines']:
        warnings.append('Multilines end regex is missing in the template.')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return
    if 'first_line' not in self['multilines']:
        warnings.append('Multilines first_line regex is missing in the template.')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return
    if 'line' not in self['multilines']:
        logger.warning('Multilines line regex is missing in the template.')
    
    start = re.search(self['multilines']['start'], content)
    end = re.search(self['multilines']['end'], content)
    if not start or not end:
        warnings.append(f'no lines found - start {start}, end {end}.')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return
    content = content[start.end(): end.start()]
    lines = []
    current_row = {}
    for line in re.split(self['multilines']['line_separator'], content):
        # if the line has empty lines in it , skip them
        if not line.strip('').strip('\n') or not line:
            continue

        # match the first line
        match = re.search(self['multilines']['first_line'], line)
        if match:
            if current_row:
                lines.append(current_row) # commit the last row
            current_row = {} #start with a new row
            current_row = {
                field: value.strip() if value else ''
                for field, value in match.groupdict().items()
            }
            continue
        
        # match the other lines
        for lineRegEx in self['multilines']['line']:
            if not lineRegEx:
                continue
            match = re.search(lineRegEx, line)
            if match:
                for field, value in match.groupdict().items():
                    current_row[field] = '%s%s%s' % (
                        current_row.get(field, ''),
                        current_row.get(field, '') and ' ' or '',
                        value.strip() if value else '',
                    )
                break
        if match:
            continue     
        warnings.append(f'ignoring *{line}* because didn\'t find any match for the line')
        pdfStatus['dbStatusCode'] = 320 if pdfStatus['dbStatusCode'] < 320 else pdfStatus['dbStatusCode']

    if current_row: # This for the last line in the table
        lines.append(current_row)

    types = self['multilines'].get('types', [])
    for row in lines:
        for name in row.keys():
            if name in types:
                try:
                    row[name] = self.coerce_type(row[name], types[name])
                except AssertionError:
                    warnings.append(f'Unable to convert {name}, value - {row[name]} in type/format {types[name]}.')
                    pdfStatus['dbStatusCode'] = 300 if pdfStatus['dbStatusCode'] < 300 else pdfStatus['dbStatusCode'] 

    if lines:
        output['lines'] = lines
