from oaplustools.package import install_dependencies_lst as _install_dependencies_lst


def install_dependencies():
    success = _install_dependencies_lst(["requests==2.31.0", "BeautifulSoup4==4.12.3", "duckduckgo_search==3.9.3",
                                         "aiohttp==3.9.3"])
    if not success:
        return
    print("Done, all possible dependencies for the data module installed ...")
