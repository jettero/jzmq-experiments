# coding: utf-8

from jzmq.jsmb.endpoint import Endpoint, DEFAULT_PUBLISH_PORT, DEFAULT_COLLECTOR_PORT, DEFAULT_DIRECTED_PORT

def test_host_no_ports():
    host = Endpoint('host')
    assert host.host == 'host'
    assert host.pub == DEFAULT_PUBLISH_PORT
    assert host.pull == DEFAULT_COLLECTOR_PORT
    assert host.router == DEFAULT_DIRECTED_PORT

def test_host_one_port():
    host = Endpoint('host:80')
    assert host.host == 'host'
    assert host.pub == 80
    assert host.pull == 81
    assert host.router == 82

def test_url():
    urlendpoint = Endpoint('udp://blah:123,456')
    assert urlendpoint.proto == 'udp'
    assert urlendpoint.host == 'blah'
    assert urlendpoint.pub == 123
    assert urlendpoint.pull == 456
    assert urlendpoint.router == 457

