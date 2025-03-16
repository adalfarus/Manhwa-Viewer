from typing import Optional, Callable, Union, Literal, List, get_type_hints, Any
# from pydantic import BaseModel, ValidationError, Field, create_model
from argparse import ArgumentParser
import sys
import re


class ArgumentParsingError(Exception):
    def __init__(self, message: str, index: int):
        super().__init__(message)
        self.index = index


class Argument:
    def __init__(self, name: str,
                 type_: Optional[type] = None,
                 choices: Optional[list] = None,
                 default: Optional[type] = None,
                 help_: Optional[str] = None):
        self.name = name
        if not choices:
            # If there are no choices, return the specified type or None
            self.type = type_ or None
        else:
            choice_types = set(type(choice) for choice in choices)
            if len(choice_types) == 1:
                # All choices have the same type
                self.type = choice_types.pop()
            else:
                # Choices have different types, return a Union of the types
                self.type = Union[tuple(choice_types)]
        self.choices = choices or []
        self.default = default  # Can be contained within choices
        self.help = help_
        # self.is_optional = default  # Meaning true if there is a default

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, value: type):
        self._default = value
        self.is_optional = value
        #if value in self.choices:
        #    self._default = value
        #else:
        #    raise ValueError(f"The default argument has to be present in the argument choices.")

    @property
    def help(self):
        return self._help

    @help.setter
    def help(self, value: str):
        self._help = value or ""

    def __repr__(self):
        return f"Argument(name={self.name}, \
type={self.type}, \
choices={self.choices}, \
default={self.default}, \
help={self.help})"


class EndPoint:
    """used to define the endpoint of a trace from an argstruct object."""
    def __init__(self, function: lambda: None, arguments: Optional[List[Argument]] = None):
        if arguments:
            self.arguments = arguments
        else:
            arguments = function.__code__.co_varnames or ()
            defaults = list(function.__defaults__ or ())
            shifted_defaults = defaults[:0] = [None] * (len(arguments) - len(defaults)) + defaults
            types = function.__annotations__ or {}
            docstring = function.__doc__ or ""

            help_ = {}
            for argument in arguments:
                start = docstring.find(argument)
                if start != -1:
                    start = start + len(argument)  # Where argument ends in docstring
                    next_line = \
                        [i for i, x in enumerate(docstring[start:]) if x == "\n" or i + 1 == len(docstring[start:])][0]
                    next_line = next_line + start
                    help_[argument] = (
                        docstring[start:next_line].replace("\n", "").strip(": "))  # Can't always leave the last as it could
            type_hints = get_type_hints(function)                                           # be the last of the docstring.
            choices = {}
            for param, type_hint in type_hints.items():
                if getattr(type_hint, '__origin__', None) is Literal:
                    # Extract the literal values
                    choices[param] = type_hint.__args__
            self.arguments = [Argument(arg_name, default=default,
                                       choices=choices.get(arg_name, None),
                                       type_=types.get(arg_name, None),
                                       help_=help_.get(arg_name, ""))
                              for arg_name, default in zip(arguments, shifted_defaults)
                              if arg_name not in ['args', 'kwargs']]
        # input(self.arguments)
        self._arg_index = {arg.name: i for i, arg in enumerate(self.arguments)}
        self.function = function

    def change_argument(self, target_arg_name: str,
                        type_: Optional[type] = None,
                        choices: Optional[list] = None,
                        default: Optional[type] = None,
                        help_: Optional[str] = None):
        if target_arg_name in self.arguments:
            for key, item in locals().items():
                if key in ["type_", "choices", "default", "help_"] and item is not None:
                    setattr(self.arguments[self._arg_index[target_arg_name]], key.strip("_"), item)
        else:
            raise NameError(f"Argument '{target_arg_name}' isn't part of the target function.")

    def replace_argument(self, target_arg_name: str, new_argument: Argument):
        if target_arg_name in self.arguments:
            self.arguments[self._arg_index[target_arg_name]] = new_argument
        else:
            raise NameError(f"Argument '{target_arg_name}' isn't part of the target function.")

    def call(self, *args, **kwargs):
        self.function(*args, **kwargs)

    def __repr__(self):
        return f"Endpoint(arguments={[f'{key}: {self.arguments[index]}' for (key, index) in self._arg_index.items()]})"


