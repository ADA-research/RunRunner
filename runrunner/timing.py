'''A class implementing a simple timer with a nice time display.'''

from time import perf_counter


class Timer:
    '''Simple timer to get the elapsed time in a nice formatted string.'''

    def __init__(self) -> None:
        '''Create a new timer. The time is started at creation.'''
        self.init_time = perf_counter()
        self.stop_time = None

    def stop(self) -> str:
        '''Stop the timer.'''
        self.stop_time = perf_counter()
        return self.__repr__()

    def __repr__(self) -> str:
        '''Return a human readable str of the elapsed time.'''
        return f'Elapsed time: {format_seconds(self.elapsed)}'

    def __str__(self) -> str:
        '''Return a human readable str of the time with hours, minutes and seconds.'''
        return format_seconds(self.elapsed)

    @property
    def elapsed(self) -> float:
        '''Return the elapsed time between init and stop, or current time if not done.'''
        if self.stop_time is None:
            return perf_counter() - self.init_time
        else:
            return self.stop_time - self.init_time


def format_seconds(seconds: float) -> str:
    '''Nice format for seconds with hours and minutes values if needed.

    Example:
        12.2 -> "12.200s"
        78.4 -> "1m 18.400s"
        4000 -> "1h 6m 40.0s"
    '''
    if seconds < 60:
        return f'{seconds:.3f}s'
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f'{int(minutes):2d}m {seconds:.3f}s'
    hours, minutes = divmod(minutes, 60)
    return f'{int(hours):d}h {int(minutes):2d}m {seconds:.3f}s'
