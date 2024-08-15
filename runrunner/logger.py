'''Logger for runrunner.'''
import logging
from pathlib import Path

# name printed before the messages
NAME = '[RunRunner]'


class Log:
    '''A simple logger.

    This will probably change in a future version to something
    more standard or versatile.
    '''

    _logger: logging.Logger = logging.getLogger(NAME)
    _logger.setLevel(logging.INFO)

    file_format = logging.Formatter(
        '%(asctime)s %(name)-12s:%(levelname)-8s %(message)s')
    console_format = logging.Formatter(
        '%(name)-12s%(levelname)-8s%(message)s'
    )

    @classmethod
    def set_log_file(cls, path: Path = None) -> None:
        '''Set the log file.'''
        cls._logger.handlers.clear()
        if path is None:
            # Only write to terminal
            console = logging.StreamHandler()
            console.setFormatter(cls.console_format)
            cls._logger.addHandler(console)
            return
        file = logging.FileHandler(path)
        file.setFormatter(cls.file_format)
        cls._logger.addHandler(file)
        console = logging.StreamHandler()
        console.setFormatter(cls.console_format)
        console.setLevel(logging.WARNING)
        cls._logger.addHandler(console)

    @classmethod
    def error(cls, txt: str) -> None:
        '''Print an error.'''
        print(f'{NAME} ERROR: {txt}')
        cls._logger.error(txt)
        exit()

    @classmethod
    def warn(cls, txt: str) -> None:
        '''Log a warning.'''
        cls._logger.warning(txt)

    @classmethod
    def info(cls, txt: str) -> None:
        '''Print information.'''
        cls._logger.info(txt)
