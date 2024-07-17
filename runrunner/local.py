'''
LocalRunner class.

The local runner uses a thread pool executor to dispatch the runs and executed them in
parallel or in series (if only one thread is available).

At the moment, the user need to use QueueJobs.wait() on the last QueueJobs before
the program exit(). If not, the thread pool is terminated and only the remaining jobs
will be completed and the wait list (jobs with dependencies) cannot be added to the
pool queue and won't be executed.
'''

# __future__ import
from __future__ import annotations

# Standard import
import os
import shlex
import subprocess
import time

from collections import Counter
from concurrent import futures
from concurrent.futures import Executor
from concurrent.futures import Future
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from math import ceil
from math import log10
from pathlib import Path
from threading import Lock
from typing import ClassVar

# RunRunner imports
from runrunner.base import Status, Job, Run
from runrunner.logger import Log
from runrunner.timing import Timer


# Main function to use to create jobs
def add_to_queue(
    cmd: str | list[str],   # The command(s) to execute
    path: str | Path | None = None,
    name: str | None = None,
    parallel_jobs: int = 1,
    stdout: Path | list[Path] | None = None,
    stderr: Path | list[Path] | None = None,
    start_now: bool = True,
    dependencies: LocalJob | list[LocalJob] | LocalRun | list[LocalRun] | None = None,
    **kwargs: str
) -> LocalRun:
    '''Add one or more command line call(s) to the local queue.

    This function is a simplified way to create QueuedJobs instances.

    Parameters:
        cmd: str | list[str]
            The command(s) to add as string(s).
        path: str | Path | None
            The working directory from where the commands will be executed. If None, use
            the current working directory
        name: str | None
            A name given to the job(s) to ease their identification. If None, a
            (non unique) name will be used based on the command call.
        stdout: Path | list[Path] | None
            The path to the standard output file. If None, stdout is send to PIPE
        stderr: Path | list[Path] | None
            The path to the standard error file. If None, stderr is send to PIPE
        parallel_jobs: int
            Number of jobs to run in parallel. By default, run on one thread (serial).
        dependencies: LocalRun | list[LocalRun] | LocalJob | list[LocalJob] | None
            The command(s) will wait for all `dependencies` to finish before starting.
    Returns
    -------
        LocalRun
            An instance of LocalRun.
    '''
    path = Path() if path is None else Path(path)

    if isinstance(cmd, str):
        cmd = [cmd]

    # make dependencies a list of CmdRun
    dependencies = _dependency_as_list(dependencies)

    if name is None:
        # Unnamed jobs
        names = [None] * len(cmd)
    else:
        # Create a list of job names. The names are formed using the run name
        # appended with a number. For example, for a run named runA with 12
        # jobs: [runA_01, runA_02, ..., runA_12]
        n = ceil(log10(len(cmd) + 1))  # For a correct number of leading 0
        names = [f'{name}_{i+1:0{n}}' for i in range(len(cmd))]

    # Cast outputs to list
    if not isinstance(stdout, list):
        stdout = [stdout] * len(cmd)
    if not isinstance(stderr, list):
        stderr = [stderr] * len(cmd)

    if len(cmd) != len(stdout) != len(stderr):
        raise ValueError('`cmd`, `stdout` and `stderr` must have the same length')

    return LocalRun(
        jobs=[LocalJob(cmd=c, path=path, name=n, stdout=o, stderr=e)
              for c, n, o, e in zip(cmd, names, stdout, stderr)],
        parallel_jobs=parallel_jobs,
        dependencies=dependencies,
        name=name,
        start_post_init=start_now
    )


def _dependency_as_list(dep: LocalJob | list[LocalJob] | LocalRun | list[LocalRun]
                        ) -> list[LocalJob]:
    '''Transform `dep` into a list[LocalJob].'''
    if dep is None:
        return []
    elif isinstance(dep, LocalJob):
        return [dep]
    elif isinstance(dep, LocalRun):
        return dep.jobs
    elif isinstance(dep, list):
        ret = []
        for d in dep:
            ret.extend(_dependency_as_list(d))
        return ret


