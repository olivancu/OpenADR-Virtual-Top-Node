__author__ = 'Olivier Van Cutsem'

import time
from datetime import datetime
import json
import os, sys
from dateutil.parser import parse
import pandas as pd

DEFAULT_DT = '1H'

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
                print(('Could open {0} but failed to parse the json'.format(filename)))
                return None
    except:
        print(('Cant open file {}'.format(filename)))
        return None

    return data_json


# Load the config and the CostCalculator Module
from electricitycostcalculator.cost_calculator.cost_calculator import CostCalculator
from electricitycostcalculator.cost_calculator.tariff_structure import *
from electricitycostcalculator.openei_tariff.openei_tariff_analyzer import *

import os, electricitycostcalculator
costcalculator_path = os.path.dirname(electricitycostcalculator.__file__) + '/'


class DReventManager():

    def __init__(self):
        self.__events_state = {}  # The amount of scheduled events since the beginning
        self.__scheduled_queue = []  # This is an ordered list

        self.__tariff_manager = CostCalculator()


    def get_scheduled_amount(self, type_dr):
        if type_dr not in list(self.__events_state.keys()): return 0

        return self.__events_state[type_dr]

    def set_scheduled_amount(self, type_dr, v):
        self.__events_state[type_dr] = v

    def add_available_event(self, ev):

        # TODO: insert the ev at the right place in the list
        self.__scheduled_queue.append(ev)

    def get_available_events(self, type_dr=None, timeframe= None):

        ret_sorted = self.__scheduled_queue

        # No specification: all the data
        if type_dr is None and timeframe is None:
            return [{'type': ev['type_dr'], 'data': ev['data_dr'].to_json()} for ev in ret_sorted if ev['data_dr'] is not None]

        # Data type is specified
        if type_dr is not None:
            ret_sorted = [ev for ev in ret_sorted if ev['type_dr'] == type_dr]

        if timeframe is None:
            return [ev['data_dr'].to_json() for ev in ret_sorted]

        # Both timeframe and type of data are speficied
        # (1) get the signals overlapping with this timeframe (2) shorten the signal
        st, et = timeframe
        ret_sorted = [x for x in ret_sorted if (x['startdate'] is not None) and (x['enddate'] is not None)]
        ret_sorted = [x for x in ret_sorted if (st <= x['startdate'] <= et) or (st <= x['enddate'] <= et) or (x['startdate'] <= st and x['enddate'] >= et)]
        ret_sorted = [ev['data_dr'][(ev['data_dr'].index >= st) & (ev['data_dr'].index <= et)].to_json() for ev in ret_sorted]

        return ret_sorted

    def decode_rawjson(self, type_dr, raw_data):
        notif_time = time.mktime(datetime.strptime(raw_data['notification-date'], "%Y-%m-%dT%H:%M:%S").timetuple())
        ret_dict = {'type_dr': type_dr, 'startdate': None, 'enddate': None, 'data_dr': None}

        if type_dr == 'dr_prices':
            ret_dict['startdate'] = raw_data["start-date"]
            ret_dict['enddate'] = raw_data["end-date"]
            ret_dict['data_dr'] = self.get_df_tariff(raw_data["type"], (raw_data["start-date"], raw_data["end-date"]), raw_data["data"])
        elif type_dr == 'dr_shed' or type_dr == 'dr_limit':
            raw_data = raw_data["data"]
            ret_dict['startdate'] = raw_data["start-date"]
            ret_dict['enddate'] = raw_data["end-date"]
            ret_dict['data_dr'] = self.get_df_powerconstraints([(raw_data["start-date"], raw_data["end-date"])], [raw_data["power"]])
        elif type_dr == 'dr_shift':
            raw_data = raw_data["data"]
            ret_dict['startdate'] = raw_data["start-date-take"]
            ret_dict['enddate'] = raw_data["end-date-relax"]
            timeframe_list = [(raw_data["start-date-take"], raw_data["end-date-take"]), (raw_data["start-date-relax"], raw_data["end-date-relax"])]
            power_list = [raw_data["power-take"], raw_data["power-relax"]]
            ret_dict['data_dr'] = self.get_df_powerconstraints(timeframe_list, power_list)
        elif type_dr == 'dr_track':
            raw_data = raw_data["data"]
            ret_dict['startdate'] = raw_data["start-date"]
            ret_dict['enddate'] = raw_data["end-date"]
            ret_dict['data_dr'] = self.get_df_powersignal((raw_data["start-date"], raw_data["end-date"]), raw_data['profile'])

        return notif_time, ret_dict

    def get_df_tariff(self, type_tariff, date_period, raw_json_data):
        """
        Return a Pandas dataframe of elec prices
        :param type_tariff: 'price-rtp' or 'price-tou'
        :param date_period: (start_date, end_date )
        :param raw_json_data: the name of the json file
        :return: a pandas dataframe
        """
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

            return price_df

        elif type_tariff == 'price-rtp':
            st, et = date_period
            index = pd.date_range(st, et, freq=DEFAULT_DT)
            return pd.DataFrame(data=raw_json_data, index=index)
        else:
            return None

    def get_df_powerconstraints(self, l_timeframe, l_power_constraint):
        """
        Create and fill a Pandas dataframe with Power information between multiple timeframe
        :param timeframe: a list of tuple
        :param power_constraint: a list of power data
        :return:
        """

        df = None
        for timeframe, power_constraint in zip(l_timeframe, l_power_constraint):
            st, et = timeframe
            index = pd.date_range(st, et, freq=DEFAULT_DT)

            new_df = pd.DataFrame(data=len(index)* [power_constraint], index=index, columns=['power'])

            if df is None:
                df = new_df
            else:
                df.append(new_df)

        return df

    def get_df_powersignal(self, timeframe, signal):
        """
        Create and fill a Pandas dataframe with Power information between multiple timeframe
        :param timeframe: a list of tuple
        :param power_constraint: a list of power data
        :return:
        """
        st, et = timeframe
        index = pd.date_range(st, et, freq=DEFAULT_DT)
        df = pd.DataFrame(data=signal, index=index, columns=['power'])

        return df
