"""
Plugin to extract tables from an invoice.
"""

import re
import logging as logger

DEFAULT_OPTIONS = {'field_separator': r'\s+', 'line_separator': r'\n'}


def extract(self, content, pdfStatus):
    """Try to extract tables from an invoice"""

    # **** do not reassign these variable. Because they hold reference to dict. values.
    warnings = pdfStatus['warnings']
    output = pdfStatus['output']

    for table in self['tables']:

        # First apply default options.
        plugin_settings = DEFAULT_OPTIONS.copy()
        plugin_settings.update(table)
        table = plugin_settings

        # Validate settings
        if 'start' not in table:
            warnings.append('Table start regex is missing in the template.')
            pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
            return
        if 'end' not in table:
            warnings.append('Table end regex is missing in the template.')
            pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
            return
        if 'body' not in table:
            warnings.append('Table body regex is missing in the template.')
            pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
            return

        start = re.search(table['start'], content)
        end = re.search(table['end'], content)

        if not start or not end:
            warnings.append(f'no table body found - start {start}, end {end}')
            pdfStatus['dbStatusCode'] = 330 if pdfStatus['dbStatusCode'] < 330 else pdfStatus['dbStatusCode']
            continue

        table_body = content[start.end(): end.start()]

        for line in re.split(table['line_separator'], table_body):
            # if the line has empty lines in it , skip them
            if not line.strip('').strip('\n') or not line:
                continue

            match = re.search(table['body'], line)
            if match:
                for field, value in match.groupdict().items():
                    # If a field name already exists, do not overwrite it
                    if field in output:
                        continue

                    if field.startswith('date') or field.endswith('date'):
                        output[field] = self.parse_date(value)
                        if not output[field]:
                            output[field] = value
                            warnings.append(f'Date parsing failed on date {value}')
                            pdfStatus['dbStatusCode'] = 300 if pdfStatus['dbStatusCode'] < 300 else pdfStatus['dbStatusCode']
                    elif field.startswith('amount'):
                        output[field] = self.parse_number(value)
                    else:
                        output[field] = value
            warnings.append(f'ignoring *{line}* because it doesn\'t match anything')
            pdfStatus['dbStatusCode'] = 320 if pdfStatus['dbStatusCode'] < 320 else pdfStatus['dbStatusCode']
