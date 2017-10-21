from collections import Iterable, MutableMapping

import inspect
import re

from calculate.calculate import ManagedClass, ffi, lib

import calculate.exception as exception
import calculate.calculate as calculate

__all__ = [
    'Lexer',
    'Function',
    'Operator',
    'ConstantFactory',
    'FunctionFactory',
    'OperatorFactory'
]


class Lexer:

    _property = '''
        def {}(self):
            return self._constants["{}"]
    '''

    def __new__(cls):
        constants = {
            'left': ffi.string(lib.calculate_left_token).decode(),
            'right': ffi.string(lib.calculate_right_token).decode(),
            'decimal': ffi.string(lib.calculate_decimal_token).decode(),
            'separator': ffi.string(lib.calculate_separator_token).decode(),
            'number_regex':
                re.compile(ffi.string(lib.calculate_number_regex).decode()),
            'name_regex':
                re.compile(ffi.string(lib.calculate_name_regex).decode()),
            'symbol_regex':
                re.compile(ffi.string(lib.calculate_symbol_regex).decode()),
            'tokenizer_regex':
                re.compile(ffi.string(lib.calculate_tokenizer_regex).decode())
        }
        attrs = {}
        for name in constants.keys():
            calculate.build(
                cls._property,
                *(name, name),
                namespace=attrs
            )
            setattr(cls, name, property(attrs[name]))
        instance = super().__new__(cls)
        setattr(instance, '_constants', constants)
        return instance

    def __repr__(self):
        constants = repr({
            name: value
            for name, value in self._constants.items()
            if not hasattr(value, 'pattern')
        })
        return f"<{self.__class__.__name__} {constants}>"


class AbstractFunction(metaclass=ManagedClass):
    pass


class Function(AbstractFunction):

    def __init__(self, handler):
        super().__init__(handler)
        calculate.make_function(self)

    def __call__(self, *args):
        return self._evaluate(*args)

    def __repr__(self):
        return f"<{self.__class__.__name__} {{'arguments': {self.arguments}}}>"

    @property
    def arguments(self):
        return calculate.arguments(self._handler)


class Operator(metaclass=ManagedClass):

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} {{"
            f"'alias': '{self.alias}', "
            f"'precedence': {self.precedence}, "
            f"'associativity': {self.associativity}"
            f"}}>"
        )

    @property
    def alias(self):
        return calculate.alias(self._handler)

    @property
    def precedence(self):
        return calculate.precedence(self._handler)

    @property
    def associativity(self):
        return calculate.associativity(self._handler)

    @property
    def function(self):
        return Function(calculate.function(self._handler))


class SymbolFactory(MutableMapping):

    class LazyEvaluator:

        def __init__(self, parser, token, cls, kind):
            self._parser = parser
            self._token = token
            self._class = cls
            self._kind = kind

        def do(self):
            return self._class(
                getattr(calculate, f'get_{self._kind}')
                (self._parser, self._token)
            )

    def __init__(self, parser, cls, kind):
        calculate.check_parser(parser)
        self._parser = parser
        self._class = cls
        self._kind = kind
        self._factory = {
            token: self.LazyEvaluator(parser, token, cls, kind)
            for token in
            getattr(calculate, f'list_{self._kind}s')(self._parser).split(',')
            if token
        }

    def __getitem__(self, key):
        key = self.__keytransform__(key)
        if key in self._factory:
            return self._factory[key].do()
        else:
            return getattr(calculate, f'get_{self._kind}')(self._parser, key)

    def __setitem__(self, key, value):
        key = self.__keytransform__(key)
        getattr(calculate, f'set_{self._kind}')(self._parser, key, value)
        self._factory[key] = \
            self.LazyEvaluator(self._parser, key, self._class, self._kind)

    def __delitem__(self, key):
        key = self.__keytransform__(key)
        getattr(calculate, f'remove_{self._kind}')(self._parser, key)
        del self._factory[key]

    def __iter__(self):
        return iter(self._factory)

    def __len__(self):
        return len(self._factory)

    def __keytransform__(self, key):
        return key

    def __repr__(self):
        keys = repr(list(self._factory.keys()))
        return f"<{self.__class__.__name__} {keys}>"


class CallableFactory(SymbolFactory):

    def __init__(self, parser, cls, kind):
        super().__init__(parser, cls, kind)
        self._builtins = dict(self._factory)
        self._cache = {}

    def __setitem__(self, key, value):
        key = self.__keytransform__(key)
        if not isinstance(value, Iterable):
            value = [value]
        if key in self._builtins:
            del self._builtins[key]
        wrapper = self.Wrapper(self._parser, self._kind, key, *value)
        self._cache[key] = wrapper
        self._factory[key] = \
            self.LazyEvaluator(self._parser, key, self._class, self._kind)

    def __delitem__(self, key):
        key = self.__keytransform__(key)
        if key not in self._builtins:
            if key in self._cache:
                del self._cache[key]
        else:
            del self._builtins[key]
        super().__delitem__(key)

    @staticmethod
    def parameters(function):
        return (
            function.arguments if isinstance(function, Function) else
            len(inspect.signature(function).parameters)
        )

    def backup(self):
        return set(self._cache.values())


class ConstantFactory(SymbolFactory):

    def __init__(self, parser):
        super().__init__(parser, float, 'constant')


class FunctionFactory(CallableFactory):

    class Wrapper:

        def __init__(self, parser, kind, token, *args):
            if len(args) != 1:
                raise TypeError(
                    f"{self.__class__.__name__}() takes 1 positional argument"
                    f" but {len(args)} were given"
                )
            self._function = args[-1]
            self._handler = ffi.new_handle(self)

            arguments = CallableFactory.parameters(self._function)
            if not 0 < arguments < 4:
                raise exception.ArgumentsMismatch(
                    f'Arguments mismatch: 1 to 3 need arguments'
                    f'vs {arguments} provided'
                )

            getattr(calculate, f'set_callback{arguments}')(
                parser,
                token,
                self._handler,
                getattr(calculate.lib, f'_calculate_callback{arguments}')
            )

        @property
        def function(self):
            return self._function

    def __init__(self, parser):
        super().__init__(parser, Function, 'function')


class OperatorFactory(CallableFactory):

    class Wrapper:

        def __init__(self, parser, kind, token, *args):
            if len(args) != 4:
                raise TypeError(
                    f"{self.__class__.__name__}() takes 4 positional arguments"
                    f" but {len(args)} were given"
                )
            self._function = args[-1]
            self._handler = ffi.new_handle(self)

            arguments = CallableFactory.parameters(self._function)
            if arguments != 2:
                raise exception.ArgumentsMismatch(
                    f'2 needed arguments vs {arguments} provided'
                )

            calculate.set_operator_callback(
                parser,
                token,
                self._handler,
                *args[:-1],
                calculate.lib._calculate_callback2
            )

        @property
        def function(self):
            return self._function

    def __init__(self, parser):
        super().__init__(parser, Operator, 'operator')

    def __setitem__(self, key, value):
        key = self.__keytransform__(key)
        if isinstance(value, Operator):
            value = (
                value.alias,
                value.precedence,
                value.associativity,
                value.function
            )
        super().__setitem__(key, value)


Lexer = Lexer()
