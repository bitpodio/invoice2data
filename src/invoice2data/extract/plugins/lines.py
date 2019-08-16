"""
Plugin to extract individual lines from an invoice.

Initial work and maintenance by Holger Brunn @hbrunn
"""

import re
import logging as logger

DEFAULT_OPTIONS = {'field_separator': r'\s+', 'line_separator': r'\n'}


def extract(self, content, pdfStatus):
    """Try to extract lines from the invoice"""

    # First apply default options.
    plugin_settings = DEFAULT_OPTIONS.copy()
    plugin_settings.update(self['lines'])
    self['lines'] = plugin_settings

    # **** do not reassign these variable. Because they hold reference to dict. values.
    warnings = pdfStatus['warnings']
    output = pdfStatus['output']
    
    # Validate settings
    if 'start' not in self['lines']:
        warnings.append('Lines start regex is missing in the template.')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return
    if 'end' not in self['lines']:
        warnings.append('Lines end regex is missing in the template.')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return
    if 'line' not in self['lines']:
        warnings.append('Lines regex is missing in the template.')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return

    start = re.search(self['lines']['start'], content)
    end = re.search(self['lines']['end'], content)
    if not start or not end:
        warnings.append(f'No lines found - start {start}, end {end}')
        pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
        return
    content = content[start.end(): end.start()]
    lines = []
    current_row = {}
    if 'first_line' not in self['lines'] and 'last_line' not in self['lines']:
        self['lines']['first_line'] = self['lines']['line']
    for line in re.split(self['lines']['line_separator'], content):
        # if the line has empty lines in it , skip them
        if not line.strip('').strip('\n') or not line:
            continue
        if 'first_line' in self['lines']:
            match = re.search(self['lines']['first_line'], line)
            if match:
                if 'last_line' not in self['lines']:
                    if current_row:
                        lines.append(current_row)
                    current_row = {}
                if current_row:
                    lines.append(current_row)
                current_row = {
                    field: value.strip() if value else ''
                    for field, value in match.groupdict().items()
                }
                continue
        if 'last_line' in self['lines']:
            match = re.search(self['lines']['last_line'], line)
            if match:
                for field, value in match.groupdict().items():
                    current_row[field] = '%s%s%s' % (
                        current_row.get(field, ''),
                        current_row.get(field, '') and '\n' or '',
                        value.strip() if value else '',
                    )
                if current_row:
                    lines.append(current_row)
                current_row = {}
                continue
        match = re.search(self['lines']['line'], line)
        if match:
            for field, value in match.groupdict().items():
                current_row[field] = '%s%s%s' % (
                    current_row.get(field, ''),
                    current_row.get(field, '') and '\n' or '',
                    value.strip() if value else '',
                )
            continue
        warnings.append(f'ignoring *{line}* because it doesn\'t match anything')
        pdfStatus['dbStatusCode'] = 320 if pdfStatus['dbStatusCode'] < 320 else pdfStatus['dbStatusCode'] 
    if current_row:
        lines.append(current_row)

    types = self['lines'].get('types', [])
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
