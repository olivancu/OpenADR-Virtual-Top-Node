# !flask/bin/python
from flask import Flask, request, g
import json
import time
from threading import Timer
import logging
from os import listdir
from os.path import isfile, join
import threading
from drevent_manager import DReventManager, read_from_json

app = Flask(__name__)

### LOGGER
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('DR-SERVER')
logger.setLevel(logging.INFO)

### CONFIGURATION
TIME_REFRESH_EVENTS = 10  # The sleeping time, between which the DR events are updated from the files
FOLDER_DR_EVENTS = './dr-custom-data/'
EXTERNAL_API = "http://127.0.0.1:5000"

list_dr_events = ['dr_prices','dr_shed', 'dr_limit', 'dr_shift', 'dr_track']

### SERVER VARIABLES

KEEP_READING_FILE = True

# DR events information and state, to keep track of change and trigger new ones
dr_manager = DReventManager()

def get_drevent_manager():
    return dr_manager

#
#### --- Flask API --- ####
#

def print_receive_data(data_type, data_payload):
    print "Receive {} signal from the DR server:".format(data_type)
    print data_payload

# - Test
@app.route('/')
def api_root():
    return 'Welcome to the Solar+ DR Server'


@app.route('/get-all-signal', methods=['GET'])
def get_all_signal():
    return get_dr_signal(None)

@app.route('/get-dr-signal/<type_dr>', methods=['GET'])
def get_dr_signal(type_dr):

    st = request.args.get('startdate')
    et = request.args.get('enddate')

    timeframe = None
    if (st is not None) and (et is not None):
        timeframe = (st, et)

    ev_manager = get_drevent_manager()
    list_events = ev_manager.get_available_events(type_dr, timeframe)

    return json.dumps(list_events)

#
#### --- File management to update the DR events available --- ####
#

def init_event_scheduler():
    """
    Read the type of DR events from the file names
    :return:
    """
    global dr_manager

    for f in listdir(FOLDER_DR_EVENTS):
        if isfile(join(FOLDER_DR_EVENTS, f)):
            name_dr = f.split(".")[0]
            dr_manager.set_scheduled_amount(name_dr, 0)

def push_event_to_queue(dr_data):

    global dr_manager

    dr_manager.add_available_event(dr_data)

def add_dr_event(type_dr, dr_raw_data):

    # Decode the event and create the timeseries
    notif_time, data_dr = dr_manager.decode_rawjson(type_dr, dr_raw_data)

    delay = max(0, notif_time - time.time())

    # Scheduling the event to be triggered later
    logger.info("Adding an event of type {0} to be available at time {1} ({2} seconds from now)".format(type_dr, notif_time, delay))
    Timer(delay, push_event_to_queue, (data_dr,)).start()

def update_dr_events():
    """
    Read the files describing the DR events and add them internally
    :return:
    """
    global dr_manager

    for f in listdir(FOLDER_DR_EVENTS):
        filepath = join(FOLDER_DR_EVENTS, f)
        if isfile(join(FOLDER_DR_EVENTS, f)):
            extension_file = f.split(".")[1]
            type_dr = f.split(".")[0]

            if extension_file == 'json':

                # Get the list of event
                dr_list = read_from_json(filepath)
                if dr_list is None: continue
                if type(dr_list) is not list:
                    logger.warning("Could not read events in {} because this is not a list".format(f))
                    continue

                # Compare the last stored length with the current file list length
                if len(dr_list) > dr_manager.get_scheduled_amount(type_dr):
                    for i in range(len(dr_list) - dr_manager.get_scheduled_amount(type_dr)):
                        add_dr_event(type_dr, dr_list[i])
                    dr_manager.set_scheduled_amount(type_dr, len(dr_list))

#### --- FIlE READER PROCESS --- ####

def file_reading_loop():
    global KEEP_READING_FILE

    # Init the scheduler state to keep track of the updates
    init_event_scheduler()

    # Run the server infinite loop
    while KEEP_READING_FILE:
        # Read the events list, check if there is new ones and add them
        logger.info(" Updating the event list")
        update_dr_events()

        # Sleep
        time.sleep(TIME_REFRESH_EVENTS)


if __name__ == '__main__':
    logger.info("#")
    logger.info("### RUNNING THE CUSTOM DR SERVER ###")
    logger.info("#")

    t = threading.Thread(target=file_reading_loop)
    t.start()
    app.run(debug=True, use_reloader=False)
    t.join()

    logger.info("--- KILLING THE CUSTOM DR SERVER ---")