from collections import defaultdict
from enum import Enum, unique
from types import ModuleType, MethodType
from abc import ABCMeta, abstractmethod

import sys
import inspect
import textwrap
import re

from calculate._calculate import ffi, lib

import calculate.exception as exception


DEFAULT_BODY = '    result = self.lib.{original_name}({signature})'
THROW_BODY = '''
    with self.Error() as error:
        result = self.lib.{original_name}(error.handler, {signature})
'''

DEFAULT_STRING = 'self.lib.{original_name}({signature}, string, chars)'
THROW_STRING = '''
        with self.Error() as error:
            self.lib.{original_name}(error.handler, {signature}, string, chars)
'''
BODY = '''
    chars = 256
    while True:
        string = self.ffi.new(f"char[{{chars}}]")
        ...
        result = self.ffi.string(string).decode()
        if result and result == "*" * len(result):
            chars *= 2
        else:
            break
'''
STRING_BODY = BODY.replace('...', DEFAULT_STRING)
WHOLE_BODY = BODY.replace('...', THROW_STRING)

EVALUATE = '''
def _evaluate(self, {signature}):
    return lib._calculate_evaluate_{kind}(
        self._error._handler.handler,
        self._handler.handler,
        {argc},
        {arguments}
    )
'''

SPEC_REGEX = re.compile(
    r'^(?P<result>\w+(?:\s\w+)?(?:\s\*)?)(?:\s)?'
    r'_calculate_(?P<name>\w+)'
    r'\((?P<signature>.*)\);$'
)
HANDLER_REGEX = re.compile(r'struct calculate_(\w+)Handler \*')
POINTER_REGEX = re.compile(r'double\(\*\)\(.+\)')


@ffi.def_extern()
def _calculate_callback1(handler, x1):
    wrapper = ffi.from_handle(handler)
    return wrapper.function(x1)


@ffi.def_extern()
def _calculate_callback2(handler, x1, x2):
    wrapper = ffi.from_handle(handler)
    return wrapper.function(x1, x2)


@ffi.def_extern()
def _calculate_callback3(handler, x1, x2, x3):
    wrapper = ffi.from_handle(handler)
    return wrapper.function(x1, x2, x3)


@unique
class Symbol(Enum):
    LEFT = 0
    RIGHT = 1
    SEPARATOR = 2
    CONSTANT = 3
    FUNCTION = 4
    OPERATOR = 5


@unique
class Associativity(Enum):
    LEFT = 0
    RIGHT = 1
    BOTH = 2


class Handler:

    def __init__(self, handler, kind):
        self._handler = handler
        self._kind = kind
        self._free = getattr(calculate, f'free_{kind}')

    def __del__(self):
        self._free(self)

    def __repr__(self):
        return f"<{self.__class__.__name__} {{'kind': {self._kind.title()}}}>"

    @property
    def handler(self):
        return self._handler


