
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

import logging
from logging import Handler
from functools import wraps

logger = logging.getLogger(__name__)


class QueueHandler(Handler):
    """ subclass Handler enabling log messages to be sent to message queue
    """
    def __init__(self, message_queue, offset):
        super(QueueHandler, self).__init__()
        self.message_queue = message_queue
        self.offset = offset

    def emit(self, record):
        message = record.msg

        if record.levelno >= 40:
            message = f'ERROR: {message}'
        elif record.levelno >= 30:
            message = f'WARN: {message}'
        elif record.levelno == 20:
            message = f'INFO: {message}'

        message = f'#{self.offset}-{message}'
        self.message_queue.put(message)


def queue_handler(function):
    """ adds QueueHandler to rootLogger in order to send log messages to a message queue
    """

    @wraps(function)
    def _queue_handler(*args, **kwargs):
        """ internal decorator for message queue handler
        """
        root_logger = logging.getLogger()

        offset = kwargs.pop('offset', 0)
        message_queue = kwargs.pop('message_queue', None)
        result_queue = kwargs.pop('result_queue', None)
        result = None
        if message_queue:
            logger.debug(f"configuring message queue log handler for '{function.__name__}' offset {offset}")
            handler = QueueHandler(message_queue, offset)
            log_formatter = logging.Formatter('%(asctime)s %(processName)s %(name)s [%(funcName)s] %(levelname)s %(message)s')
            handler.setFormatter(log_formatter)
            root_logger.addHandler(handler)
            root_logger.setLevel(logging.DEBUG)

        try:
            result = function(*args, **kwargs)
            return result

        except Exception as exception:
            result = exception
            logger.error(str(exception), exc_info=True)
            # log control message that an error occurred
            logger.debug('ERROR')

        finally:
            # add result to result queue with offset index
            if result_queue:
                logger.debug(f"adding '{function.__name__}' offset {offset} result to result queue")
                result_queue.put({
                    offset: result
                })
            logger.debug(f'execution of {function.__name__} offset {offset} ended')
            # log control message that method completed
            logger.debug('DONE')
            if message_queue:
                root_logger.removeHandler(handler)

    return _queue_handler


class QueueHandlerDecorator():
    """ QueueHandlerDecorator to facilitate pickling of decorated functions with multiprocessing
    """
    def __init__(self, function):
        """ class constructor
        """
        self.function = function

    def __call__(self, *args, **kwargs):
        """ decorate function with queue handler
        """
        logger.debug(f'decorating function {self.function.__name__} with queue_handler')
        return queue_handler(self.function)(*args, **kwargs)
