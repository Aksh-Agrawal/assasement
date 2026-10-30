from concurrent.futures import Future

import httpx

from app import diagnostics
from app.ui.device import DeviceConsole


def test_ready_503_preserves_independent_connectivity_and_account_state(monkeypatch):
    def respond(request):
        if request.url.path == '/health':
            return httpx.Response(200)
        return httpx.Response(503, json={'database': 'ok', 'migration': 'outdated'})
    monkeypatch.setattr(diagnostics, 'create_client', lambda *a, **kw: httpx.Client(
        base_url='https://cloud.invalid', transport=httpx.MockTransport(respond)))
    network = diagnostics.collect_network_status('https://cloud.invalid', auth_token='test')
    assert network.backend_reachable is True
    assert network.database_ready is False
    assert network.auth_accepted is None
    console = object.__new__(DeviceConsole)
    console.future = Future()
    console.future.set_result((0, (True, network, 'Available')))
    console.generation = 0
    console.operation = 'network'
    console.account_verified = False
    assert console.poll()
    assert console.internet_status == 'Available'
    assert 'reachable, not ready' in console.message
    assert 'Internet unavailable' not in console.message
    assert console.account_verified is False
