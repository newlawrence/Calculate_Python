from collections import Iterable, Iterator
from types import MethodType

import functools

from calculate.calculate import ManagedClass

import calculate.calculate as calculate

__all__ = ['Expression']


class Expression(ManagedClass):

    class ExpressionIterator(Iterator):

        def __init__(self, nodes, branches, cache):
            self._nodes = nodes
            self._branches = branches
            self._branch = 0
            self._cache = cache

        def __next__(self):
            if self._branch == self._branches:
                raise StopIteration
            expression = Expression(
                calculate.get_node(self._nodes, self._branch),
                self._cache
            )
            self._branch += 1
            return expression

        def __repr__(self):
            name = self.__class__.__name__
            return (
                f"<{name} {{"
                f"'branch': {self._branch}, "
                f"'branches': {self._branches}"
                f"}}>"
            )

    def __init__(self, handler, cache):
        super().__init__(handler)
        self._error = calculate.Error()
        self._cache = cache

        evaluate = {
            0: lambda self:
                calculate.evaluate_expression(self._handler, 0, 0., 0., 0.),
            1: lambda self, x0:
                calculate.evaluate_expression(self._handler, 1, x0, 0., 0.),
            2: lambda self, x0, x1:
                calculate.evaluate_expression(self._handler, 2, x0, x1, 0.),
            3: lambda self, x0, x1, x2:
                calculate.evaluate_expression(self._handler, 3, x0, x1, x2)
        }[len(self.variables)]
        evaluate = MethodType(functools.wraps(self._evaluate)(evaluate), self)
        setattr(self, '_evaluate', evaluate)

    def __call__(self, *args):
        return self._evaluate(*args)

    def __float__(self):
        return calculate.evaluate_expression(self._handler, 0, 0., 0., 0.)

    def __hash__(self):
        return calculate.hash(self._handler)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            bool(calculate.equal(self._handler, other._handler))
        )

    def __len__(self):
        return calculate.branches(self._handler)

    def __getitem__(self, index):
        name = self.__class__.__name__
        if index >= len(self):
            raise IndexError(f'{name} index out of range')
        return Expression(
            calculate.get_node(calculate.nodes(self._handler), index),
            self._cache
        )

    def __iter__(self):
        return self.ExpressionIterator(
            calculate.nodes(self._handler),
            len(self),
            self._cache
        )

    def __repr__(self):
        name = self.__class__.__name__
        return (
            f"<{name} {{"
            f"'expression': '{self.infix}', "
            f"'variables': {repr(self.variables)}"
            f"}}>"
        )

    def _evaluate(self):
        pass

    @property
    def token(self):
        return calculate.token(self._handler)

    @property
    def symbol(self):
        return calculate.symbol(self._handler)

    @property
    def infix(self):
        return calculate.infix(self._handler)

    @property
    def postfix(self):
        return calculate.postfix(self._handler)

    @property
    def variables(self):
        variables = calculate.variables(self._handler)
        return variables.split(',') if variables else []


Iterable.register(Expression)
