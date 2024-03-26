'''Common properties for all runners.'''
from __future__ import annotations
from enum import Enum


class Status(str, Enum):
    '''Possible run statuses.'''

    UNKNOWN = 'unknown'
    NOTSET = 'notset'
    WAITING = 'waiting'
    RUNNING = 'running'
    COMPLETED = 'completed'
    ERROR = 'error'
    KILLED = 'killed'

    @staticmethod
    def from_slurm_string(source: str) -> Status:
        '''Create Status from Slurm Job State Codes.

        For reference see page below:
        https://slurm.schedmd.com/squeue.html#SECTION_JOB-STATE-CODES
        '''
        # TODO: Replace with match case once we are running on Python >=3.10
        source = source.lower()

        if source in ['pending', 'suspended', 'configuring', 'resv_del_hold',
                      'preempted', 'requeued', 'requeue_fed', 'requeue_hold',
                      'stopped', 'signaling']:
            return Status.WAITING
        elif source in ['running', 'completing', 'resizing', 'stage_out']:
            return Status.RUNNING
        elif source in ['cancelled', 'deadline', 'timeout']:
            return Status.KILLED
        elif source in ['boot_fail', 'failed', 'node_fail', 'out_of_memory',
                        'special_exit', 'revoked']:
            return Status.ERROR
        elif source == 'completed':
            return Status.COMPLETED
        else:
            # All Slurm job states have been routed to a Status.
            # This Status should therefore in principal never occur.
            return Status.UNKNOWN


class Runner(str, Enum):
    '''Available runners.'''

    LOCAL = 'local'
    SLURM = 'slurm'
    SLURM_RR = 'slurm_rr'  # Temporary until runrunner for Slurm works satisfactorily
