'''
The Slurm runner creates sbatch scripts that are submitted to Slurm to be run.

The description of the run and its jobs (subtasks) are stored on disk in a json
file. The json file is saved automatically after a SlurmRun is submitted to
Slurm. The SlurmRun instance can be reloaded from this json file (see
SlurmRun.from_file).
'''

# TODO: Make the depencies a list[str] so the json is smaller

# __future__ import
from __future__ import annotations

# Standard import
import json
import re
import os

from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from time import time

# External libs import
import pydantic
from pydantic import Field

# RunRunner import
from runrunner.base import Status, Job, Run
from runrunner.logger import Log
from runrunner.utils import simple_run
from runrunner.utils import quote
from runrunner.utils import timestampedname

# Constants
WAIT_CHECK_INTERVAL = 1.0
_SRUN_START_ = '----- srun start -----'
_SRUN_END_ = '----- srun end -----'
_START_TIME_ = 'Start time'
_END_TIME_ = 'End time'

# -- Precompiled Regex --
# Extract the batch job number for the sbatch command output
_regex_sbatch_stdout_ = re.compile(r'^Submitted batch job (\d+)$')
# Extract the name and number for a filename of the form 'name-number'
_regex_slurmrun_name_ = re.compile(r'(.*)-(\d+)')
# Extract the job information given by Slurm via scontrol show job $jobid
_regex_slurm_scontrol_show_job = re.compile(r'[^\s]+=[^\s]+')

# SBATCH options
# Extract the --array options from a string
sbatch_option_array_pattern = re.compile('^(-)?a(rray)')
array_task_key_pattern = re.compile(r' ArrayTaskId=(\d+-?\d*%?\d*) ')
array_task_id_pattern = re.compile('[-%]')


def add_to_queue(
        cmd: str | list[str],
        path: str | Path | list[str] | list[Path] | None = None,
        name: str | None = None,
        parallel_jobs: int = None,
        dependencies: SlurmRun | list[SlurmRun] | None = None,
        base_dir: str | Path = None,
        sbatch_options: list[str] = None,
        srun_options: list[str] = None,
        output_path: str | Path | list[str] | list[Path] | None = None,
        **kwargs: str

) -> SlurmRun:
    '''Create a SlurmRun for with the list of `cmd`.

    This function is a simplified way to create SlurmRun instances.

     Parameters:
         cmd: str | list[str]
            The command(s) as string(s).
        path: str | Path | list[str] | list[Path] | None
            The working directory(ies) from where the commands will be executed. If the
            parameters is a single value, this value will be used for all the cmd. If
            path is a list, the length of the list must be the same as the number of
            commands. If None, use the current working directory.
        name: str | None
            A name given to the run that will be use in the saved files. If
            None, a unique name will be created. If a previous run with the same name is
            detected in the log directory, a number will be appended or incremented so
            the name is unique.
        base_dir: str | Path
            A directory where the sbatch script, the json, the stdout and stderr files
            will be created. If the directory does not exist, it will be created. By
            default, use the current working directory.
        parallel_jobs: int
            Number of jobs to run in parallel. If None (default) will be set to the
            amount of jobs created in this run.
        dependencies: SlurmRun | list[SlurmRun] | None
            The command(s) will wait for all `dependencies` to finish before starting.
        sbatch_options: list[str]
            A list of options that will be used in the sbatch scripts.
            Example: ['--mem-per-cpu=3000', '--exclude=ethnode[23-30]']
        srun_options: list[str]
            A list of options that will be used when running srun.
            Example: ['--cpu-freq=high']
        output_path: str | Path | list[str] | list[Path] | None
            The output file(s) for the commands output to be piped to by Slurm. If the
            parameters is a single value, this value will be used for all the cmd. If
            path is a list, the length of the list must be the same as the number of
            commands. If None, use the default Slurm .out file of the sbatch script.
    Returns
    -------
        slurm_run: SlurmRun
            An instance of SlurmRun
    '''
    # Input check
    if isinstance(cmd, str):
        cmd = [cmd]
    path = path or Path()
    if isinstance(path, str) or isinstance(path, Path):
        path = [path] * len(cmd)
    if len(cmd) != len(path):
        Log.error('The number of paths should be 1 or equal to the number of commands.')
    if not isinstance(output_path, list):
        output_path = [output_path] * len(cmd)
    if len(cmd) != len(output_path):
        Log.error('The number of output paths should be 1'
                  ' or equal to the number of commands.')
    if isinstance(dependencies, SlurmRun):
        dependencies = [dependencies]

    # Verify the SBATCH options -- Allow user to override
    if sbatch_options is not None:
        array_options = re.findall(sbatch_option_array_pattern, ' '.join(sbatch_options))
        array_options = [re.search(r'%(\d+)', option) for option in array_options
                         if re.search(r'%(\d+)', option) is not None]
        if len(array_options) > 0:
            if len(array_options) > 1:
                Log.warn('Detected multiple array specifications in '
                      f' SlurmRun Sbatch Options list for job {name}. Selecting first.')
            parallel_jobs = int(array_options[0][1])
    if parallel_jobs is None:
        parallel_jobs = len(cmd)

    slurm_run = SlurmRun(
        name=name,
        base_dir=base_dir,
        dependencies=dependencies or [],
        parallel_jobs=parallel_jobs,
        sbatch_options=sbatch_options or [],
        srun_options=srun_options or []
    )
    for c, p, o in zip(cmd, path, output_path):
        slurm_run.add_job(cmd=c, working_dir=p, output=o)
    return slurm_run.submit()


