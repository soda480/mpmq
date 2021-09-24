#   -*- coding: utf-8 -*-  
import sys
import uuid
import logging
from time import sleep
from random import randint
from mpmq import MPmq

logger = logging.getLogger(__name__)


def get_process_data(count):
    process_data = []
    for _ in range(count):
        process_data.append({
            'uuid': str(uuid.uuid4()).split('-')[0]})
    return process_data


def do_something(*args):
    uuid = args[0]['uuid']
    logger.debug(f'processor id {uuid}')
    return 'X' * 1000000


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    process_data = get_process_data(10)
    mpcon = MPmq(function=do_something, process_data=process_data)

    print('Processing...')
    mpcon.execute(raise_if_error=True)
    for item in process_data:
        print(len(item['result']))


if __name__ == '__main__':

    main()
