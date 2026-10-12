import arena


def test_package_exposes_version() -> None:
    assert arena.__version__ == "0.1.0"
