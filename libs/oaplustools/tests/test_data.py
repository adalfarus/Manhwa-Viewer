from oaplustools.data import database, imagetools, updaters, faker, advanced_imagetools, compressor


class TestUpdaters:
    def test_get_last_version(self):
        updater = updaters.GithubUpdater("adalfarus", "unicode-writer")
        assert (updater.get_latest_tag_version(), updater.get_latest_release_title_version()) == ("0.0.2", "0.0.2")
        
    def test_local(self):
        assert updaters.local_test()


class TestDatabase:
    def test_local(self):
        assert database.local_test()


class TestFaker:
    def test_local(self):
        assert faker.local_test()


class TestImagetools:
    def test_local(self):
        assert imagetools.local_test()


class TestAdvancedImagetools:
    def test_local(self):
        assert advanced_imagetools.local_test()


class TestCompressor:
    def test_local(self):
        assert compressor.local_test()
