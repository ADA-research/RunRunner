'''Logger for runrunner.'''
import logging
from pathlib import Path
from threading import Lock

# name printed before the messages
NAME = '[RunRunner]'


class Log:
    '''A simple logger.

    This will probably change in a future version to something
    more standard or versatile.
    '''

    _logger: logging.Logger = logging.getLogger('simple')
    _logger.setLevel(logging.INFO)
    _print_lock = Lock()

    @classmethod
    def set_log_file(cls, path: Path = None) -> None:
        '''Set the log file.'''
        cls._logger.handlers.clear()
        if path is None:
            # Only write to terminal
            cls._logger.addHandler(logging.StreamHandler())
            return
        cls._logger.addHandler(logging.FileHandler(path))

    @classmethod
    def error(cls, txt: str) -> None:
        '''Print an error.'''
        with Log._print_lock:
            cls._logger.error(f'{NAME} {txt}')
        exit()

    @classmethod
    def warn(cls, txt: str) -> None:
        '''Print a warning.'''
        with Log._print_lock:
            cls._logger.warning(f'{NAME} {txt}')

    @classmethod
    def info(cls, txt: str) -> None:
        '''Print information.'''
        with Log._print_lock:
            cls._logger.info(f'{NAME} {txt}')