class ArgStruct:
    """arg_struct example : {
        "cmd1": ["cmd12", "cmd13"],
        "cmd2": {"cmd22": ["cmd221"], "cmd23": {...}}
    }
    -> structure
    cmd1
        cmd12
        cmd13
    cmd2
        cmd22
            cmd221
        cmd23
            ..."""
    def __init__(self):
        self.commands = {}

    def add_command(self, command: str, subcommands: Optional[dict] = None):
        if subcommands is None:
            subcommands = {}
        self.commands[command] = subcommands

    def add_subcommand(self, parent: str, subcommand: str):
        if parent not in self.commands:
            raise ValueError(f"Command '{parent}' not found.")
        if isinstance(self.commands[parent], dict):
            self.commands[parent][subcommand] = {}
        else:
            raise ValueError(f"Command '{parent}' cannot have subcommands.")

    def add_nested_command(self, parent: str, command: str, subcommand: Optional[Union[str, dict]] = None):
        if subcommand is None:
            subcommand = {}

        # Navigate to the correct parent level
        parts = parent.split('.')
        current_level = self.commands
        for part in parts:
            if part not in current_level or not isinstance(current_level[part], dict):
                raise ValueError(f"Command '{parent}' not found or is not a valid parent.")
            current_level = current_level[part]

        if isinstance(subcommand, str):
            current_level[command] = {subcommand: {}}
        else:
            current_level[command] = subcommand

    def get_structure(self):
        return self.commands


