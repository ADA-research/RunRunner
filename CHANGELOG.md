# Changelog for RunRunner

Notable changes to RunRunner are documented in this file.

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

