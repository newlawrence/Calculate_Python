import re

from calculate.calculate import ffi, lib

__all__ = ['Lexer']


class Lexer:

    def __repr__(self):
        name = self.__class__.__name__
        constants = repr({
            name: getattr(self, name)
            for name in ['left', 'right', 'decimal', 'separator']
        })
        return f"<{name} {constants}>"

    @property
    def left(self):
        return ffi.string(lib.calculate_left_token()).decode()

    @property
    def right(self):
        return ffi.string(lib.calculate_right_token()).decode()

    @property
    def decimal(self):
        return ffi.string(lib.calculate_decimal_token()).decode()

    @property
    def separator(self):
        return ffi.string(lib.calculate_separator_token()).decode()

    @property
    def number_regex(self):
        return re.compile(ffi.string(lib.calculate_number_regex()).decode())

    @property
    def name_regex(self):
        return re.compile(ffi.string(lib.calculate_name_regex()).decode())

    @property
    def symbol_regex(self):
        return re.compile(ffi.string(lib.calculate_symbol_regex()).decode())

    @property
    def tokenizer_regex(self):
        return re.compile(ffi.string(lib.calculate_tokenizer_regex()).decode())


Lexer = Lexer()
