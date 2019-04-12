__author__ = 'Olivier Van Cutsem'

import time, json
from threading import Timer
import logging
from os import listdir
from os.path import isfile, join

FORMAT = '%(asctime) %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('DR-SERVER')
logger.setLevel(logging.INFO)

### CONFIGURATION
TIME_REFRESH_EVENTS = 1
FOLDER_DR_EVENTS = './dr-custom-data/'

### SERVER VARIABLES

# THE GLOBAL VARIABLE THAT KEEPS THE INFINITE LOOP RUNNING
KEEP_SERVER_ON = True

# DR events information and state, to keep track of change and trigger new ones
event_scheduler = {}

def read_from_json(filename):
    """
    Read json data
    :return:
     - A JSON object of the file
    """
    data_json = None

    try:
        with open(filename, 'r') as input_file:
            try:
                data_json = json.load(input_file)
            except ValueError:
                print ('Could open {0} but failed to parse the json'.format(filename))
                return None
    except:
        print ('Cant open file {}'.format(filename))
        return None

    return data_json

def init_event_scheduler():
    """
    Read the type of DR events from the file names
    :return:
    """
    global event_scheduler

    for f in listdir(FOLDER_DR_EVENTS):
        if isfile(join(FOLDER_DR_EVENTS, f)):
            name_dr = f.split(".")[0]
            event_scheduler[name_dr] = {'current_length': 0}

def push_event_to_api(type_event, data):
    logger.info("Sending an event of type {0} to the external API".format(type_event))

def print_time():
    print "FROM print_time()", time.time()

def stop_server():
    global KEEP_SERVER_ON
    KEEP_SERVER_ON = False

def add_dr_event(type_dr, dr_event_json):

    # TODO analyse the event
    scheduled_time = 0
    delay = max(0, scheduled_time - time.time())

    logger.info("Adding an event of type {0} to be scheduled at time {1} ({2} seconds from now)".format(type_dr, scheduled_time, delay))
    Timer(delay, push_event_to_api, (type_dr)).start()

def update_dr_events():
    """
    Read the files describing the DR events and add them internally
    :return:
    """
    global event_scheduler

    for f in listdir(FOLDER_DR_EVENTS):
        filepath = join(FOLDER_DR_EVENTS, f)
        if isfile(join(FOLDER_DR_EVENTS, f)):
            type_dr = f.split(".")[0]

            # Get the list of event
            dr_list = read_from_json(filepath)
            if dr_list is None: continue

            # Compare the last stored length with the current file list length
            if len(dr_list) > event_scheduler[type_dr]["current_length"]:
                for i in range(event_scheduler[type_dr]["current_length"] - len(dr_list)):
                    add_dr_event(type_dr, dr_list[i])
                event_scheduler[type_dr]["current_length"] = len(dr_list)


if __name__ == '__main__':

    logger.info("#")
    logger.info("### RUNNING THE CUSTOM DR SERVER ###")
    logger.info("#")

    # data_to_send contains the final JSON to send to the fake DR server/database

    # --- Transform JSON encoded data into time-series
    while KEEP_SERVER_ON:

        update_dr_events()

        time.sleep(TIME_REFRESH_EVENTS)
        Timer(10, stop_server, ()).start()
        print time.time()

    logger.info("--- KILLING THE CUSTOM DR SERVER ---")
