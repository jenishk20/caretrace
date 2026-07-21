import app as application


def test_network_status_does_not_probe_an_external_host(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("external network probe attempted")

    monkeypatch.setattr(application.socket, "create_connection", fail_if_called)

    assert application._network_reachable() is False