class LibraryManager(ModuleType):

    def __new__(cls, name):
        instance = super().__new__(cls, name)
        setattr(instance, 'ffi', ffi)
        setattr(instance, 'lib', lib)

        for original_name in [
                name for name in dir(lib)
                if name.startswith('_calculate')
                and inspect.isbuiltin(getattr(lib, name))
        ]:
            method = getattr(lib, original_name)
            spec = inspect.getdoc(method).split('\n')[0]
            result, name, signature = re.match(SPEC_REGEX, spec).groups()
            signature = re.sub(POINTER_REGEX, 'void *', signature)

            throw = False
            if (
                    signature.startswith('struct calculate_Error') and
                    len(signature) > 31 and
                    name != 'message'
            ):
                signature, throw = (signature[31:], True)

            stringify = False
            if result == 'void' and signature.endswith('char *, size_t'):
                signature, stringify = (signature[:-16], True)
            handlingfy = re.match(HANDLER_REGEX, result)
            handlingfy = handlingfy.groups()[0].lower() if handlingfy else ''
            symbolify = bool(result.startswith('enum calculate_Symbol'))
            associativify = bool(result.startswith('enum calculate_Assoc'))

            signature = signature.split(', ')
            arguments = defaultdict(int)
            for i, arg in enumerate(signature):
                if arg.startswith('struct'):
                    signature[i] = f'h{arguments["handler"]}'
                    arguments['handler'] += 1
                elif arg.startswith('void'):
                    signature[i] = f'p{arguments["pointer"]}'
                    arguments['pointer'] += 1
                elif arg.startswith('char'):
                    signature[i] = f's{arguments["string"]}'
                    arguments['string'] += 1
                elif arg == 'size_t':
                    signature[i] = f'i{arguments["integer"]}'
                    arguments['integer'] += 1
                elif arg == 'double':
                    signature[i] = f'x{arguments["double"]}'
                    arguments['double'] += 1
                elif 'enum' in arg:
                    signature[i] = f'e{arguments["enum"]}'
                    arguments['enum'] += 1

            adapters = []
            for arg in signature:
                if arg.startswith('h'):
                    adapters.append(f'    {arg} = {arg}.handler')
                elif arg.startswith('s'):
                    adapters.append(f'    {arg} = {arg}.encode()')
                elif arg.startswith('e'):
                    adapters.append(f'    {arg} = {arg}.value')
            signature = ', '.join([arg for arg in signature if arg])

            header = f'def {name}(self, {signature}):'
            if stringify and throw:
                BODY = WHOLE_BODY.format(**locals())
            elif stringify:
                BODY = STRING_BODY.format(**locals())
            elif throw:
                BODY = THROW_BODY.format(**locals())
            else:
                BODY = DEFAULT_BODY.format(**locals())

            result = '    return {}(result{})'
            if handlingfy:
                result = result.format('Handler', f', "{handlingfy}"')
            elif associativify:
                result = result.format('Associativity', '')
            elif symbolify:
                result = result.format('Symbol', '')
            else:
                result = result.format('', '')

            cls.build(
                '\n'.join([header, *adapters, BODY, result]),
                namespace=instance.__dict__,
                instance=instance
            )
        return instance

    def _make(self, instance, kind, argc):
        signature = [f'x{i}' for i in range(argc)]
        arguments = signature + ['0.' for i in range(3 - argc)]
        signature, arguments = map(', '.join, (signature, arguments))
        setattr(instance, '_error', self.Error())
        self.build(
            EVALUATE.format(**locals()),
            namespace=instance.__dict__,
            instance=instance
        )

    def make_function(self, function):
        self._make(function, 'function', function.arguments)

    def make_expression(self, expression):
        self._make(expression, 'expression', len(expression.variables))

    @staticmethod
    def build(code, *args, **kwargs):
        namespace = kwargs['namespace']
        instance = kwargs.get('instance')
        names = set(namespace.keys())
        if args:
            code = code.format(*args)
        exec(textwrap.dedent(code), globals(), namespace)
        if instance is not None:
            name = (set(namespace.keys()) - names).pop()
            namespace[name] = MethodType(namespace[name], instance)


calculate = LibraryManager(__name__)


class ManagedClass(ABCMeta):

    _init = '''
        def __init__(self, handler):
            self._handler = handler
            if not calculate.check_{}(self._handler):
                raise ValueError('Invalid resource handler')
    '''

    def __new__(mcs, name, bases, attrs):
        if not bases:
            sub = name.replace('Abstract', '').lower()
            calculate.build(mcs._init, sub, namespace=attrs)
            if name.startswith('Abstract'):
                attrs['__init__'] = abstractmethod(attrs['__init__'])
        return super().__new__(mcs, name, bases, attrs)


class AbstractError(metaclass=ManagedClass):
    pass


class Error(AbstractError):

    def __init__(self):
        super().__init__(calculate.get_error())

    def __enter__(self):
        return self._handler

    def __exit__(self, *args):
        if args[0]:
            return False
        elif calculate.status(self._handler):
            exception.throw(calculate.message(self._handler))

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} {{"
            f"'status': {self.status}, "
            f"'message': '{self.message}'"
            f"}}>"
        )

    @property
    def status(self):
        return bool(calculate.status(self._handler))

    @property
    def message(self):
        return calculate.message(self._handler)


setattr(calculate, 'Symbol', Symbol)
setattr(calculate, 'Associativity', Associativity)
setattr(calculate, 'Handler', Handler)
setattr(calculate, 'ManagedClass', ManagedClass)
setattr(calculate, 'Error', Error)
sys.modules[__name__] = calculate
