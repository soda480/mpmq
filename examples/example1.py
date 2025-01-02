import logging
from faker import Faker
from time import sleep
from random import randint
from mpmq import MPmq
from progress1bar import ProgressBar

logger = logging.getLogger(__name__)

TOTAL_ITEMS = 200
BACKGROUND_PROCESSES = 5

class PoolBar(MPmq):
    def __init__(self, **kwargs):
        super(PoolBar, self).__init__(**kwargs)
        config = {
            'total': TOTAL_ITEMS,
            'clear_alias': True,
            'show_complete': False,
            'show_prefix': False,
            'show_duration': True,
            'show_bar': False,
            'completed_message': f'All background processes done - completed processing {TOTAL_ITEMS} items.',
            'regex': {'count': r'^.* processed item .*$', 'alias': r'^(?P<value>.*)$'}
        }
        self.progress_bar = ProgressBar(**config)

    def process_message(self, offset, message):
        self.progress_bar.match(message)

def get_process_data(count):
    fake = Faker()
    process_data = []
    for _ in range(count):
        process_data.append({
            'worker_id': fake.first_name(),
            'items': [fake.vin() for _ in range(int(TOTAL_ITEMS/count))]})
    return process_data

def do_work(worker_id=None, items=None):
    for item in items:
        logger.debug(f'{worker_id} processed item {item}')
        sleep(randint(10,100)/100)

def main():
    process_data = get_process_data(BACKGROUND_PROCESSES)
    worker_ids = [process['worker_id'] for process in process_data]
    print(f"\nThe following workers: {', '.join(worker_ids)} will process a total of {TOTAL_ITEMS} items.")
    print('\nShowing worker status using ProgressBar:')
    PoolBar(function=do_work, process_data=process_data).execute(raise_if_error=True)

if __name__ == '__main__':
    main()
