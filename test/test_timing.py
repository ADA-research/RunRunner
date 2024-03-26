'''Tests for the timing module.'''
# from runrunner import local
from runrunner import timing


def test_format_seconds() -> None:
    '''Test format_seconds() handling of different amounts of seconds.'''
    # Integer seconds < 60
    output = timing.format_seconds(6)
    assert (output == '6.000s')

    # Float seconds < 60
    output = timing.format_seconds(6.1)
    assert (output == '6.100s')

    # Integer seconds >= 60
    output = timing.format_seconds(60)
    assert (output == ' 1m 0.000s')

    # Float seconds >= 60
    output = timing.format_seconds(60.435234)
    assert (output == ' 1m 0.435s')

    # Integer minutes >= 60
    output = timing.format_seconds(3600)
    assert (output == '1h  0m 0.000s')

    # Float minutes >= 60
    output = timing.format_seconds(3600.2)
    assert (output == '1h  0m 0.200s')
