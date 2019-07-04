"""
Plugin to extract multiple lines from an invoice.
Initial work and maintenance by Yogeshwar Singh
"""

import re
import logging as logger

DEFAULT_OPTIONS = {'field_separator': r'\s+', 'line_separator': r'\n'}


def extract(self, content, output):
    """Try to extract lines from the invoice"""

    # First apply default options.
    plugin_settings = DEFAULT_OPTIONS.copy()
    plugin_settings.update(self['multilines'])
    self['multilines'] = plugin_settings

    # Validate settings
    assert 'start' in self['multilines'], 'Multilines start regex missing'
    assert 'end' in self['multilines'], 'Multilines end regex missing'
    assert 'line' in self['multilines'], 'Multilines line regex missing'
    assert 'first_line' in self['multilines'], 'Multilines first_line regex missing'

    start = re.search(self['multilines']['start'], content)
    end = re.search(self['multilines']['end'], content)
    if not start or not end:
        logger.warning('no lines found - start %s, end %s', start, end)
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
            match = re.search(lineRegEx, line)
            if match:
                for field, value in match.groupdict().items():
                    current_row[field] = '%s%s%s' % (
                        current_row.get(field, ''),
                        current_row.get(field, '') and '\n' or '',
                        value.strip() if value else '',
                    )
                break
        if match:
            continue     
        logger.debug('ignoring *%s* because didn\'t find any match for the line', line)

    if current_row: # This for the last line in the table
        lines.append(current_row)

    types = self['multilines'].get('types', [])
    for row in lines:
        for name in row.keys():
            if name in types:
                row[name] = self.coerce_type(row[name], types[name])

    if lines:
        output['multilines'] = lines
