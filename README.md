# mpmq
[![GitHub Workflow Status](https://github.com/soda480/mpmq/workflows/build/badge.svg)](https://github.com/soda480/mpmq/actions)
[![vulnerabilities](https://img.shields.io/badge/vulnerabilities-None-brightgreen)](https://pypi.org/project/bandit/)
[![coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)](https://pybuilder.io/)
[![complexity](https://img.shields.io/badge/complexity-A-brightgreen)](https://radon.readthedocs.io/en/latest/api.html#module-radon.complexity)
[![PyPI version](https://badge.fury.io/py/mpmq.svg)](https://badge.fury.io/py/mpmq)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-teal)](https://www.python.org/downloads/)

The mpmq module enables seamless interprocess communication between a parent and child processes when parallelizing a task across multiple workers. The `MPmq` class defines a custom log handler that sends all log messages from child workers to a thread-safe queue that the parent can consume and handle. This is helpful in cases where you want the parent to show real-time progress of child workers as they execute a task.

### Installation
```bash
pip install mpmq
```

### `MPmq class`
```
mpmq.MPmq(function, process_data=None, shared_data=None, processes_to_start=None)
```
> `function` - the function represents the task you wish the child workers to execute

> `process_data` - list of dictionaries where each dictionary contains the arguments that will be sent to each background child process executing the function; the length of the list dictates the total number of processes that will be executed

> `shared_data` - a dictionary containing arbitrary data that will be sent to all processes as key word arguments

> `process_to_start` - the number of processes to initially start; this represents the number of concurrent processes that will be running. If the total number of processes is greater than this 
number then execution will be queued and executed to ensure that this concurrency is maintained

> **execute(raise_if_error=False)**
>> Start execution the process’s activity. If `raise_if_error` is set to True, an exception will be raised if any function encountered an error during execution.

> **process_message(offset, message)**
>> Process a message sent from one of the background workers executing the function. The `offset` represents the index of the executing Process; this number is the same as the corresponding index within the `process_data` list that was sent to the constructor. The `message` represents the message that was logged by the function. 

### Examples

 The primary intent is for the MPmq class to be used as a superclass where the subclass ovverrides the `process_message` method to handle messages coming in from the child workers. The following example demonstrate how this can be done.

#### [Worker Status as a Progress Bar](https://github.com/soda480/mpmq/blob/main/examples/example1.py)

The example parallizezes a task across multiple processes using a pool of worker processes. Status of each worker is shown as a Progress Bar, as each Child worker in the pool completes an item defined in the task the Parent updates a Progress Bar.

![example](https://raw.githubusercontent.com/soda480/mpmq/main/docs/images/example1.gif)


#### [Worker Status as a List](https://github.com/soda480/mpmq/blob/main/examples/example2.py)

The example parallizezes a task across multiple processes using a pool of worker processes. Status of each worker is shown using an array where each index of the array represents an individual worker, as each Child worker in the pool completes the associated item in the List is updated with the completed message.

![example](https://raw.githubusercontent.com/soda480/mpmq/main/docs/images/example2.gif)


### Projects using `mpmq`

* [`mpcurses`](https://pypi.org/project/mpcurses/) An abstraction of the Python curses and multiprocessing libraries providing function execution and runtime visualization capabilities

* [`mppbars`](https://pypi.org/project/mppbar/) Scale execution of a function across multiple across a number of background processes while displaying their execution status via a progress bar

* [`mp4ansi`](https://pypi.org/project/mp4ansi/) A simple ANSI-based terminal emulator that provides multi-processing capabilities

### Development

Clone the repository and ensure the latest version of Docker is installed on your development server.

Build the Docker image:
```sh
docker image build \
-t mpmq:latest .
```

Run the Docker container:
```sh
docker container run \
--rm \
-it \
-v $PWD:/code \
mpmq:latest \
bash
```

Execute the build:
```sh
pyb -X
```
