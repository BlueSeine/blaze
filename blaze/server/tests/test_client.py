from __future__ import absolute_import, division, print_function

import pytest
pytest.importorskip('flask')

from pandas import DataFrame
from blaze import compute, by, into, discover
from blaze import data as bz_data
from blaze.expr import Expr, symbol, Field
from blaze.dispatch import dispatch
from blaze.server import Server
from blaze.server.client import Client


df = DataFrame([['Alice', 100], ['Bob', 200]],
               columns=['name', 'amount'])

df2 = DataFrame([['Charlie', 100], ['Dan', 200]],
                columns=['name', 'amount'])

tdata = {'accounts': df, 'accounts2': df}

server = Server(tdata)

test = server.app.test_client()

from blaze.server import client
client.requests = test # OMG monkey patching


def test_client():
    c = Client('localhost:6363')
    assert str(discover(c)) == str(discover(tdata))

    t = symbol('t', discover(c))
    expr = t.accounts.amount.sum()

    assert compute(expr, c) == 300
    assert 'name' in t.accounts.fields
    assert isinstance(t.accounts.name, Field)
    assert compute(t.accounts.name, c) == ['Alice', 'Bob']


def test_expr_client_interactive():
    c = Client('localhost:6363')
    t = bz_data(c)

    assert compute(t.accounts.name) == ['Alice', 'Bob']
    assert (into(set, compute(by(t.accounts.name, min=t.accounts.amount.min(),
                                                  max=t.accounts.amount.max())))
            == set([('Alice', 100, 100), ('Bob', 200, 200)]))


def test_compute_client_with_multiple_datasets():
    c = bz_data('blaze://localhost:6363')
    s = symbol('s', discover(c))

    assert compute(s.accounts.amount.sum() + s.accounts2.amount.sum(),
                    {s: c}) == 600


def test_bz_data():
    c = bz_data('blaze://localhost:6363')
    assert isinstance(c.data, Client)
    assert str(discover(c)) == str(discover(tdata))


def test_bz_data_default_port():
    ec = bz_data('blaze://localhost')
    assert str(discover(ec)) == str(discover(tdata))


def test_bz_data_non_default_port():
    ec = bz_data('blaze://localhost:6364')
    assert ec.data.url == 'http://localhost:6364'


def test_bz_data_all_in_one():
    ec = bz_data('blaze://localhost:6363')
    assert str(discover(ec)) == str(discover(tdata))


class CustomExpr(Expr):
    __slots__ = '_hash', '_child'

    @property
    def dshape(self):
        return self._child.dshape


@dispatch(CustomExpr, DataFrame)
def compute_up(expr, tdata, **kwargs):
    return tdata


def test_custom_expressions():
    ec = Client('localhost:6363')
    t = symbol('t', discover(ec))

    assert list(map(tuple, compute(CustomExpr(t.accounts), ec))) == into(list, df)


def test_client_dataset_fails():
    with pytest.raises(ValueError):
        bz_data('blaze://localhost::accounts')
    with pytest.raises(ValueError):
        bz_data('blaze://localhost::accounts')


def test_client_dataset():
    d = bz_data('blaze://localhost')
    assert list(map(tuple, into(list, d.accounts))) == into(list, df)
