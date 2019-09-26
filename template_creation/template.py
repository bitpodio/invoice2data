
class Template:
    def __init__(self):
        self._issuer = ''
        self._keywords = []
        self._fields = {}
        self._tableStart = ""
        self._tableEnd = ""
        self._tableFirstLine = ""
        self._line = []
        self._types = {}
        self._line_group_header = ""
        self._remove_whitespace = "false"
        self._currency = "AUD"
        self._date_formats = []
        self._multiline = {
            "start": self._tableStart,
            "end": self._tableEnd,
            "first_line": self._tableFirstLine ,
            "line": self._line,
            "types": self._types,
            "line_group_header": self._line_group_header 
            }
        self.__options = {
            "remove_whitespace": self._remove_whitespace,
            "currency": self._currency,
            "date_formats": self._date_formats
        }

    @property
    def issuer(self):
        return self._issuer
    
    @issuer.setter
    def issure(self, value):
        if isinstance(value, str):
            self._issuer = value
        else:
            raise ValueError('Issuer must be a string.')
    
    @property
    def keywords(self):
        return self._keywords
    @keywords.setter
    def keywords(self, value):
        if isinstance(value, str):
            self._keywords.append(value)
        elif isinstance(value, list):
            self._keywords += value
        else:
            raise ValueError('Keywords must be a list or a string')

    @property
    def fields(self):
        return self._fields
    @fields.setter
    def fields(self, value):
        if isinstance(value, dict):
            self._fields.update(value)
        else:
            raise ValueError('Fields must be a dictionary.')

    
    @property
    def multiline(self):
        return self._multiline

    @property
    def options(self):
        return self.__options

    @property
    def tableStart(self):
        return self._tableStart
    
    @tableStart.setter
    def tableStart(self, value):
        if isinstance(value, str):
            self._tableStart = value
        else:
            raise ValueError('tableStart must be a string.')

    @property
    def tableEnd(self):
        return self._tableEnd
    @tableEnd.setter
    def tableEnd(self, value):
        if isinstance(value, str):
            self._tableEnd = value
        else:
            raise ValueError('tableEnd must be a string.')

    @property
    def tableFirstLine(self):
        return self._tableFirstLine
    @tableFirstLine.setter
    def tableFirstLine(self, value):
        if isinstance(value, str):
            self._tableFirstLine = value
        else:
            raise ValueError('tableFirstLine must be a string.')

    @property
    def line(self):
        return self._line
    @line.setter
    def line(self, value):
        if isinstance(value, str):
            self._line.append(value)
        elif isinstance(value, list):
            self._line += value
        else:
            raise ValueError('Line must be a list or a string')

    @property
    def types(self):
        return self._types
    @types.setter
    def types(self, value):
        if isinstance(value, dict):
            self._types.update(value)
        else:
            raise ValueError('Types must be a dictionary.')

    @property
    def line_group_header(self):
        return self._line_group_header
    @line_group_header.setter
    def line_group_header(self, value):
        if isinstance(value, str):
            self._line_group_header = value
        else:
            raise ValueError('line_group_header must be a string.')

    @property
    def remove_whitespace(self):
        return self._remove_whitespace
    @remove_whitespace.setter
    def remove_whitespace(self, value):
        if value in ["true", "True", True, "false", "False", False]:
            self._remove_whitespace = value
        else:
            raise ValueError('remove_whitespace must be a true/false value.')

    @property
    def currency (self):
        return self._currency 
    @currency.setter
    def currency (self, value):
        if isinstance(value, str):
            self._currency  = value
        else:
            raise ValueError('currency  must be a string.')

    @property
    def date_formats(self):
        return self._date_formats
    @date_formats.setter
    def date_formats(self, value):
        if isinstance(value, str):
            self._date_formats.append(value)
        elif isinstance(value, list):
            self._date_formats += value
        else:
            raise ValueError('date_formats must be a list or a string')