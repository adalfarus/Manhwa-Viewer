from oaplustools.io import environment, loggers


class TestEnvironment:
    def test_local(self):
        assert environment.local_test()


class TestLoggers:
    def test_local(self):
        assert loggers.local_test()
