# coding: utf-8

import pytest


@pytest.fixture
def always_true():
    yield True
