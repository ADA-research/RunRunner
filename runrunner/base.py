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


class Job:
    '''Abstract class for Job objects.'''

    def __init__(self, **kwargs: str) -> None:
        '''Initialise a new Job.'''
        raise NotImplementedError

    @property
    def status(self) -> Status:
        '''Return the status of the job. See runrunner.base.Status for statuses.'''
        return self._status

    @property
    def is_completed(self) -> bool:
        '''Return true if the job was completed, false otherwise.'''
        return self.status == Status.COMPLETED

    @property
    def is_error(self) -> bool:
        '''Return true if there was an error during the job, false otherwise.'''
        return self.status == Status.ERROR

    def run(self) -> Job:
        '''Execute the job.'''
        raise NotImplementedError

    def wait(self, timeout: int = None) -> Job:
        '''Wait for cmd to complete before returning.'''
        raise NotImplementedError

    def kill(self) -> None:
        '''Kill the job.'''
        raise NotImplementedError

    @property
    def returncode(self) -> int:
        '''Return the return code of the cmd.'''
        raise NotImplementedError

    @property
    def stdout(self) -> str:
        '''Return the standard output stream.'''
        raise NotImplementedError

    @property
    def stderr(self) -> str:
        '''Return the standard error stream.'''
        raise NotImplementedError

    @property
    def pid(self) -> int:
        '''Return the PID of the job's process.'''
        raise NotImplementedError

    def write_log(self) -> None:
        '''Write the subprocess output to the log.'''
        raise NotImplementedError


class Run:
    '''Abstract class for Run objects.'''

    @property
    def all_status(self) -> list[Status]:
        '''Return an iterator over the status of the jobs.'''
        raise NotImplementedError

    @property
    def status(self) -> Status:
        '''Global status of the jobs.'''
        raise NotImplementedError

    def run_all(self) -> Run:
        '''Run the jobs of the run object.'''
        raise NotImplementedError

    def _add_job_to_queue(self, job: Job) -> any:
        '''Add 'job' to the execution list.'''
        raise NotImplementedError

    def wait(self, timeout: int = None) -> Run:
        '''Wait for the run to finish.'''
        raise NotImplementedError

    def kill(self) -> Run:
        '''Terminate the run.'''
        raise NotImplementedError

    def __repr__(self) -> str:
        '''Return a simple representation of the job.'''
        raise NotImplementedError

    def __len__(self) -> int:
        '''Return the number of sub-runs.'''
        raise NotImplementedError
