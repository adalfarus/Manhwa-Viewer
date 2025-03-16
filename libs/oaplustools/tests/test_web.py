from oaplustools.web import utils, request, search


class TestUtils:
    def test_local(self):
        assert utils.local_test()


class TestRequest:
    def test_local(self):
        assert request.local_test()


class TestSearch:
    def test_local(self):
        assert search.local_test()
