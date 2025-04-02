from oaplustools import execute_python_command, set_dir_to_ex


class TestDirectFunctions:
    def test_all(self):
        try:
            # set_dir_to_ex()  # Won't work
            execute_python_command(["--version"])
        except Exception as e:
            print(f"Exception occurred {e}")
            assert False
        else:
            assert True
