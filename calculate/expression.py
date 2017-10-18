from collections import Iterable, Iterator

from calculate.calculate import ManagedClass

import calculate.exception as exception
import calculate.calculate as calculate

__all__ = ['Expression']


class AbstractExpression(metaclass=ManagedClass):
    pass


Iterable.register(AbstractExpression)


class Expression(AbstractExpression):

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
            return (
                f"<{self.__class__.__name__} {{"
                f"'branches': {self._branches}"
                f"}}>"
            )

    def __init__(self, handler, cache):
        super().__init__(handler)
        self._cache = cache

    def __call__(self, *args):
        needed, provided = (len(self.variables), len(args))
        if not provided:
            raise exception.ArgumentsMismatch(
                f'at least 1 needed argument'
            )
        elif provided > 3:
            raise exception.ArgumentsMismatch(
                f'{needed} needed argument{"s,".split(",")[int(needed == 1)]} '
                f'vs {provided} provided'
            )
        x0 = args[0]
        x1 = args[1] if provided > 1 else 0.
        x2 = args[2] if provided > 2 else 0.
        return calculate.evaluate_expression(
            self._handler,
            provided,
            *(x0, x1, x2)
        )

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
        if index >= len(self):
            raise IndexError(f'{self.__class__.__name__} index out of range')
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
        return (
            f"<{self.__class__.__name__} {{"
            f"'expression': '{self.infix}', "
            f"'variables': {repr(self.variables)}"
            f"}}>"
        )

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
