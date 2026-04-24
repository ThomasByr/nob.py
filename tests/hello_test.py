def test_hello():
    """this tests importing nob"""
    from nob import hello

    assert "hello" in dir() and callable(hello)
