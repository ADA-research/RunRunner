# Changelog for RunRunner

Notable changes to RunRunner are documented in this file.

## [0.1.9] 2024/12/20

### Added

- Replace white space option for naming Slurm run files

## [0.1.8] 2024/10/28

### Fixed
- SlurmJob Runtime computation when job is finished is now correct. Time of running jobs is formatted to be 2 decimals at maximum.
- SlurmRun no longer automatically refreshes its jobs details upon fetching its status, now instead this has to be done manually by the user by running .get_latest_job_details. Does still happen upon loading a a run from file.
- Better support for determining SlurmJob status for slurm ID's that can no longer be found in the Slurm DB

## [0.1.7.1] 2024/10/14

### Fixed
- Bug for SlurmJobs setting state to completed when actually the job is running

## [0.1.7] 2024/10/09

### Fixed
- SlurmRun.kill no longer kills each job and instead kills the whole batch at once

### Changed
- SlurmRun now extracts latest information from the JSON job data instead for improved stability
- A SlurmRun is considered waiting when one of its jobs is waiting instead of all jobs (Condition that no jobs are, killed, crashed or running)

### Removed
- SlurmJobs no longer have the requeues property

## [0.1.6.4] 2024/08/27

### Fixed
- Minor release for a bugfix regarding the retrieval of slurm job status for a single job

## [0.1.6.3] 2024/08/26

### Fixed
- Minor release for a bugfix regarding the retrieval of slurm job status for a single job

### Changed
- Updated logging functionality

## [0.1.6] 2024/08/15

### Changed
- When checking SlurmRun jobs status, this is now requested in one subprocess call instead of N.
- Logging has been improved and now has file support.

## [0.1.5] 2024/08/07

### Changed
- When loading a SlurmRun from file, the dependencies are only loaded with only their IDs when load_dependencies is false. Before it was just empty.

## [0.1.4] - 2024/07/17

### Added
- Shared base class for Local/Slurm Run/Job objects
- The stdout/stderr for Local runs is now configurable
- Local Jobs can be started at the will of the user with new optional add_to_queue/constructor argument
- SlurmJobs inherit many new properties from scontrol, and SlurmRuns offer the same options.


## [0.1.3] - 2024/04/15

### Changed
- Changed the loading from file to ignore dependencies in the JSON by default to avoid unnecesarry IO.

### Fixed
- Bug in the SlurmJob object causing instances to share slurm_job_details dict.

## [0.1.2] - 2024/03/28

### Changed
- The amount of parallel jobs is by default now None and will be calculated by the number of submitted jobs
- The logging statement for saving .json now has a verbose option to reduce excess logging when submitting a run

## [0.1.0] - 2024/03/26

### Added
- Support for Slurm output piping array through add_job_to_queue
- Expanded Slurm status details, now all Slurm info on a job is available through the slurm_job_details. This is used to determine the job status (A simplified representation of slurm job status.)

### Changed
- Replaced the mechanic with which RunRunner Slurm job status are detected. This now uses scontrol show job output instead of file detection, which caused latency issues when the commands were started within a node (e.g. the mother process was a slurm job)

### Fixed
- Changed the control flow of SBATCH options given to RunRunner's Slurm queue: The amount of parallel jobs will be replaced if the --array option is given with a different amount of parallel jobs.
- LocalJobs currently had no logical flow if the Popen threw an exception. This has been implemented and shows the user the exception message created by subprocess.Popen.
- The Slurm job .wait() could run into exceptional delays due to the file-checking mechanic, if the managing job was being executed on a different node than the actual job. This has been fixed with a new monitoring system that uses slurm mechanics.

## [0.0.3] - 2022/10/17
### Added

### Changed

### Fixed
- Fixed bug in `timing.py` function `format_seconds()` which had cascading effects causing e.g. job statuses in LOCAL runner not to be updated when they should and getting stuck in an infinite loop for running times above 60 seconds.

## [Unreleased]

### Added

### Changed

### Fixed

