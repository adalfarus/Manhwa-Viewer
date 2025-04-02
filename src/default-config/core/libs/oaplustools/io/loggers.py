import sys
import time
from typing import TextIO, Union, Optional, Type, Callable, Tuple
from enum import Enum
import warnings


class LogType(Enum):
    NONE = ""
    INFO = "[INFO] "
    DEBUG = "[DEBUG] "
    WARN = "[WARN] "
    ERR = "[ERR] "
    ANY = None


# Doesn't work at the moment
# def overwrite_log_type(new_log_type: Type[LogType]):
#     LogType = new_log_type


def classify_type_stan(message: str) -> Tuple[LogType, str]:
    mess = message.lower()
    if any(x in mess for x in ["err", "error"]):
        log_type = LogType.ERR
    elif any(x in mess for x in ["warn", "warning"]):
        log_type = LogType.WARN
    elif any(x in mess for x in ["deb", "debug"]):
        log_type = LogType.DEBUG
    else:
        log_type = LogType.NONE
    return log_type, ""


class Logger(object):
    def __init__(self, log_filename: str = "Default.log",
                 include_timestamp: bool = True,
                 print_log_to_stdout: bool = True, *_, **__):
        self.include_timestamp = include_timestamp
        self.print_log_to_stdout = print_log_to_stdout
        self.log_file = open(log_filename, "a", encoding='utf-8')
        
    def _add_timestamp(self, message: str) -> str:
        """Adds a timestamp to the message if include_timestamp is True."""
        if self.include_timestamp and message.strip():
            timestamp = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}] " if self.include_timestamp else ''
            return timestamp + message if message != '\n' else message
        return message
    
    def log(self, message: str):
        """Logs a message to the file and optionally to stdout."""
        message = str(message)
        message_with_timestamp = self._add_timestamp(message) + "\n"
        self.log_file.write(message_with_timestamp)
        self.log_file.flush()
        if self.print_log_to_stdout:
            self._write_to_stdout(message_with_timestamp)
            
    def _write_to_stdout(self, message: str):
        """Writes message to stdout."""
        print(message)
        
    def close(self):
        """Closes the log file."""
        self.log_file.close()
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        """Destructor to ensure the log file is closed properly."""
        self.close()


class PrintLogger(Logger):
    def __init__(self, log_filename: str = "Default.log", include_timestamp: bool = True,
                 capture_stdout: bool = True, overwrite_stdout: bool = True,
                 stdout_passthrough: bool = True, print_log_to_stdout: bool = True, *_, **__):
        super().__init__(log_filename, include_timestamp, print_log_to_stdout)
        self.capture_stdout = capture_stdout
        self.terminal = sys.stdout if overwrite_stdout else None
        self.stdout_passthrough = stdout_passthrough
        self.buffer = ''
            
    def _check_content(self, content: str):
        """Check the content from stdout traffic."""
        if self.capture_stdout:
            message_with_timestamp = self._add_timestamp(content)
            self.log_file.write(message_with_timestamp)
            self.log_file.flush()
        if self.stdout_passthrough:
            message_with_timestamp = self._add_timestamp(content)
            self._write_to_stdout(message_with_timestamp)

    def _write_to_stdout(self, message: str):  # Overwrite this with the new one
        """Writes message to stdout."""
        if self.terminal is not None:
            self.terminal.write(message)
            self.terminal.flush()

    def write(self, message: str):
        """Original write, here to catch any stdout traffic."""
        self.buffer += message
        if message.endswith('\n'):
            content = self.buffer
            self.buffer = ''
            self._check_content(content)

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # Flush behaviour is already handled elsewhere.
        pass
        
    def close(self): # Overwrite this too
        """Closes the log file and restores the original stdout, if overwritten."""
        self.log_file.close()
        if self.terminal:
            sys.stdout = self.terminal


