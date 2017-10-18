from types import ModuleType

import sys


def init(self, message=None):
    super(self.__class__, self).__init__(message if message else self._message)


class BaseError(Exception):

    _message = ''

    def __init__(self, message=None):
        super().__init__(message if message else 'Unexpected error')

    @classmethod
    def throw(cls, message):
        if message.startswith(cls._message):
            if message:
                raise cls(message.split(': ')[-1])
            else:
                raise cls()


class ExceptionManager(ModuleType):

    _exceptions = {
        'BadCast': 'Bad cast',
        'ArgumentsMismatch': 'Arguments mismatch',
        'EmptyExpression': 'Empty expression',
        'ParenthesisMismatch': 'Parenthesis mismatch',
        'RepeatedSymbol': 'Repeated symbol',
        'SyntaxError': 'Syntax error',
        'UndefinedSymbol': 'Undefined symbol',
        'UnsuitableName': 'Unsuitable symbol name',
        'UnusedSymbol': 'Unused symbol'
    }

    def __new__(cls, name):
        instance = super().__new__(cls, name)
        for name, message in cls._exceptions.items():
            exception = type(
                name,
                (BaseError,),
                {'__init__': init, '_message': message}
            )
            setattr(instance, name, exception)
            cls._exceptions[name] = exception
        setattr(instance, 'BaseError', BaseError)
        cls._exceptions['BaseError'] = BaseError
        return instance

    @classmethod
    def throw(cls, message):
        for exception in cls._exceptions.values():
            exception.throw(message)


sys.modules[__name__] = ExceptionManager(__name__)
