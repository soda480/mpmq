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
            'uuid': str(uuid.uuid4()).split('-')[0]
        })
    return process_data

def do_something(uuid=None, lower=None, upper=None):
    logger.debug(f'processor id {uuid}')
    total = randint(lower, upper)
    logger.debug(f'{uuid} processing total of {total}')
    for index in range(total):
        logger.debug(f'{uuid} processed {index}')
        sleep(.001)
    return total

def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    process_data = get_process_data(5)
    mpq = MPmq(
        function=do_something,
        process_data=process_data,
        shared_data={'lower': 1000, 'upper': 2000})
    print('Processing...')
    results = mpq.execute(raise_if_error=True)
    print(f"Total items processed {sum(result for result in results)}")

if __name__ == '__main__':
    main()