class LocalJob(Job):
    '''A local machine execution of a single command.

    Attributes
    ----------
    base_dir:
        The directory for the log files
    cmd: str
        The command to execute as a single string
    path: Path
        The working directory where to execute the command
    name: str
        A (non-unique) name for the LocalRun
    '''

    base_dir: Path = Path('Tmp')
    cmd: str
    path: Path
    name: str

    # Private attributes
    _process: subprocess.Popen = None
    _status: Status = Status.NOTSET

    def __init__(self,
                 cmd: str,
                 path: str | Path | None = None,
                 name: str | None = None,
                 stdout: Path | None = None,
                 stderr: Path | None = None,
                 ) -> None:
        '''Initialise a new LocalJob.

        The job is created, but not executed. Use LocalJob.run() to
        execute the command.

        Parameters
        ----------
        cmd: str
            The command to run as a single string
        path: str | Path | None
            The working directory where to execute the command. If None (default), the
            current working directory is used.
        name: str | None
            A (non-unique) name for the LocalJob. If None (default), the name is the
            name of the command to execute. Ex.: /some/path/mycode --flag 12, will have
            the name "mycode".
        stdout: Path | None
            The path to the standard output file. If None, stdout is send to PIPE
        stderr: Path | None
            The path to the standard error file. If None, stderr is send to PIPE
        '''
        self.cmd = str(cmd)
        self.path = Path() if path is None else Path(path)
        self.name = name or Path(shlex.split(self.cmd)[0]).name
        self._stdout_target = stdout
        self._stderr_target = stderr

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

    @property
    def stdout_target(self) -> any:
        '''Return the standard output stream.'''
        if self._stdout_target is None:
            return subprocess.PIPE
        return self._stdout_target.open('a')

    @property
    def stderr_target(self) -> any:
        '''Return the standard error stream.'''
        if self._stderr_target is None:
            return subprocess.PIPE
        return self._stderr_target.open('a')

    def run(self) -> LocalJob:
        '''Execute the job.'''
        if self.status == Status.RUNNING:
            Log.warn(f'{self}: Trying to start an already running job. Skipped.')
            return self

        # Create working dir (if needed)
        self.path.mkdir(parents=True, exist_ok=True)

        # Launch the subprocess
        Log.info(f'{self}: Started -- Time: {datetime.now()} ')
        t = Timer()
        # As the command for the subprocess can contain user created input,
        # the input may be errornous. Therefore, we need a try-catch statement.
        try:
            self._process = subprocess.Popen(
                shlex.split(self.cmd),
                stdout=self.stdout_target,
                stderr=self.stderr_target,
                cwd=self.path,
            )
        except Exception as except_msg:
            print(f'ERROR starting job {self.name}: {except_msg}')
            self._status = Status.ERROR
            return self
        self.wait()
        t.stop()
        Log.info(f'{self}: Completed -- Elapsed time: {t}')
        self.write_log()

        return self

    def wait(self, timeout: int = None) -> LocalJob:
        '''Wait for cmd to complete before returning.'''
        self._process.wait(timeout=timeout)
        if self._process.returncode == os.EX_OK:
            self._status = Status.COMPLETED
        else:
            self._status = Status.ERROR
        return self

    def kill(self) -> None:
        '''Kill the job.'''
        self._process.kill()
        self._status = Status.KILLED

    @property
    def returncode(self) -> int:
        '''Return the return code of the cmd.'''
        return self._process.poll()

    @property
    def stdout(self) -> str:
        '''Return the standard output stream.'''
        if self._stdout_target is not None:
            return self._stdout_target.read_text()
        return self._process.stdout.read().decode()

    @property
    def stderr(self) -> str:
        '''Return the standard error stream.'''
        if self._stderr_target is not None:
            return self._stderr_target.read_text()
        return self._process.stderr.read().decode()

    @property
    def pid(self) -> int:
        '''Return the PID of the job's process.'''
        if self._process is None:
            return None
        else:
            return self._process.pid

    def __repr__(self) -> str:
        '''Return a simple representation of the job.'''
        return f'JOB {self.name}'


