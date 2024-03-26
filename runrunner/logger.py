'''Logger for runrunner.'''

from threading import Lock

# name printed before the messages
NAME = 'RunRunner'


class Log:
    '''A simple logger.

    This will probably change in a future version to something
    more standard or versatile.
    '''

    _print_lock = Lock()

    @classmethod
    def error(cls, txt: str) -> None:
        '''Print an error.'''
        with Log._print_lock:
            print(NAME, 'ERROR', txt, flush=True)
        exit()

    @classmethod
    def warn(cls, txt: str) -> None:
        '''Print a warning.'''
        with Log._print_lock:
            print(NAME, 'WARNING', txt, flush=True)

    @classmethod
    def info(cls, txt: str) -> None:
        '''Print information.'''
        with Log._print_lock:
            print(NAME, txt, flush=True)
