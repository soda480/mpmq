# mpmq
[![GitHub Workflow Status](https://github.com/soda480/mpmq/workflows/build/badge.svg)](https://github.com/soda480/mpmq/actions)
[![vulnerabilities](https://img.shields.io/badge/vulnerabilities-None-brightgreen)](https://pypi.org/project/bandit/)
[![coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)](https://pybuilder.io/)
[![complexity](https://img.shields.io/badge/complexity-A-brightgreen)](https://radon.readthedocs.io/en/latest/api.html#module-radon.complexity)
[![PyPI version](https://badge.fury.io/py/mpmq.svg)](https://badge.fury.io/py/mpmq)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-teal)](https://www.python.org/downloads/)

The mpmq module provides a convenient way to scale execution of a function across multiple input values by distributing the input across a specified number of background processes. It also provides the means for the caller to intercept and process messages from the background processes while they execute the function. It does this by configuring a custom log handler that sends the function's log messages to a thread-safe queue; several API's are provided for the caller to process the messages from the message queue. The number of processes along with the input data for each process is specified as a list of dictionaries. The number of elements in the list dictates the total number of processes to execute. The result of each function is returned as a list to the caller after all background workers complete.

The main features are:

* execute function across multiple processes
* queue function execution
* create log handler that sends function log messages to thread-safe message queue
* process messages from log message queue
* maintain result of all executed functions
* terminate execution using keyboard interrupt

### Installation
```bash
pip install mpmq
```

### `MPmq class`
```
mpmq.MPmq(function, process_data=None, shared_data=None, processes_to_start=None)
```
> `function` - the function to execute

> `process_data` - list of dictionaries where each dictionary contains the key word arguments that will be sent to each background process executing the function; the length of the list dictates the total number of processes that will be executed

> `shared_data` - a dictionary containing arbitrary data that will be sent to all processes as key word arguments

> `process_to_start` - the number of processes to initially start; this represents the number of concurrent processes that will be running. If the total number of processes is greater than this 
number then execution will be queued and executed to ensure that this concurrency is maintained

> **execute(raise_if_error=False)**
>> Start execution the process’s activity. If `raise_if_error` is set to True, an exception will be raised if any function encountered an error during execution.

> **process_message(offset, message)**
>> Process a message sent from one of the background processes executing the function. The `offset` represents the index of the executing Process; this number is the same as the corresponding index within the `process_data` list that was sent to the constructor. The `message` represents the message that was logged by the function.

### Examples

A simple example using mpmq:

```python
from mpmq import MPmq
import sys, logging
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(processName)s [%(funcName)s] %(levelname)s %(message)s")

def do_work(pid=None, number=None):
    logger.info(f"hello from process: {pid}")
    return number + int(pid)

process_data = [{'pid': item} for item in range(3)]
results = MPmq(function=do_work, process_data=process_data, shared_data={'number': 10}).execute()
print(f"Results: {', '.join(str(num) for num in results)}")
 ```

Executing the code above results in the following (for conciseness only INFO level messages are shown):

```Python
MainProcess [start_next_process] INFO started background process at offset:0 with id:862 name:Process-1
Process-1 [do_work] INFO hello from process: 0
MainProcess [start_next_process] INFO started background process at offset:1 with id:863 name:Process-2
MainProcess [start_next_process] INFO started background process at offset:2 with id:865 name:Process-3
MainProcess [start_processes] INFO started 3 background processes
Process-2 [do_work] INFO hello from process: 1
Process-2 [_queue_handler] DEBUG adding 'do_work' offset:1 result to result queue
Process-3 [do_work] INFO hello from process: 2
Process-2 [_queue_handler] DEBUG execution of do_work offset:1 ended
Process-2 [_queue_handler] DEBUG DONE
Process-3 [_queue_handler] DEBUG adding 'do_work' offset:2 result to result queue
MainProcess [complete_process] INFO process at offset:1 id:863 name:Process-2 has completed
Process-3 [_queue_handler] DEBUG execution of do_work offset:2 ended
Process-3 [_queue_handler] DEBUG DONE
Process-1 [_queue_handler] DEBUG adding 'do_work' offset:0 result to result queue
Process-1 [_queue_handler] DEBUG execution of do_work offset:0 ended
Process-1 [_queue_handler] DEBUG DONE
MainProcess [complete_process] INFO joining process at offset:1 with id:863 name:Process-2
MainProcess [process_control_message] INFO the to process queue is empty
MainProcess [complete_process] INFO process at offset:2 id:865 name:Process-3 has completed
MainProcess [complete_process] INFO joining process at offset:2 with id:865 name:Process-3
MainProcess [process_control_message] INFO the to process queue is empty
MainProcess [complete_process] INFO process at offset:0 id:862 name:Process-1 has completed
MainProcess [complete_process] INFO joining process at offset:0 with id:862 name:Process-1
MainProcess [process_control_message] INFO the to process queue is empty
MainProcess [run] INFO there are no more active processses - quitting
>>> print(f"Results: {', '.join(str(num) for num in results)}")
Results: 10, 11, 12
```

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
