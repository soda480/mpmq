
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
    """ multi-processing (MP) message queue controller
        execute function across multiple processes
        queue function execution
        queue function log messages to thread-safe message queue
        process messages from log message queue
        maintain result of all executed functions
        terminate execution using keyboard interrupt
    """
    def __init__(self, function, *, process_data=None, shared_data=None, processes_to_start=None, timeout=None):
        """ MPmq constructor
        """
        logger.debug('executing MPmq constructor')
        self.function = QueueHandlerDecorator(function)
        self.process_data = [{}] if process_data is None else process_data
        self.shared_data = {} if shared_data is None else shared_data
        self.active_processes = {}
        self.finished_processes = {}
        self.message_queue = Queue()
        self.result_queue = Queue()
        self.process_queue = SimpleQueue()
        self.processes_to_start = processes_to_start if processes_to_start else len(self.process_data)
        self.timeout = timeout if timeout else TIMEOUT

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
        logger.info(f'started {len(self.active_processes)} background processes')

    def start_next_process(self):
        """ start next process in the process queue
        """
        process_queue_data = self.process_queue.get()
        offset = process_queue_data[0]
        process_data = process_queue_data[1]
        process = Process(
            target=self.function,
            args=(process_data, self.shared_data),
            kwargs={
                'message_queue': self.message_queue,
                'offset': offset,
                'result_queue': self.result_queue})
        process.start()
        logger.info(f'started background process at offset:{offset} with id:{process.pid} name:{process.name}')
        # update active_processes dictionary with process meta-data for the process offset
        self.active_processes[offset] = {
            'process': process,
            'start_time': datetime.datetime.now()
        }

    def terminate_processes(self):
        """ terminate all active processes
        """
        for offset, process_data in self.active_processes.items():
            logger.info(f"terminating process at offset:{offset} with id:{process_data['process'].pid} name:{process_data['process'].name}")
            process_data['process'].terminate()

    def join_processes(self):
        """ join processes
        """
        for offset, process_data in self.finished_processes.items():
            logger.info(f"joined process at offset:{offset} with id:{process_data['process'].pid} name:{process_data['process'].name}")
            process_data['process'].join(self.timeout)

    def purge_process_queue(self):
        """ purge process queue
        """
        logger.info('purging all items from the to process queue')
        while not self.process_queue.empty():
            logger.info(f'purged {self.process_queue.get()} from the to process queue')

    def get_end_time_duration(self, start_time):
        """ return tuple of end_time and duration based off start_time
        """
        begin_time = start_time.time().strftime('%H:%M:%S')
        end_time = datetime.datetime.now().time().strftime('%H:%M:%S')
        duration = str(datetime.datetime.strptime(end_time, '%H:%M:%S') - datetime.datetime.strptime(begin_time, '%H:%M:%S'))
        return end_time, duration

    def remove_active_process(self, offset):
        """ remove active process at offset
        """
        process_data = self.active_processes.pop(offset, None)
        process = process_data['process']
        logger.info(f'process at offset:{offset} id:{process.pid} name:{process.name} has completed')
        # compute duration and add to finished processes
        end_time, duration = self.get_end_time_duration(process_data['start_time'])
        process_data['end_time'] = end_time
        process_data['duration'] = duration
        self.finished_processes[offset] = process_data

    def update_result(self):
        """ update process data with result
        """
        logger.debug('updating process data with results')
        logger.debug(f'the result queue size is: {self.result_queue.qsize()}')
        logger.debug('updating process data with result from result queue')
        while True:
            try:
                result_data = self.result_queue.get(True, self.timeout)
                for offset, result in result_data.items():
                    logger.debug(f'adding result of process at offset:{offset} to process data')
                    self.process_data[offset]['result'] = result
            except Empty:
                logger.debug('result queue is empty')
                break
        # close result queue
        self.result_queue.close()

    def active_processes_empty(self):
        """ return True if active processes is empty else False
            method added to facilitate unit testing
        """
        # no active processes means its empty
        return not self.active_processes

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
        return {
            'offset': None,
            'control': None,
            'message': message
        }

    def process_control_message(self, offset, control):
        """ process control message
        """
        if control == 'DONE':
            self.remove_active_process(offset)
            if self.process_queue.empty():
                logger.info('the to process queue is empty')
                if self.active_processes_empty():
                    raise NoActiveProcesses()
            else:
                self.start_next_process()
        else:
            logger.info(f'error detected for process at offset:{offset}')
            self.purge_process_queue()

    def process_non_control_message(self, offset, message):
        """ process non-control message
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
                    self.process_non_control_message(message['offset'], message['message'])

            except NoActiveProcesses:
                logger.info('there are no more active processses - quitting')
                break

            except Empty:
                pass
        # close message queue
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

    def check_result(self):
        """ raise exception if any result in process data is exception
        """
        logger.debug('checking results for errors')
        errors = []
        for index, process in enumerate(self.process_data):
            if isinstance(process.get('result'), Exception):
                errors.append(str(index))
        if errors:
            raise Exception(f"the process at index {','.join(errors)} had errors")

    def execute(self, raise_if_error=False):
        """ public execute api
        """
        try:
            self.execute_run()
            self.update_result()
            self.join_processes()
            if raise_if_error:
                self.check_result()

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt signal received - killing all active processes')
            self.terminate_processes()
            sys.exit(-1)

        finally:
            self.final()