class SlurmJob(pydantic.BaseModel, Job):
    '''Defines a SlurmJob.

    A SlurmJob is a unit of work to be done by Slurm. Usually corresponding to a single
    command
    executed via srun. One or more SlurmJob are combined in a SlurmRun. The SlurmJob
    can be created and passed to a SlurmRun at its creation or added using the
    SlurmRun.add_job(...) function.

    The stdout_file, stderr_file and slurm_job_id are set by SlurmRun when the job
    is submitted to Slurm and should not be set manually.

    Properties
    ----------
    cmd: str
        The command to be executed as a string. The command should not include the
        srun call.
    working_dir: Path
        The working directory from where the command will be called. This is not where
        the output files will be saved.
    output_file: Path
        The file where the commands output should be piped to by Slurm. Default is none,
        using the general slurm's .out file as specified in stdout_file.
    stdout_file: Path
        The path to the standard output file. This value is set by SlurmRun when
        the jobs are submitted to Slurm. Be aware that this file includes a
        header and footer needed by RunRunner. To get the stdout without
        the header and footer use the SlurmJob.stdout property.
    stderr_file: Path
        The path to the standard error file. This value is set by SlurmRun when
        the jobs are submitted to Slurm.
    slurm_job_id: str
        The Slurm ID of the job. This value is set by SlurmRun when
        the jobs are submitted to Slurm.
    '''

    cmd: str
    working_dir: Path = Field(default_factory=Path)
    output_file: Path = None
    stdout_file: Path = None
    stderr_file: Path = None
    slurm_job_id: str = None

    # Properties derived by SlurmRun parent
    job_state: str = None
    start_time_stamp: int = None
    end_time_stamp: int = None
    submit_time_stamp: int = None
    job_restarts: int = None
    job_qos: str = None
    job_partition: str = None
    job_nodes: str = None

    def __init__(self, **data: list) -> None:
        '''Initialise the SlurmJob.'''
        super().__init__(**data)

    @property
    def status(self) -> Status:
        '''Return the Status of the job.'''
        if self.job_state is None:
            if (self.stderr_file is not None and self.stderr_file.exists() and os.stat(
                    self.stderr_file).st_size > 0):
                return Status.ERROR
            elif (self.stdout_file is not None and self.stdout_file.exists() and os.stat(
                    self.stdout_file).st_size > 0):
                return Status.COMPLETED
            return Status.NOTSET
        return Status.from_slurm_string(self.job_state)

    @property
    def runtime(self) -> str:
        '''Return the Slurm Job run time.'''
        # To prevent certain slurm defaults giving wrong indications
        if self.status == Status.WAITING:
            return str(timedelta(0))  # Job hasn't started yet
        if self.start_time is None or self.end_time is None:
            return None
        if self.status == Status.RUNNING:
            # When the Job is running, end time is the latest possible end time
            return str(datetime.now() - self.start_time)
        return str(self.start_time - self.end_time)

    @property
    def start_time(self) -> datetime:
        '''Return the start time of the job.'''
        if self.start_time_stamp is not None:
            if self.start_time_stamp == 0:
                return None
            return datetime.fromtimestamp(
                self.start_time_stamp)
        return None

    @property
    def end_time(self) -> datetime:
        '''Return the end time of the job.'''
        if self.end_time_stamp is not None:
            if self.end_time_stamp == 0:
                return None
            return datetime.fromtimestamp(self.end_time_stamp)
        return None

    @property
    def submit_time(self) -> datetime:
        '''Return the submit time of the job.'''
        if self.submit_time_stamp is not None:
            return datetime.fromtimestamp(self.submit_time_stamp)
        return None

    @property
    def partition(self) -> str:
        '''Return the partition of the job.'''
        if self.job_partition is not None:
            return self.job_partition
        return ''

    @property
    def restarts(self) -> int:
        '''Return the amount of times the job was restarted.'''
        if self.job_restarts is not None:
            return self.job_restarts
        return -1

    @property
    def nodes(self) -> str:
        '''Return the node names the job is running on.'''
        if self.job_nodes is not None:
            return ' '.join([
                alloc_node['nodename']
                for alloc_node in self.job_nodes])
        return ''

    @property
    def qos(self) -> str:
        '''Return the Quality of Service of the job.'''
        if self.job_qos is not None:
            return self.job_qos
        return ''

    @property
    def stdout(self) -> str:
        '''Return the standard output of the job (without RunRunner header/footer).'''
        header_split = self._stdout_raw_.split(_SRUN_START_)
        if len(header_split) > 1:
            return header_split[1].split(_SRUN_END_)[0]
        else:
            return ''

    @property
    def stderr(self) -> str:
        '''Return the standard error output of the job.'''
        if self.stderr_file.is_file():
            with open(self.stderr_file, 'r') as f:
                return f.read()
        else:
            return ''

    @property
    def job_log(self) -> dict[str, str]:
        '''Return the job log.

        The log contains information about the job execution extracted from parsing
        the job stdout header and footer. The information is injected
        by the sbatch script created by SlurmRun.
        '''
        raw = self._stdout_raw_
        header = raw.split(_SRUN_START_)
        footer = raw.split(_SRUN_END_)
        if len(footer) == 1:  # No _SRUN_END_ string found
            lines = header[0]
        else:
            lines = header[0] + footer[1]
        log = {}
        for line in lines.splitlines():
            if line.find(':') > 0:
                key, value = line.split(':', maxsplit=1)
                log[key.strip()] = value.strip()
        return log

    @property
    def _stdout_raw_(self) -> str:
        '''Return the raw stdout (including RunRunner header and footer).'''
        if self.stdout_file.is_file():
            with open(self.stdout_file, 'r') as f:
                return f.read()
        else:
            return ''

    def kill(self) -> SlurmJob:
        '''Terminate the running job.'''
        Log.info(f'Killing SlurmJob {self.slurm_job_id}')
        simple_run(f'scancel {self.slurm_job_id}')
        return self

    def wait(self, timeout: float = None) -> SlurmJob:
        '''Wait for the job to complete (possibly with error).'''
        t0 = time()
        while self.status in [Status.RUNNING, Status.WAITING]:
            if (timeout is not None) and ((time() - t0) > timeout):
                raise TimeoutError
            sleep(WAIT_CHECK_INTERVAL)
        return self

    def update(self, job_info: dict) -> SlurmJob:
        '''Update the job details from Slurm.'''
        self.job_state = job_info['job_state'][0]
        self.start_time_stamp = job_info['start_time']['number']
        self.end_time_stamp = job_info['end_time']['number']
        self.submit_time_stamp = job_info['submit_time']['number']
        self.job_restarts = job_info['restart_cnt']
        self.job_qos = job_info['qos']
        self.job_partition = job_info['partition']
        if ('job_resources' in job_info and 'allocated_nodes'
            in job_info['job_resources']):
            self.job_nodes = job_info['job_resources']['allocated_nodes']
        return self