class ArguMint:
    @staticmethod
    def _error(i, command_string):
        print(command_string)
        print(" "*i+"^")

    @staticmethod
    def _lst_error(i, arg_i, command_lst, do_exit=False):
        length = sum(len(item) for item in command_lst[:i]) + i
        print(' '.join(command_lst) + "\n" +
              " " * (length + arg_i) + "^")
        if do_exit:
            sys.exit(1)

    def __init__(self, default_endpoint: Union[EndPoint, Callable],
                 description: Optional[str] = None,
                 arg_struct: Optional[Union[ArgStruct, dict]] = None):
        self.default_endpoint = self._ender(default_endpoint)
        self.description = description or ""
        if isinstance(arg_struct, ArgStruct):
            arg_struct = arg_struct.get_structure()
        self.arg_struct = arg_struct or {}
        self.endpoints = {}

        self.formats = {1: "Usage: nuisco <subcommand> [--args]", 2: "Usage: nuisco create-template [project_name] [--args]"}

    def _check_path(self, path: str, overwrite_pre_args: Optional[Union[ArgStruct, dict]] = None):
        if isinstance(overwrite_pre_args, ArgStruct):
            overwrite_pre_args = overwrite_pre_args.get_structure()
        current_level = overwrite_pre_args or self.arg_struct
        for point in path.split("."):
            if point not in current_level or not isinstance(current_level[point], dict):
                return False
            current_level = current_level[point]
        return True

    @staticmethod
    def _ender(potential_endpoint: Union[EndPoint, Callable]):
        if type(potential_endpoint) is EndPoint:
            endpoint = potential_endpoint
        else:
            endpoint = EndPoint(potential_endpoint)
        return endpoint

    def replace_pre_args(self, new_pre_args: Union[ArgStruct, dict]):
        if isinstance(new_pre_args, ArgStruct):
            new_pre_args = new_pre_args.get_structure()
        to_del = []
        for path, endpoint in self.endpoints.items():
            if self._check_path(endpoint, new_pre_args):
                continue
            else:
                to_del.append(path)
        print(f"Removed {len([self.endpoints.pop(epPath) for epPath in to_del])} endpoints.")

    def add_endpoint(self, path: str, endpoint: Union[EndPoint, Callable]):
        endpoint = self._ender(endpoint)

        if self._check_path(path):
            if not self.endpoints.get(path):
                self.endpoints[path] = endpoint  # I need someway to associate arguments with the arg struct
            else:
                raise ValueError(f"The path {path} already has an endpoint.")
        else:
            raise ValueError(f"The path '{path}' doesn't exist.")

    def replace_endpoint(self, path: str, endpoint: Union[EndPoint, Callable]):
        endpoint = self._ender(endpoint)

        if self._check_path(path):
            self.endpoints[path] = endpoint  # I need someway to associate arguments with the arg struct
        else:
            raise ValueError(f"The path '{path}' doesn't exist.")

    def _parse_pre_args(self, pre_args: list):
        struct_lst = []

        current_struct = self.arg_struct
        i = call = None
        try:
            for i, call in enumerate(pre_args):
                if call in current_struct or ("ANY" in current_struct and len(current_struct) == 1):
                    struct_lst.append(call)
                    if not i == len(pre_args)-1:
                        current_struct = current_struct[call]
                elif len(current_struct) == 0:  # At endpoint
                    break
                else:
                    raise IndexError
        except TypeError:
            print("Too many pre arguments.")
            self._lst_error(i, 0, pre_args, True)
        except (IndexError, KeyError):
            print(f"The argument '{call}' doesn't exist in current_struct ({current_struct}).")
            self._lst_error(i, 0, pre_args, True)
        return struct_lst

    @staticmethod
    def _parse_args_native_light(args: List[str], endpoint: EndPoint, smart_typing: bool = True):
        parsed_args = {}
        remaining_args = list(endpoint.arguments)

        for i, arg in enumerate(args):
            # Check for keyword argument
            if arg.startswith("--"):
                key, _, value = arg[2:].partition('=')
                if not any(a.name == key for a in endpoint.arguments):
                    raise ArgumentParsingError(f"Unknown argument: {key}", i)
                arg_obj = next(a for a in endpoint.arguments if a.name == key)
                parsed_args[key] = arg_obj.type(value) if arg_obj.type else value
                remaining_args.remove(arg_obj)

            # Check for flag argument
            elif arg.startswith("-"):
                key = arg[1:]
                if not any(a.name == key and a.type is bool for a in endpoint.arguments):
                    raise ArgumentParsingError(f"Unknown flag argument: {key}", i)
                parsed_args[key] = True
                remaining_arg = next(a for a in endpoint.arguments if a.name == key)
                remaining_args.remove(remaining_arg)

            # Handle positional argument
            else:
                if smart_typing:
                    # Find the first argument with a matching type
                    for pos_arg in remaining_args:
                        if isinstance(pos_arg.default, type(arg)) or pos_arg.default is None:
                            parsed_args[pos_arg.name] = pos_arg.type(arg)
                            remaining_args.remove(pos_arg)
                            break
                    else:
                        raise ArgumentParsingError("No matching argument type found", i)
                else:
                    # Assign to the next available argument
                    if remaining_args:
                        pos_arg = remaining_args.pop(0)
                        parsed_args[pos_arg.name] = pos_arg.type(arg)

        # Assign default values for missing optional arguments
        for arg in remaining_args:
            if arg.default is not None:
                parsed_args[arg.name] = arg.default

        return parsed_args

    @staticmethod
    def _parse_args_native(args: List[str], endpoint: EndPoint, smart_typing: bool = True):
        parsed_args = {}
        remaining_args = list(endpoint.arguments)

        for i, arg in enumerate(args):
            if arg.startswith("--"):
                key, _, value = arg[2:].partition('=')
                matched_args = [a for a in endpoint.arguments if a.name == key]
                if not matched_args:
                    raise ArgumentParsingError(f"Unknown argument: {key}", i)
                arg_obj = matched_args[0]

                # Create a temporary Pydantic model for conversion and validation
                temp_model = type('TempModel', (BaseModel,), {key: (arg_obj.type, None)})
                try:
                    parsed_args[key] = temp_model(**{key: value}).dict()[key]
                except ValidationError as e:
                    raise ArgumentParsingError(str(e), i)

            elif arg.startswith("-"):
                # Handle flag argument
                key = arg[1:]
                if not any(a.name == key and a.type is bool for a in endpoint.arguments):
                    raise ArgumentParsingError(f"Unknown flag argument: {key}", i)
                parsed_args[key] = True

            else:
                # Handle positional argument with smart typing
                if remaining_args:
                    if smart_typing:
                        for pos_arg in remaining_args:
                            # Create a temporary Pydantic model for conversion and validation
                            TempModel = create_model('TempModel', **{pos_arg.name: pos_arg.type})
                            try:
                                parsed_value = TempModel.parse_obj({pos_arg.name: arg}).dict()[pos_arg.name]
                                parsed_args[pos_arg.name] = parsed_value
                                remaining_args.remove(pos_arg)
                                break
                            except ValidationError:
                                continue
                    else:
                        # Assign to the next available argument without smart typing
                        pos_arg = remaining_args.pop(0)
                        TempModel = create_model('TempModel', **{pos_arg.name: pos_arg.type})
                        try:
                            parsed_value = TempModel.parse_obj({pos_arg.name: arg}).dict()[pos_arg.name]
                            parsed_args[pos_arg.name] = parsed_value
                        except ValidationError:
                            raise ArgumentParsingError(f"Error parsing {pos_arg.name}", i)

        # Assign default values for missing optional arguments
        for arg in remaining_args:
            if arg.default is not None:
                parsed_args[arg.name] = arg.default

        return parsed_args

    @staticmethod
    def _parse_args_arg_parse(args: List[str], endpoint: EndPoint):
        parser = ArgumentParser()

        # Set up argparse for keyword and flag arguments
        for arg in endpoint.arguments:
            if arg.type is bool:  # For boolean flags
                parser.add_argument(f"-{arg.name[0]}", f"--{arg.name}", action='store_true', help=arg.help)
            else:
                parser.add_argument(f"--{arg.name}", type=arg.type, default=arg.default, help=arg.help)

        # Parse arguments with argparse
        parsed_args = parser.parse_args(args)
        return vars(parsed_args)

    def _parse_args(self, args: List[str], endpoint: EndPoint, mode: Literal["arg_parse", "native_light", "native"] = "arg_parse") -> dict:
        func = self._parse_args_native if mode == "native" else self._parse_args_native_light if mode == "native_light" else self._parse_args_arg_parse
        return func(args, endpoint)

    def parse_cli(self, system: sys = sys, mode: Literal["arg_parse", "native_light", "native"] = "arg_parse"):
        arguments = system.argv
        pre_args = self._parse_pre_args(arguments)
        path = '.'.join(pre_args)
        args = arguments[arguments.index(pre_args[-1])+1:]  # Will return an empty list, if [i:] is longer than the list
        endpoint = self.endpoints.get(path) or self.default_endpoint
        arguments = self._parse_args(args, endpoint, mode)
        endpoint.call(**arguments)


