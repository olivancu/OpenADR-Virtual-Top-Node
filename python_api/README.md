# OpenADR API and custem Python DR server

## OpenADR API for pricing events

This section describes how to populate an official EPRI VTN server with Peak-Day Pricing events, without passing through the web UI.

1. Populate events in pdp_events.json file
2. run the script once: `python event_json_readers.py`

## Custom generic DR server

This repository also enables the deployment of a simple DR event scheduler, pushing data to a pre-deployed server and able to receive back informations.

1. Encode the DR events in the files located in the folder `dr-custom-data` according to the templates in `dr-custom-data-template`.

2. run the DR server: `python dr_custom_server.py`

3. The server will periodically read data from the `dr-custom-data` folder, checking for new event. 
As a new event flag is raised regarding the length of the corresponding json list, **any new event must be appended at the beginning of the list !**.
