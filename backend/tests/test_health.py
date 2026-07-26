from trama_publica.api.app import health


def test_health() -> None:
    assert health() == {"status": "ok"}