class SlurmRun(pydantic.BaseModel, Run):
    '''A group of jobs that can be executed on a Slurm scheduler.

    The jobs must be SlurmJob instances. They can be added at the initialisation
    of the SlurmRun or added iteratively using SlurmRun.add(...).

    A SlurmRun will create multiple files. The file names are based on the name
    of the SlurmRun and are saved in base_dir. The files are:
    - The description file (.json): a json file containing the needed information to
    recreate the SlurmRun instance (and its SlurmJob instances).
    - The sbatch script (.sh): a bash file used to submit the jobs to Slurm
    - The output and error files (.out and .err): the standard output and error
    stream of the jobs. One file per job.

    Properties
    ----------
    name: str
        The name of the SlurmRun. This name will be used to save the script, the
        description file (a json) and the output files of the jobs. If the name
        exists on the disk, a new name will be create by using the name followed by
        an underscore and a number. If the name already finish with an underscore and
        a number, this number will be incremented. For example: run1 -> run1_0001,
        runB_004 -> runB_005. If not provided, a random string will be created
        based on the current date and time (see function utils.timestampedname).
    base_dir: Path
        A path where the output files are created
    dependencies: list[SlurmRun]
        A list of SlurmRun corresponding to the dependencies of the SlurmRun
    sbatch_options: list[str]
        The list of sbatch options as strings
    srun_options: list[str]
        The list of srun options as strings
    jobs: list[SlurmJob]
        The list of jobs forming the run
    parallel_jobs: int
        The number of job to run in parallel. Default: 1
    submitted: bool
        Indicates if the jobs where submitted to Slurm or not
    run_id: str
        The slurm_id of the run
    '''

    name: str = Field(default_factory=timestampedname)
    base_dir: Path = Field(default_factory=Path)
    dependencies: list[SlurmRun | str] = []
    sbatch_options: list[str] = []
    srun_options: list[str] = []
    jobs: list[SlurmJob] = []
    parallel_jobs: int = 1
    submitted: bool = False
    run_id: str = None

    # Not saved in the json
    loaded_from_file: bool = Field(False, exclude=True)

    def __init__(self, **data: list) -> None:
        '''Initialise a SlurmRun.'''
        # Remove None value so the default is activated
        for key in ['name', 'base_dir', 'dependencies']:
            if key in data and data[key] is None:
                del data[key]

        super().__init__(**data)
        self.base_dir = self.base_dir.expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

        if not self.loaded_from_file:
            # Detect and manage if the name already exists
            if self.script_filepath.is_file():  # The name already exists
                # Extract some info from the name
                if match := _regex_slurmrun_name_.findall(self.name):
                    base_name = match[0][0]
                    number_of_digits = len(match[0][1])
                else:
                    base_name = self.name
                    number_of_digits = 3

                # Find the highest number
                names = [f.stem for f in self.base_dir.glob(f'{base_name}*.sh')]
                match = _regex_slurmrun_name_.findall('\n'.join(names))
                value = max([int(m[1]) for m in match]) if match else 0

                new_name = f'{base_name}-{value+1:0{number_of_digits}}'

                Log.info('Script file with the same name detected. '
                         f'Using a new unique name: {self.name} -> {new_name}')
                self.name = new_name
            # Save json (not perfect, but somewhat reserve the name)
            self.to_file()

    def add_job(self, cmd: str, working_dir: Path = None, output: Path = None) -> None:
        '''Add a job to the list of jobs. The name is created automatically.'''
        self.jobs.append(SlurmJob(
            cmd=cmd,
            working_dir=working_dir or self.base_dir,
            output_file=output,
            name=self.name + f'-{len(self.jobs):04}'))

    def submit(self) -> SlurmRun:
        '''Submit the run to the scheduler.'''
        if self.submitted:
            Log.error('Run already submitted.')

        sbatch_script = self.write_sbatch_script()
        process = simple_run(f'sbatch {quote(sbatch_script.resolve())}')
        if process.returncode != 0:
            Log.error('Error when submiting to sbatch\n'
                      f'----- stdout -----\n{process.stdout}\n'
                      f'----- stderr -----\n{process.stderr}\n')
        else:
            self.submitted = True
            self.run_id = _regex_sbatch_stdout_.findall(process.stdout)[0]

            for i, job in enumerate(self.jobs):
                # The 'i' follow the same numbering as the array in the
                # sbatch file. As far as we know, this should also
                # correspond to the job_id number from Slurm. Any 'safer'
                # way to assign the job_id would be welcomed.
                job.slurm_job_id = f'{self.run_id}_{i}'
                job.stdout_file = self.filepath(f'-{i:04}.out')
                job.stderr_file = self.filepath(f'-{i:04}.err')
            self.to_file()
            Log.info(f'Submitted a run to Slurm (job {self.run_id})')
        return self

    def filepath(self, suffix: str = '') -> Path:
        '''Get a Path to a file inside the base_dir.

        The Path is formed with the run name and an optional suffix.
        '''
        # Convert to a str so the suffix can be whatever we want
        return Path(str(self.base_dir / self.name) + suffix)

    @classmethod
    def from_file(cls, file: Path, load_dependencies: bool = False) -> SlurmRun:
        '''Load a SlurmRun from a json file.

        Args:
            file: Path to the JSON file to load the object from
            load_dependencies: If True, the dependecies in the file will also be loaded.
                If False, the dependencies will be filled with the run id string.
        '''
        with open(file, 'r') as f:
            data = json.load(f)
        data['loaded_from_file'] = True
        if not load_dependencies:
            # NOTE: Maybe dependency loading should be removed and only use ID
            # If the file is overwritten, will be saved as ids
            ids = [d if isinstance(d, str) else d['run_id']
                   for d in data['dependencies']]
            data['dependencies'] = []
        slurmrun = cls.parse_obj(data)
        if not load_dependencies:
            slurmrun.dependencies = ids
        slurmrun.get_slurm_job_details()
        return slurmrun

    def to_file(self) -> Path:
        '''Save the run description to a json file. Return a path to the file.'''
        Log.info(f'Saving run description to file {self.json_filepath}')
        with open(self.json_filepath, 'w') as f:
            f.write(self.json())
        return self.json_filepath

    def wait(self, timeout: int = None) -> SlurmRun:
        '''Wait for all the jobs in the run to finish.'''
        for j in self.jobs:
            j.wait(timeout=timeout)
        return self

    def kill(self) -> SlurmRun:
        '''Kill the run and all its jobs.'''
        Log.info(f'Killing SlurmRun {self.run_id}')
        simple_run(f'scancel {self.run_id}')
        return self

    def __repr__(self) -> str:
        '''Return a simple representation of the job.'''
        return f'SLURM_RUN {self.name}[jobs={len(self)}]'

    def __len__(self) -> int:
        '''Return the number of sub-runs.'''
        return self.jobs.__len__()

    def write_sbatch_script(self) -> Path:
        '''Write the sbatch script. Return the path to the file.'''
        with open(self.script_filepath, 'w') as f:
            f.write(self.sbatch_script)
        return self.script_filepath

    def get_slurm_job_details(self) -> None:
        '''Retrieve the latest job details from Slurm.'''
        if all(job.status not in [Status.RUNNING, Status.WAITING, Status.NOTSET]
               for job in self.jobs):  # No more jobs running
            return
        scontrol = simple_run(f'scontrol show job {self.run_id} --json')
        job_details = json.loads(scontrol.stdout)['jobs']
        for job_info in job_details:
            job_id = job_info['array_task_id']['number']
            self.jobs[job_id].update(job_info)
        if len(job_details) > 0:  # Possible changes, save to file
            self.to_file()

    @property
    def script_filepath(self) -> Path:
        '''Path the script file needed by sbatch.'''
        return self.filepath('.sh')

    @property
    def json_filepath(self) -> Path:
        '''Path to the json file containing the description of the run.'''
        return self.filepath('.json')

    @property
    def dependency_str(self) -> list[str]:
        '''Return the list of dependency ids.'''
        dep = [sr.run_id if isinstance(sr, SlurmRun) else sr for sr in self.dependencies]
        if dep:
            return 'afterany:' + ':'.join(dep)
        else:
            return ''

    # Slurm Run Properties
    @property
    def all_status(self) -> list[Status]:
        '''Get a list of the job statuses.'''
        self.get_slurm_job_details()
        return [job.status for job in self.jobs]

    @property
    def status(self) -> Status:
        '''Return the status of the run.'''
        status = self.all_status
        if any(s == Status.ERROR for s in status):
            return Status.ERROR
        elif any(s == Status.KILLED for s in status):
            return Status.KILLED
        elif any(s == Status.RUNNING for s in status):
            return Status.RUNNING
        elif any(s == Status.WAITING for s in status):
            return Status.WAITING
        elif all(s == Status.COMPLETED for s in status):
            return Status.COMPLETED
        return Status.NOTSET

    @property
    def runtime(self) -> str:
        '''Return the run time of the run.'''
        # Retrieve the maximum run time over all jobs
        run_times = [job.runtime for job in self.jobs if job.runtime is not None]
        return max(run_times) if run_times else ''

    @property
    def start_time(self) -> datetime:
        '''Return the start time of the run.'''
        start_times = [job.start_time for job in self.jobs if job.start_time is not None]
        if len(start_times) == 0:  # Job has not started yet
            return None
        return min(start_times)

    @property
    def end_time(self) -> datetime:
        '''Return the end time of the run.'''
        end_times = [job.start_time for job in self.jobs if job.start_time is not None]
        if len(end_times) == 0:  # Job has not finished yet
            return None
        return max(end_times)

    @property
    def submit_time(self) -> datetime:
        '''Return the submit time of the run.'''
        for job in self.jobs:
            if job.submit_time is not None:
                return job.submit_time
        return None

    @property
    def partition(self) -> str:
        '''Return the partition of the run.'''
        return ','.join(set([job.partition for job in self.jobs if job.partition != '']))

    @property
    def nodes(self) -> str:
        '''Return the node names the jobs are running on.'''
        return ','.join(set([job.nodes for job in self.jobs if job.nodes != '']))

    @property
    def qos(self) -> str:
        '''Return the Quality of Service of the run.'''
        return ','.join(set([job.qos for job in self.jobs if job.qos != '']))

    @property
    def sbatch_script(self) -> str:
        '''Return the bash script as a string to be passed as argument to sbatch.'''
        out_arr = ''
        if any([j.output_file is not None for j in self.jobs]):
            out_arr = '\n'.join(['OUT=(  \\',
                                *[f'\t{quote(job.output_file.expanduser())} \\'
                                  for job in self.jobs],
                                ')'])
        return '\n'.join([
            # script header --------------------------------------------------------
            '#!/bin/bash',
            '# Slurm sbatch script',
            '# Generated by: RunRunner',
            f"# Datetime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            '',
            # sbatch options -------------------------------------------------------
            *[f'#SBATCH {option}' for option in self.sbatch_options],
            f'#SBATCH --array=0-{len(self)-1}%{self.parallel_jobs}',
            f"#SBATCH --output={quote(self.filepath('-%4a.out'))}",
            f"#SBATCH --error={quote(self.filepath('-%4a.err'))}",
            f'#SBATCH --dependency={self.dependency_str}',
            '',
            # command array -------------------------------------------------------
            'CMD=(  \\',
            *[f'\t{quote(job.cmd)}  \\' for job in self.jobs],
            ')',
            # working dir array ----------------------------------------------------
            'WORKINGDIR=(  \\',
            *[f'\t{quote(job.working_dir.expanduser())} \\' for job in self.jobs],
            ')',
            # output file array ----------------------------------------------------
            f'{out_arr}',
            # print some info before the job ---------------------------------------
            'hostnamectl',
            'cd ${WORKINGDIR[$SLURM_ARRAY_TASK_ID]}',
            *[f'echo \"{name:>18}: {value}\"' for name, value in (
                ('Job name', '$SLURM_JOB_NAME'),
                ('Job ID', '$SLURM_JOB_ID'),
                ('Task array ID', '$SLURM_ARRAY_TASK_ID'),
                ('Working directory', '$(pwd)'),
                ('Command', '${CMD[$SLURM_ARRAY_TASK_ID]}'),
                (_START_TIME_, '$(date --rfc-3339=ns)'))],
            # start the job --------------------------------------------------------
            f'echo {_SRUN_START_}',
            ' '.join(['srun', *self.srun_options, '${CMD[$SLURM_ARRAY_TASK_ID]}',
                      '> ${OUT[$SLURM_ARRAY_TASK_ID]}' if len(out_arr) > 0 else '']),
            f'echo {_SRUN_END_}',
            # job finished ---------------------------------------------------------
            f'echo {_END_TIME_:>18}: $(date --rfc-3339=ns)',
            ''])  # Add an empty line at the end
