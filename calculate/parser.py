from calculate.calculate import ManagedClass
from calculate.symbol import ConstantFactory, FunctionFactory, OperatorFactory
from calculate.expression import Expression

import calculate.calculate as calculate


__all__ = ['Parser', 'DefaultParser']


class BaseParser(ManagedClass):

    def __init__(self, handler):
        super().__init__(handler)
        self._constants = ConstantFactory(self._handler)
        self._functions = FunctionFactory(self._handler)
        self._operators = OperatorFactory(self._handler)

    def __repr__(self):
        name = self.__class__.__name__
        return (
            f"<{name} {{"
            f"'constants': {len(self.constants)}, "
            f"'functions': {len(self.functions)}, "
            f"'operators': {len(self.operators)}"
            f"}}>"
        )

    def _backup(self):
        cache = set()
        cache |= self._functions.backup()
        cache |= self._operators.backup()
        return cache

    @property
    def constants(self):
        return self._constants

    @property
    def functions(self):
        return self._functions

    @property
    def operators(self):
        return self._operators

    def cast(self, expression):
        return calculate.cast(self._handler, expression)

    def to_string(self, value):
        return calculate.to_string(self._handler, value)

    def create_node(self, token, nodes=None, variables=None):
        nodes = [] if nodes is None else nodes
        variables = [] if variables is None else variables
        expressions = calculate.get_nodes()
        for index, node in enumerate(nodes):
            expressions = calculate.insert_node(expressions, node._handler)
        return Expression(
            calculate.create_node(
                self._handler,
                token,
                expressions,
                ','.join(variables)
            ),
            self._backup()
        )

    def from_value(self, value):
        return Expression(
            calculate.from_value(self._handler, value),
            self._backup()
        )

    def from_infix(self, expression, variables=None):
        variables = [] if variables is None else variables
        return Expression(
            calculate.from_infix(
                self._handler,
                expression,
                ','.join(variables)
            ),
            self._backup()
        )

    def from_postfix(self, expression, variables=None):
        variables = [] if variables is None else variables
        return Expression(
            calculate.from_postfix(
                self._handler,
                expression,
                ','.join(variables)
            ),
            self._backup()
        )

    def parse(self, expression):
        return Expression(
            calculate.parse(self._handler, expression),
            self._backup()
        )

    def variables(self, node, variables):
        return Expression(
            calculate.new_variables(
                self._handler,
                node._handler,
                ','.join(variables)
            ),
            self._backup()
        )

    def optimize(self, node):
        return Expression(
            calculate.optimize(self._handler, node._handler),
            self._backup()
        )

    def replace(self, one, branch, another, variables=None):
        variables = one.variables() if variables is None else variables
        return Expression(
            calculate.replace(
                self._handler,
                *(one._handler, branch, another._handler),
                ','.join(variables)
            ),
            self._backup()
        )

    def substitute(self, node, variable, value):
        return Expression(
            calculate.substitute(
                self._handler,
                node._handler,
                variable,
                value
            ),
            self._backup()
        )


class Parser(BaseParser):

    def __init__(self):
        super().__init__(calculate.get_parser())


class DefaultParser(BaseParser):

    def __init__(self):
        super().__init__(calculate.get_default_parser())
