'''Initiliase runrunner.'''
from __future__ import annotations

from runrunner.local import add_to_queue as add_to_local_queue
from runrunner.slurm import add_to_queue as add_to_slurm_queue

from runrunner.base import Runner, Run


def add_to_queue(runner: Runner, **options: str) -> Run:
    '''Add jobs to queue depending on the given Runner.'''
    if runner.lower() == Runner.LOCAL:
        queue = add_to_local_queue
    elif runner.lower() == Runner.SLURM:
        queue = add_to_slurm_queue
    else:
        # error
        queue = None
    return queue(**options)