def local_test():
    try:
        def sorry(*args, **kwargs):
            print("Not implemented yet, sorry!")

        def help_text():
            print("Build -> dir/file or help.")

        def build_file(path: Literal["./main.py", "./file.py"] = "./main.py", num: int = 0):
            """
            build_file
            :param path: The path to the file that should be built.
            :param num:
            :return None:
            """
            print(f"Building file {path} ..., {num}")

        from oaplustools.package import timid

        timer = timid.TimidTimer()

        arg_struct = {'apt': {'build': {'file': {}, 'dir': {'main': {}, 'all': {}}}, 'help': {}}}

        # Example usage
        builder = ArgStruct()
        builder.add_command("apt")
        builder.add_nested_command("apt", "build", "file")

        builder.add_nested_command("apt.build", "dir", {'main': {}, 'all': {}})
        # builder.add_subcommand("apt.build", "dir")
        # builder.add_nested_command("apt.build.dir", "main")
        # builder.add_nested_command("apt.build.dir", "all")

        builder.add_command("apt.help")
        # builder.add_nested_command("apt", "help")

        print(builder.get_structure())  # Best to cache this for better times (by ~15 microseconds)

        parser = ArguMint(default_endpoint=sorry, arg_struct=arg_struct)
        parser.add_endpoint("apt.help", help_text)

        parser.add_endpoint("apt.build.file", build_file)

        sys.argv[0] = "apt"

        # Testing
        # sys.argv = ["apt", "help"]
        sys.argv = ["apt", "build", "file", "./file.py", "--num=19"]
        parser.parse_cli(sys, "native_light")
        print(timer.end())
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