class TypeLogger(PrintLogger):  # The , *_, **__ need to be added as direct init calls lead to errors
    def __init__(self, log_filename: str = "Default.log", include_timestamp: bool = True, capture_stdout: bool = True,
                 overwrite_stdout: bool = True, stdout_passthrough: bool = True, print_log_to_stdout: bool = True,
                 display_message_type: bool = True, message_type_classifier: Callable = classify_type_stan,
                 classify_message_type: bool = True, enable_type_system: bool = True, write_type: bool = True,
                 current_display_type: LogType = LogType.ANY, current_logging_type: LogType = LogType.ANY, *_, **__):
        super().__init__(log_filename, include_timestamp, capture_stdout,
                         overwrite_stdout, stdout_passthrough, print_log_to_stdout)
        self.display_message_type = display_message_type
        self.message_type_classifier = message_type_classifier
        self.classify_message_type = classify_message_type
        self.enable_type_system = enable_type_system
        self.write_type = write_type
        self.current_display_type = current_display_type
        self.current_logging_type = current_logging_type
        self.log_switch = False # If the program is currently logging

    def _add_type(self, message: str, log_type: Optional[LogType] = None) -> str:
        """Adds the type to the message if an depending on the switches."""
        if self.enable_type_system and message.strip():
            if self.display_message_type and not self.log_switch:
                if not log_type and self.classify_message_type:
                    message_type, remove_str = self.message_type_classifier(message)
                elif log_type:
                    message_type, remove_str = log_type, ""
                else:
                    message_type, remove_str = LogType.NONE, ""
                message = message.replace(remove_str, "")
                if self.current_display_type == message_type or self.current_display_type == LogType.ANY:
                    message = message_type.value + message if message != '\n' else message
            elif (self.display_message_type and self.write_type) and self.log_switch:
                if not log_type and self.classify_message_type:
                    message_type, remove_str = self.message_type_classifier(message)
                elif log_type:
                    message_type, remove_str = log_type, ""
                else:
                    message_type, remove_str = LogType.NONE, ""
                message = message.replace(remove_str, "")
                if self.current_logging_type == message_type or self.current_logging_type == LogType.ANY:
                    message = message_type.value + message if message != '\n' else message
        return message

    def log(self, *message: Union[str, LogType], log_type: Optional[LogType] = None):
        """Logs a message to the file and optionally to stdout."""
        if isinstance(message, str):
            message = [message]
        elif isinstance(message, list) or isinstance(message, tuple):
            message = list(message)
        else: raise TypeError(f"{message.__class__} isn't supported'")
        logT, pop_lst = LogType.NONE, []
        for i, item in enumerate(message):
            if isinstance(item, LogType):
                logT = item
                pop_lst.append(i)
        [message.pop(x - i) for i, x in enumerate(pop_lst)]
        message = ' '.join([str(x) for x in message])
        log_type = log_type or logT
        message_with_timestamp = self._add_timestamp(message) + "\n"
        self.log_switch = True
        self.log_file.write(self._add_type(message_with_timestamp, log_type))
        self.log_file.flush()
        if self.print_log_to_stdout:
            message_with_timestamp = self._add_timestamp(message) + "\n"
            self.log_switch = False
            self._write_to_stdout(self._add_type(message_with_timestamp, log_type))
            
    def _check_content(self, content: str):
        """Check the content from stdout traffic."""
        if self.capture_stdout:
            message_with_timestamp = self._add_timestamp(content)
            self.log_switch = True
            self.log_file.write(self._add_type(message_with_timestamp))
            self.log_file.flush()
        if self.stdout_passthrough:
            message_with_timestamp = self._add_timestamp(content)
            self.log_switch = False
            self._write_to_stdout(self._add_type(message_with_timestamp))


class FullTypeLogger:
    """This class is here to implement a full type system on top of the print system
    Please do not use it however, as it's quite complex - Use it as an inspiration for your
    own logger subclass instead. This doesn't inherit from anything, to focus on making a good
    logger instead on compatibility. The aim is to be better than the default logger. This also
    acts as an inspiration for the normal TypeLogger.
    """
    def __init__(self, log_filename: str = "Default.log", include_timestamp: bool = True,
                 print_logger: PrintLogger = PrintLogger, display_message_type: bool = True,
                 message_type_classifier: Callable = lambda: None, classify_message_type: bool = True,
                 enable_type_system: bool = True, current_display_type: LogType = LogType.ANY,
                 current_logging_type: Optional[LogType] = LogType.ANY):
        raise NotImplementedError("This class is not implemented yet. Please use with caution")

        if print_logger and isinstance(print_logger, PrintLogger):
            self.print_logger = PrintLogger(log_filename, include_timestamp)
        else: raise TypeError("print_logger needs to be a (sub-)class of PrintLogger")
        self.display_message_type = display_message_type
        self.message_type_classifier = message_type_classifier
        self.classify_message_type = classify_message_type
        self.enable_type_system = enable_type_system
        self.current_display_type = current_display_type
        self.current_logging_type = current_logging_type
    
    def log(self, message: str, type: Type[LogType]=LogType.NONE):
        message = str(message)
        pass


def monitor_stdout(log_file: Optional[str] = None,
                   logger: Optional[Type[Logger]] = None
                   ) -> Union[TextIO, Type[Logger]]:
    """Monitors and logs stdout messages based on given parameters.

    Args:
        log_file: The name of the log file.
        logger: An instance of the Logger class.

    Returns:
        An instance of the Logger class with stdout being monitored and logged.
    """
    if logger is None:
        if log_file is None:
            raise ValueError("Either log_file or logger must be provided")
        logger = PrintLogger(log_file)
    elif type(logger) is Logger:
        raise ValueError("The default Logger class wasn't built to be used\
like this, please use PrintLogger or TypeLogger instead.")
    
    sys.stdout = logger
    return sys.stdout


def local_test():
    try:
        logger = Logger("./test_data/cu.txt")
        logger.log("Hello Worlds")
        logger2 = PrintLogger("./test_data/cu.txt")
        print("Hellow worldddsssss")
        monitor_stdout(logger=logger2)
        print("Logging this")
        logger2.log("Logging that")
        logger2.close()
        print("Just print lol")
        ref = monitor_stdout(logger=TypeLogger("./test_data/cu.txt"))
        print("[Debug] No ref, so just print xd")
        print("[Warn] No ref, so just print xd")
        print("Do not do this, you need a ref to close it")
        ref.log("Hello World [Warn]", LogType.WARN, LogType.WARN)
        ref.close()
        print("DONE")
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
