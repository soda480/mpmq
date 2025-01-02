
# Copyright (c) 2021 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import sys
import logging
import datetime
from time import sleep
from inspect import signature
from multiprocessing import Queue
from multiprocessing import Process
from queue import Queue as SimpleQueue
from queue import Empty

from mpmq.handler import QueueHandlerDecorator

logger = logging.getLogger(__name__)

TIMEOUT = 3


class NoActiveProcesses(Exception):
    """ Raise when NoActiveProcesses is used to signal end
    """
    pass


class MPmq():
    """ The mpmq module provides a convenient way to scale execution of a function across multiple input values by
        distributing the input across a specified number of background processes. It also provides the means for the
        caller to intercept and process messages from the background processes while they execute the function.
        It does this by configuring a custom log handler that sends the function's log messages to a thread-safe queue;
        several API's are provided for the caller to process the messages from the message queue. The number of
        processes along with the input data for each process is specified as a list of dictionaries. The number of
        elements in the list dictates the total number of processes to execute. The result of each function is returned
        as a list to the caller after all background workers complete.
    """
    def __init__(self, function, *, process_data=None, shared_data=None, processes_to_start=None, timeout=None):
        """ MPmq constructor
        """
        logger.debug('executing MPmq constructor')
        self.function = QueueHandlerDecorator(function)
        self._function = function
        self.process_data = [{}] if process_data is None else process_data
        self.shared_data = {} if shared_data is None else shared_data
        self.processes = {}
        self.message_queue = Queue()
        self.result_queue = Queue()
        self.process_queue = SimpleQueue()
        self.processes_to_start = processes_to_start if processes_to_start else len(self.process_data)
        self.timeout = timeout if timeout else TIMEOUT
        self.active_processes = 0
        self.completed_processes = 0

    def populate_process_queue(self):
        """ populate process queue from process data offset
        """
        logger.debug('populating the process queue')
        for offset, data in enumerate(self.process_data):
            item = (offset, data)
            logger.debug(f'adding {item} to the process queue')
            self.process_queue.put(item)
        logger.debug(f'added {self.process_queue.qsize()} items to the process queue')

    def start_processes(self):
        """ start processes
        """
        self.populate_process_queue()

        logger.debug(f'there are {self.process_queue.qsize()} items in the process queue')
        logger.debug(f'starting {self.processes_to_start} background processes')
        for _ in range(self.processes_to_start):
            if self.process_queue.empty():
                logger.debug('the process queue is empty - no more processes need to be started')
                break
            self.start_next_process()
        logger.info(f'started {self.active_processes} background processes')

    def on_start_process(self):
        pass

    def start_next_process(self):
        """ start next process in the process queue
        """
        (offset, process_data) = self.process_queue.get()
        kwargs = {
            'message_queue': self.message_queue,
            'offset': offset,
            'result_queue': self.result_queue
        }
        # if all function parameters have defaults or are variable keywords then
        # pass process_data and shared_data as key word arguments to the function
        # this ensures backwards compatability for older versions of mpmq
        function_signature = signature(self._function)
        use_kwargs = all(
            (parameter.default != parameter.empty) or (parameter.kind == parameter.VAR_KEYWORD)
            for parameter in function_signature.parameters.values())
        args = ()
        if use_kwargs:
            kwargs.update(**process_data)
            kwargs.update(**self.shared_data)
        else:
            args = (process_data, self.shared_data)
        process = Process(target=self.function, args=args, kwargs=kwargs)
        process.start()
        logger.info(f'started background process at offset:{offset} with id:{process.pid} name:{process.name}')
        # update processes dictionary with process meta-data for the process at offset
        self.processes[offset] = {
            'process': process,
            'start_time': datetime.datetime.now(),
            'stop_time': None,
            'duration': None
        }
        self.active_processes += 1
        self.on_start_process()

    def terminate_processes(self):
        """ terminate all active processes
        """
        for offset, meta in self.processes.items():
            process = meta['process']
            if not meta['process'].is_alive():
                continue
            logger.info(f"terminating process at offset:{offset} with id:{process.pid} name:{process.name}")
            process.terminate()
        self.active_processes = 0

    def purge_process_queue(self):
        """ purge process queue
        """
        logger.info('purging all items from the to process queue')
        while not self.process_queue.empty():
            logger.info(f'purged {self.process_queue.get()} from the to process queue')

    @staticmethod
    def get_duration(start_time, stop_time):
        """ return duartion based off start_time and stop_time
        """
        start = start_time.time().strftime('%H:%M:%S')
        stop = stop_time.time().strftime('%H:%M:%S')
        duration = str(datetime.datetime.strptime(stop, '%H:%M:%S') - datetime.datetime.strptime(start, '%H:%M:%S'))
        return duration

    def on_complete_process(self):
        pass

    def complete_process(self, offset):
        """ complete the process at offset
        """
        meta = self.processes[offset]
        process = meta['process']
        logger.info(f'process at offset:{offset} id:{process.pid} name:{process.name} has completed')
        meta['stop_time'] = datetime.datetime.now()
        meta['duration'] = self.get_duration(meta['start_time'], meta['stop_time'])
        logger.info(f"joining process at offset:{offset} with id:{process.pid} name:{process.name}")
        process.join(self.timeout)
        self.active_processes -= 1
        self.completed_processes += 1
        self.on_complete_process()

    def get_results(self):
        """ return results of function execution from all processes
        """
        logger.debug('getting results from all processes using the result queue')
        logger.debug(f'the result queue size is: {self.result_queue.qsize()}')
        results = []
        while True:
            try:
                result_data = self.result_queue.get(True, self.timeout)
                offset = result_data['offset']
                result = result_data['result']
                logger.debug(f'adding result of process at offset:{offset} to results')
                results.insert(offset, result)
            except Empty:
                logger.debug('the result queue is now empty')
                break
        self.result_queue.close()
        return results

    def get_message(self):
        """ return message from top of message queue
        """
        message = self.message_queue.get(False)
        match = re.match(r'^#(?P<offset>\d+)-(?P<control>DONE|ERROR)$', message)
        if match:
            return {
                'offset': int(match.group('offset')),
                'control': match.group('control'),
                'message': message
            }

        match = re.match(r'^#(?P<offset>\d+)-(?P<message>.*)$', message)
        if match:
            return {
                'offset': int(match.group('offset')),
                'control': None,
                'message': match.group('message')
            }
        raise ValueError(f'message {message} is not formatted correctly')

    def process_control_message(self, offset, control):
        """ process control message
        """
        if control == 'DONE':
            self.complete_process(offset)
            if self.process_queue.empty():
                logger.info('the to process queue is empty')
                if not self.active_processes:
                    raise NoActiveProcesses()
                logger.debug(f'there are {self.active_processes} background processes still alive')
            else:
                self.start_next_process()
        else:
            logger.info(f'error detected for process at offset:{offset}')
            self.purge_process_queue()

    def process_message(self, offset, message):
        """ process message
            to be overriden by child class
        """
        pass

    def run(self):
        """ start processes and process messages
        """
        logger.debug('executing run task')
        self.start_processes()
        while True:
            try:
                message = self.get_message()
                if message['control']:
                    self.process_control_message(message['offset'], message['control'])
                else:
                    self.process_message(message['offset'], message['message'])

            except NoActiveProcesses:
                logger.info('there are no more active processses - quitting')
                break

            except Empty:
                pass
        self.message_queue.close()

    def execute_run(self):
        """ wraps call to run
        """
        logger.debug('executing run task wrapper')
        self.run()

    def final(self):
        """ called in finally block
            to be overriden by child class
        """
        logger.debug('executing final task')

    @staticmethod
    def check_results(results):
        """ raise exception if any result is exception
        """
        logger.debug('checking results for errors')
        errors = []
        for offset, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(str(offset))
        if errors:
            raise Exception(f"the process at offset {', '.join(errors)} had errors")

    def execute(self, raise_if_error=False):
        """ public execute api
        """
        try:
            self.execute_run()
            results = self.get_results()
            if raise_if_error:
                self.check_results(results)
            return results

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt signal received - killing all active processes')
            self.terminate_processes()
            sys.exit(-1)

        finally:
            self.final()
