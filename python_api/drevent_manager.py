__author__ = 'Olivier Van Cutsem'

import time
from datetime import datetime
import json
import os, sys
from dateutil.parser import parse

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


# Load the config and the CostCalculator Module
costcalculator_path = read_from_json("./settings.json")["cost_calculator_path"]
sys.path.append(os.path.abspath(costcalculator_path))
from cost_calculator.cost_calculator import CostCalculator
from cost_calculator.tariff_structure import *
from openei_tariff.openei_tariff_analyzer import *

class DReventManager():

    def __init__(self):
        self.__events_state = {}

        self.__tariff_manager = CostCalculator()


    def get_scheduled_amount(self, type_dr):
        if type_dr not in self.__events_state.keys(): return 0

        return self.__events_state[type_dr]

    def set_scheduled_amount(self, type_dr, v):
        self.__events_state[type_dr] = v

    def decode_rawjson(self, type_dr, raw_data):
        notif_time = time.mktime(datetime.strptime(raw_data['notification-date'], "%Y-%m-%dT%H:%M:%S").timetuple())
        data_dr = None

        if type_dr == 'dr_prices':
            data_dr = self.get_timeseries_tariff(raw_data["type"], (raw_data["start-date"], raw_data["end-date"]), raw_data["data"])
        elif type_dr == 'dr_shed':
            pass
        elif type_dr == 'dr_limit':
            pass
        elif type_dr == 'dr_shift':
            pass
        elif type_dr == 'dr_track':
            pass

        return notif_time, data_dr

    def get_timeseries_tariff(self, type_tariff, date_period, raw_json_data):
        start_date, end_date = date_period

        if type_tariff == 'price-tou':

            # Init the CostCalculator with the tariff data
            tariff_data = OpenEI_tariff()
            tariff_data.read_from_json(costcalculator_path+raw_json_data['tariff-json'])
            tariff_struct_from_openei_data(tariff_data, self.__tariff_manager)  # Now __tariff_manager has the blocks that defines the tariff

            # Get the price signal
            timestep = TariffElemPeriod.HOURLY
            start_date_sig = parse(start_date)
            end_date_sig = parse(end_date)
            price_df, map = self.__tariff_manager.get_electricity_price((start_date_sig, end_date_sig), timestep)

            return price_df.to_json()

        elif type_tariff == 'price-rtp':
            return {'timestamp': [], 'energy_price': raw_json_data}
        else:
            return {}
