__author__ = 'Olivier Van Cutsem'

import time, json
from threading import Timer
import logging
from os import listdir
from os.path import isfile, join
from drevent_manager import DReventManager, read_from_json
import requests

### LOGGER
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('DR-SERVER')
logger.setLevel(logging.INFO)

### CONFIGURATION
TIME_REFRESH_EVENTS = 10  # The sleeping time, between which the DR events are updated from the files
FOLDER_DR_EVENTS = './dr-custom-data/'
EXTERNAL_API = "http://127.0.0.1:5000"
MAPPING_DREVENT_API = {'dr_prices': 'add-dr-signal/price',
                       'dr_shed': 'add-dr-signal/shed',
                       'dr_limit': 'add-dr-signal/limit',
                       'dr_shift': 'add-dr-signal/shift',
                       'dr_track': 'add-dr-signal/track'}

### SERVER VARIABLES

# THE GLOBAL VARIABLE THAT KEEPS THE INFINITE LOOP RUNNING
KEEP_SERVER_ON = True

# DR events information and state, to keep track of change and trigger new ones
drevent_manager = DReventManager()

def stop_server():
    global KEEP_SERVER_ON
    KEEP_SERVER_ON = False

def init_event_scheduler():
    """
    Read the type of DR events from the file names
    :return:
    """
    global drevent_manager

    for f in listdir(FOLDER_DR_EVENTS):
        if isfile(join(FOLDER_DR_EVENTS, f)):
            name_dr = f.split(".")[0]
            drevent_manager.set_scheduled_amount(name_dr, 0)

def push_event_to_api(type_event, dr_data):

    r = requests.post('{}/{}'.format(EXTERNAL_API, MAPPING_DREVENT_API[type_event]), json=dr_data)

    if r.status_code == 200:
        logger.info("New event of type {0} sent to the external API".format(type_event))
    else:
        logger.warning("Error while sending an event of type {0} to the external API".format(type_event))

def add_dr_event(type_dr, dr_raw_data):

    # Decode the event and create the timeseries
    scheduled_time, data_dr = drevent_manager.decode_rawjson(type_dr, dr_raw_data)
    delay = max(0, scheduled_time - time.time())

    # Scheduling the event to be triggered later
    logger.info("Adding an event of type {0} to be scheduled at time {1} ({2} seconds from now)".format(type_dr, scheduled_time, delay))
    Timer(delay, push_event_to_api, (type_dr, data_dr)).start()

def update_dr_events():
    """
    Read the files describing the DR events and add them internally
    :return:
    """
    global drevent_manager

    for f in listdir(FOLDER_DR_EVENTS):
        filepath = join(FOLDER_DR_EVENTS, f)
        if isfile(join(FOLDER_DR_EVENTS, f)):
            type_dr = f.split(".")[0]

            # Get the list of event
            dr_list = read_from_json(filepath)
            if dr_list is None: continue
            if type(dr_list) is not list:
                logger.warning("Could not read events in {} because this is not a list".format(f))
                continue

            # Compare the last stored length with the current file list length
            if len(dr_list) > drevent_manager.get_scheduled_amount(type_dr):
                for i in range(len(dr_list) - drevent_manager.get_scheduled_amount(type_dr)):
                    add_dr_event(type_dr, dr_list[i])
                    drevent_manager.set_scheduled_amount(type_dr, len(dr_list))


if __name__ == '__main__':

    logger.info("#")
    logger.info("### RUNNING THE CUSTOM DR SERVER ###")
    logger.info("#")

    # Init the scheduler state to keep track of the updates
    init_event_scheduler()

    # Run the server infinite loop
    while KEEP_SERVER_ON:

        # Read the events list, check if there is new ones and add them
        logger.info(" Updating the event list")
        update_dr_events()

        # Sleep
        time.sleep(TIME_REFRESH_EVENTS)

    logger.info("--- KILLING THE CUSTOM DR SERVER ---")
