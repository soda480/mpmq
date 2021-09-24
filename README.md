# mpmq #
[![GitHub Workflow Status](https://github.com/soda480/mpmq/workflows/build/badge.svg)](https://github.com/soda480/mpmq/actions)
[![Code Coverage](https://codecov.io/gh/soda480/mpmq/branch/main/graph/badge.svg?token=SAEJLS4FCM)](https://codecov.io/gh/soda480/mpmq)
[![Code Grade](https://www.code-inspector.com/project/12270/status/svg)](https://frontend.code-inspector.com/project/12270/dashboard)
[![PyPI version](https://badge.fury.io/py/mpmq.svg)](https://badge.fury.io/py/mpmq)
[![python](https://img.shields.io/badge/python-3.9-teal)](https://www.python.org/downloads/)

Mpmq is an abstraction of the Python multiprocessing library providing execution pooling and message queuing capabilities. Mpmq can scale execution of a specified function across multiple background processes. It creates a log handler that sends all log messages from the running processes to a thread-safe queue. The main process reads the messages off the queue for processing. The number of processes along with the arguments to provide each process is specified as a list of dictionaries. The number of elements in the list will dictate the total number of processes to execute. The result of each function is read from the result queue and written to the respective dictionary element upon completion.

The main features are:

* execute function across multiple processes
* queue function execution
* create log handler that sends function log messages to thread-safe message queue
* process messages from log message queue
* maintain result of all executed functions
* terminate execution using keyboard interrupt


### Installation ###
```bash
pip install mpmq
```

### Examples ###

A simple example using mpmq:

```python
from mpmq import MPmq
import sys, logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(processName)s [%(funcName)s] %(levelname)s %(message)s")

def do_work(*args):
    logger.info(f"hello from process {args[0]['pid']}")
    return 10 + int(args[0]['pid'])

process_data = [{'pid': item} for item in range(3)]
MPmq(function=do_work, process_data=process_data).execute()
print(f"Total items processed {sum([item['result'] for item in process_data])}")
 ```

Executing the code above results in the following (for conciseness only INFO level messages are shown):

```Python
MainProcess [start_next_process] INFO started background process at offset:0 with id:1967 name:Process-1
MainProcess [start_next_process] INFO started background process at offset:1 with id:1968 name:Process-2
Process-1 [do_work] INFO hello from process 0
MainProcess [start_next_process] INFO started background process at offset:2 with id:1969 name:Process-3
MainProcess [start_processes] INFO started 3 background processes
Process-1 [_queue_handler] DEBUG adding 'do_work' offset:0 result to result queue
Process-1 [_queue_handler] DEBUG execution of do_work offset:0 ended
Process-1 [_queue_handler] DEBUG DONE
MainProcess [remove_active_process] INFO process at offset:0 id:1967 name:Process-1 has completed
Process-2 [do_work] INFO hello from process 1
Process-3 [do_work] INFO hello from process 2
Process-2 [_queue_handler] DEBUG adding 'do_work' offset:1 result to result queue
Process-3 [_queue_handler] DEBUG adding 'do_work' offset:2 result to result queue
Process-2 [_queue_handler] DEBUG execution of do_work offset:1 ended
Process-2 [_queue_handler] DEBUG DONE
Process-3 [_queue_handler] DEBUG execution of do_work offset:2 ended
Process-3 [_queue_handler] DEBUG DONE
MainProcess [process_control_message] INFO the to process queue is empty
MainProcess [remove_active_process] INFO process at offset:1 id:1968 name:Process-2 has completed
MainProcess [process_control_message] INFO the to process queue is empty
MainProcess [remove_active_process] INFO process at offset:2 id:1969 name:Process-3 has completed
MainProcess [process_control_message] INFO the to process queue is empty
MainProcess [run] INFO there are no more active processses - quitting
MainProcess [join_processes] INFO joined process at offset:0 with id:1967 name:Process-1
MainProcess [join_processes] INFO joined process at offset:1 with id:1968 name:Process-2
MainProcess [join_processes] INFO joined process at offset:2 with id:1969 name:Process-3
>>> print(f"Total items processed {sum([item['result'] for item in process_data])}")
Total items processed 33
```

### Projects using `mpmq` ###

* [`mpcurses`](https://pypi.org/project/mpcurses/) An abstraction of the Python curses and multiprocessing libraries providing function execution and runtime visualization capabilities

* [`mp4ansi`](https://pypi.org/project/mp4ansi/) A simple ANSI-based terminal emulator that provides multi-processing capabilities.

### Development ###

Clone the repository and ensure the latest version of Docker is installed on your development server.

Build the Docker image:
```sh
docker image build \
-t \
mpmq:latest .
```

Run the Docker container:
```sh
docker container run \
--rm \
-it \
-v $PWD:/code \
mpmq:latest \
/bin/sh
```

Execute the build:
```sh
pyb -X
```
