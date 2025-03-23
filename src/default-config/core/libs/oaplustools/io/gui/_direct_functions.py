from oaplustools.package import install_dependencies_lst as _install_dependencies_lst


def install_dependencies():
    success = _install_dependencies_lst(["PySide6==6.6.1", "brotli==1.1.0"])
    if not success:
        return
    print("Done, all possible dependencies for the data module installed ...")