@dataclass
class LocalRun(Run):
    '''A collections of jobs.

    When created the runs will be added to the execution list
    if all their dependencies are satisfied. If not, the QueuedRun will be added to
    a wait list waiting for the dependencies.

    Attributes
    ----------
    jobs: list[LocalJob]
        The list of jobs
    parallel_jobs: int
        Number of jobs to run in parallel. Default to 1 (serial execution).
    dependencies: List[LocalJob] | None
        The list of job that the Run dependencies on. The Run won't be executed until all
        the dependencies are completed.
    name: str
        A name for the Run. Default: name of the first job
    '''

    jobs: list[LocalJob]
    parallel_jobs: int = 1
    dependencies: list[LocalJob] | None = None
    name: str | None = None
    start_post_init: bool = True

    # Private attribute
    _futures: list[Future] | None = None   # see concurrent.future.Future

    # Class attribute variables
    _executor: ClassVar[Executor | None] = None
    _max_workers: ClassVar[int | None] = None
    _wait_list: ClassVar[list[LocalRun]] = []
    _queue_lock: ClassVar = Lock()

    def __post_init__(self) -> None:
        '''Initialise a LocalRun.'''
        self.name = self.name or self.jobs[0].name
        self.dependencies = self.dependencies or []
        if self.dependencies:
            Log.info(f'{self}: Added to wait list. Jobs:  {len(self)}\t'
                     f'Dependencies: {len(self.dependencies)}.')
        else:
            Log.info(f'{self}: Adding jobs to local queue. Jobs: {len(self)}')

        if self.start_post_init:
            self.run_all()

    @property
    def all_status(self) -> list[Status]:
        '''Return an iterator over the status of the jobs.'''
        return [job.status for job in self.jobs]

    @property
    def status(self) -> Status:
        '''Global status of the jobs.

        Checked in this order:
            Any error     => RunStatus.ERROR
            All waiting   => RunStatus.WAITING
            Some running  => RunStatus.RUNNING
            All completed => RunStatus.COMPLETED
            Any killed    => RunStatus.KILLED
        '''
        n_jobs = len(self)

        count = {s: 0 for s in Status}  # All status at 0
        count |= Counter(self.all_status)  # Update subruns status

        if count[Status.ERROR] > 0:
            return Status.ERROR
        elif count[Status.WAITING] == n_jobs:
            return Status.WAITING
        elif count[Status.RUNNING] > 0:
            return Status.RUNNING
        elif count[Status.COMPLETED] == n_jobs:
            return Status.COMPLETED
        elif count[Status.KILLED] > 0:
            return Status.KILLED
        else:
            return Status.NOTSET

    def run_all(self) -> LocalRun:
        '''Run the jobs.

        The jobs will be added either to the queue to be executed as soon as possible
        or on a wait list, depending on the status of the dependencies of the run.
        '''
        if all([run.is_completed for run in self.dependencies]):
            # All dependencies are completed

            if self._futures is not None:
                # The run was already added.
                Log.warn(f'{self}: jobs already on the queue.')
            else:
                # Create the executor (if needed)
                LocalRun._init_executor(max_workers=self.parallel_jobs)

                # Add the job the execution list
                self._futures = [self._add_job_to_queue(job) for job in self.jobs]

                # Remove from the wait list if needed
                if self in LocalRun._wait_list:
                    LocalRun._wait_list.remove(self)
        else:
            # Some dependencies are not completed
            # TODO: Manage if some dependencies have error
            if self not in LocalRun._wait_list:
                # Run not on the wait list, add it
                LocalRun._wait_list.append(self)

        return self

    def _add_job_to_queue(self, job: LocalJob) -> Executor:
        '''Add 'job' to the execution list.

        When possible the job will be executed by calling job.run(). After
        the completion of the job, a check is made to see if any run on
        the wait list can be added to the execution list (by calling
        Run.run_all() on all the LocalRun on the wait list).
        '''
        Log.info(f'{self}: Adding {job} to local queue')
        job._status = Status.WAITING

        def job_run_with_post() -> None:
            job.run()
            # post completion
            with LocalRun._queue_lock:
                for run in LocalRun._wait_list:
                    run.run_all()

        return LocalRun._executor.submit(job_run_with_post)

    def wait(self, timeout: int = None) -> LocalRun:
        '''Wait for the run to finish.'''
        while self._futures is None:
            time.sleep(0.1)
        for _ in futures.as_completed(self._futures, timeout=timeout):
            pass
        return self

    def kill(self) -> LocalRun:
        '''Terminate the run.'''
        for job in self.jobs:
            job.kill()
        return self

    def __repr__(self) -> str:
        '''Return a simple representation of a LocalRun.'''
        return f'RUN {self.name}'

    def __len__(self) -> int:
        '''Return the number of sub-runs.'''
        return self.jobs.__len__()

    @staticmethod
    def _init_executor(max_workers: int | None = None) -> None:
        '''Initialize, if needed, the executor.

        The max_workers will set the number
        of parallel jobs. The max_workers only work on the first call to the first,
        i.e. at the creation of the executor.
        '''
        if LocalRun._executor is None:
            LocalRun._executor = ThreadPoolExecutor(max_workers=max_workers)
        elif LocalRun._max_workers != max_workers:
            Log.warn('Change in workers size not implemented')
