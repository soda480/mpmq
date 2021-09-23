[![GitHub Workflow Status](https://github.com/soda480/mpmq/workflows/build/badge.svg)](https://github.com/soda480/mpmq/actions)
[![Code Coverage](https://codecov.io/gh/soda480/mpmq/branch/main/graph/badge.svg?token=SAEJLS4FCM)](https://codecov.io/gh/soda480/mpmq)
[![Code Grade](https://www.code-inspector.com/project/12270/status/svg)](https://frontend.code-inspector.com/project/12270/dashboard)
[![PyPI version](https://badge.fury.io/py/mpmq.svg)](https://badge.fury.io/py/mpmq)

# mpmq #

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
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def do_work(*args):
    logger.info(f"hello from process {args[0]['pid']}")
    return 10 + int(args[0]['pid'])

process_data = [{'pid': item} for item in range(3)]
MPmq(function=do_work, process_data=process_data).execute()
print(f"Total items processed {sum([item['result'] for item in process_data])}")
 ```

Executing the code above results in the following (for conciseness only INFO level messages are shown):

```Python
INFO:mpmq.mpmq:started background process at offset 0 with process id 216
INFO:mpmq.mpmq:started background process at offset 1 with process id 217
INFO:__main__:hello from process 0
INFO:mpmq.mpmq:started background process at offset 2 with process id 218
INFO:mpmq.mpmq:started 3 background processes
INFO:__main__:hello from process 1
INFO:mpmq.mpmq:process at offset 0 process id 216 has completed
INFO:mpmq.mpmq:the to process queue is empty
INFO:__main__:hello from process 2
INFO:mpmq.mpmq:process at offset 1 process id 217 has completed
INFO:mpmq.mpmq:the to process queue is empty
INFO:mpmq.mpmq:process at offset 2 process id 218 has completed
INFO:mpmq.mpmq:the to process queue is empty
INFO:mpmq.mpmq:there are no more active processses - quitting
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
