from oaplustools.package import timid, argumint


class TestTimid:
    def test_local(self):
        assert timid.local_test()


class TestArguMint:
    def test_local(self):
        assert argumint.local_test()
