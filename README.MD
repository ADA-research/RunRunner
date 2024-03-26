# RunRunner - A Python handler for managing (Slurm)Jobs

RunRunner is a wrapper library for creating and managing subprocesses and their status', mainly focussed on using Slurm but (in absence) can also work with local jobs.

## Installation

Installation of the latest version is done using Pip:

pip install RunRunner

## Usage

RunRunner works with 'queues', either the local version or Slurm version. To use RunRunner, simply add the bash call you want to be executed to the queue with:

``add_to_queue''

By specifying Runner (an Enum from base.py), RunRunner determines whether to add to the local queue (local.py) or Slurm (Slurm.py). To check what arguments each queue accepts, see the add_to_queue implementations at the top of each respective file. The call to the queue returns a structured object (a LocalRun or SlurmRun) containing the data regarding the subprocess. A run consists of one or more jobs which will contains the actual subprocess call. To start a run after creation, one can simply .submit the run and .wait for it to be done. To verify if everything went correctly, a .Status is supplied which uses .Status enum from base.py.


## Credits

Developers:
* Thijs Snelleman
* Jeroen Rook
* Koen van der Blom (Inactive)
* Jeremy Gobeil (Original developer, inactive)