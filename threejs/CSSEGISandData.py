#!/usr/bin/env python
"""
Library for parsing the data from CSSEGISandData/COVID-19 github repo
and derive cummulative and daily delta values
"""
import logging
import csv
import json
import requests


class CSSEGISandData:
    """
    Handles the data from https://github.com/CSSEGISandData/COVID-19
    It's used to transform it into arrays/objects in javascript for the ThreeJS javascript code
    """

    def __init__(self, logging):
        """
        Sets up initial variables on the source of the data
        """
        self.logger = logging
        raw_https_repo = "raw.githubusercontent.com/CSSEGISandData/COVID-19"
        base_url = "https://{}/{}".format(
            raw_https_repo,
            "master/csse_covid_19_data/csse_covid_19_time_series/")
        self.confirmed_url = "{}/{}".format(
            base_url, "time_series_covid19_confirmed_global.csv")
        self.deaths_url = "{}/{}".format(
            base_url, "time_series_covid19_deaths_global.csv")
        self.recovered_url = "{}/{}".format(
            base_url, "time_series_covid19_recovered_global.csv")

    def load_default_datasources(self):
        """
        Performs http requests to load the data from the configured URLs.
        The data is loaded into strings which can later be parsed
        """
        confirmed_req = requests.get(self.confirmed_url)
        deaths_req = requests.get(self.deaths_url)
        recovered_req = requests.get(self.recovered_url)

    def parse_header(self, header_array, USFileType=False, offset_dates=None):
        """
        The header line is composed of:
        Province/State,Country/Region,Lat,Lng,Day1,Day2,Day3
        :param header_array list: The header line split already by commas
        :param USFileType bool: Wether we should include only US or exclude US
        :param offset_dates int: override the default calculation of offset_dates
        """
        # Province/State, Country/Region, Lat, Lng
        logger = logging.getLogger("parse_header")
        date_keys = []
        if offset_dates is None:
            if USFileType:
                offset_dates = 11
            else:
                offset_dates = 4
        for date_item in header_array[offset_dates:]:
            # date_items look like 2/11/02
            (month, day, year) = date_item.split("/")
            # Zero-pad to 2 "digits" month and day
            day = day.rjust(2, '0')
            month = month.rjust(2, '0')
            new_date_key = "{}-{}-{}".format(year, month, day)
            logger.debug("New date %s makes key: %s", date_item, new_date_key)
            date_keys.append(new_date_key)
        logger.info("Found date_keys: %s", date_keys)
        return date_keys

    def parse_data_line(self, data_array, date_keys, USFileType=False, offset_dates=None, forceProcessUS=False):
        """
        The data line is composed of: SomeProvince/SomeState,SomeCountry/SomeRegion,Lat0,Lng0,Day1Value,Day2Value,Day3Value
        :param data_array list: A line split already by commas
        :param date_keys list: A list of dates to fill from the data array
        :param USFileType bool: Mark the records as being from either US filetype or not
        :param offset_dates int: override the default calculation of offset_dates
        :param forceProcessUS bool: Mark the records as needing to be forcefully processed or not
        :returns tuple: ("Lat,Lng,Country - Region,True,True", [{"Year-Mothh-Day":{"cumulative": CumulativeValue, "day": DayTotal, "delta": Delta}},{}])
        """
        res = dict()
        logger = logging.getLogger("parse_data_line")
        if USFileType:
            country_region = "{} - {}".format(data_array[7].replace(
                ",", ""), data_array[6].replace(",", ""))
            if data_array[5]:
                country_region = "{} - {}".format(
                    country_region, data_array[5])
            lat = data_array[8]
            lng = data_array[9]
            if offset_dates is None:
                offset_dates = 11
        else:
            country_region = data_array[1].replace(",", "")
            if data_array[0]:
                country_region = "{} - {}".format(country_region,
                                                  data_array[0].replace(",", ""))
            lat = data_array[2]
            lng = data_array[3]
            if offset_dates is None:
                offset_dates = 4
        gps_key = "{},{},{},{},{}".format(
            lat, lng, country_region, USFileType, forceProcessUS)
        prev_cumulative = None
        prev_day_value = None
        for date_idx, date_item in enumerate(data_array[offset_dates:]):
            current_column_date = date_keys[date_idx]
            logger.debug("Found data %s for day: %s",
                         date_item, current_column_date)
            # The data may be a 0.0 in some columns, but ases shouldn't be floating points?
            curr_date_value = int(float(date_item))
            if prev_cumulative is None:
                # This is the first date recorded, the daily value will be set to cumulative.
                # There is no delta yet.
                day_value = curr_date_value
                day_delta = 0
            else:
                day_value = curr_date_value - prev_cumulative
                day_delta = day_value - prev_day_value
            res[current_column_date] = {
                "cumulative": curr_date_value,
                "day": day_value,
                "delta": day_delta
            }
            prev_day_value = day_value
            prev_cumulative = curr_date_value
        return (gps_key, res)

    def parse_csv_file(self, fname, USFileType=False, offset_dates=None, forceProcessUS=False):
        """
        :param fname str: The filename to parse
        :param USFileType bool: Mark the records as being from either US filetype or not
        :param offset_dates int: override the default calculation of offset_dates
        :param forceProcessUS bool: Mark the records as needing to be forcefully processed or not
        :returns tuple like (["date1","date2"]{"lat,lng,Country - Province,False,False":[{"2020-02-01":{"cumulative": 100, "day": 2, "delta": -5}}])
        """
        logger = logging.getLogger("parse_csv_file")
        logger.info("Starting to parse file %s", fname)
        res = dict()
        date_keys = []
        with open(fname) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',', quotechar='"')
            for lineno, csv_line in enumerate(csv_reader):
                # Remove the new line:
                # The first items in the CSV are:
                if lineno == 0:
                    date_keys = self.parse_header(
                        csv_line, USFileType, offset_dates)
                else:  # This is not the header
                    gps_key, gps_daily_data = self.parse_data_line(
                        csv_line,
                        date_keys,
                        USFileType=USFileType,
                        offset_dates=offset_dates,
                        forceProcessUS=forceProcessUS)
                    res[gps_key] = gps_daily_data
        logger.info("Finished parsing file")
        return (date_keys, res)

    def get_stats_for_day(self, gps_records, series_key):
        """
        Returns a dict with collected stats for a given day.
        :param gps_records dict: The per-day gps records with their cumulative/day/delta values
        :param series_key: The 0 indexed day from the start of our dataset
        :returns: dict with {"top_cumulative": {"value": X, "location_idx": Y}, "total": Z}
        """
        res = dict()
        res["name"] = series_key
        res["top_cumulative"] = dict()
        res["top_cumulative"]["value"] = 0
        res["top_cumulative"]["location_idx"] = 0
        res["top_day"] = dict()
        res["top_day"]["value"] = 0
        res["top_day"]["location_idx"] = 0
        res["top_delta"] = dict()
        res["top_delta"]["value"] = 0
        res["top_delta"]["location_idx"] = 0
        # For the most part, the stats have minimum value of 0, except for delta, which can be negative
        # So let's find the minimum value
        cumulative_global = 0
        day_global = 0
        delta_global = 0
        location_number = 0
        for lat_lng_key, lat_lng_data in gps_records.items():
            _lat, _lng, location, USFileType, forceProcessUS = lat_lng_key.split(
                ",")
            for day_key, day_data in lat_lng_data.items():
                if day_key == series_key:
                    if USFileType == "False" and location == "US" and forceProcessUS == "False":
                        logging.debug("Ignoring stat for day: %s location: %s, USFileType: %s, forceProcessUS: %s",
                                      day_key, location, USFileType, forceProcessUS)
                    else:
                        cumulative_global += day_data["cumulative"]
                        day_global += day_data["day"]
                        delta_global += day_data["delta"]
                    if day_data["cumulative"] > res["top_cumulative"]["value"]:
                        res["top_cumulative"]["value"] = day_data["cumulative"]
                        res["top_cumulative"]["location_idx"] = location_number
                    if abs(day_data["day"]) > res["top_day"]["value"]:
                        res["top_day"]["value"] = abs(day_data["day"])
                        res["top_day"]["location_idx"] = location_number
                    if abs(day_data["delta"]) > res["top_delta"]["value"]:
                        res["top_delta"]["value"] = abs(day_data["delta"])
                        res["top_delta"]["location_idx"] = location_number
            location_number += 1
        res["cumulative_global"] = cumulative_global
        res["day_global"] = day_global
        res["delta_global"] = delta_global
        return res

    def generate_globe_json_string(self, gps_records, daily_series, pretty_print=False):
        """
        Returns a JSON object that can be loaded into the our globe drawing functions
        :param gps_records dict: The per-day gps records with their cumulative/day/delta values
        :param daily_series list: The list of days that we are filling
        :param pretty_print bool: human readable json structures
        Data format: see data/-data-schema.json
        """
        logger = logging.getLogger("generate_globe_json_string")
        logger.info("Starting creating array structs for the JSON")
        # First, let's scan day indexes, they will become series and be in the dropdown:
        locations = []
        series_stats = []
        # Let's push the locations and their daily values
        for lat_lng_key, lat_lng_data in gps_records.items():
            lat, lng, location, USFileType, forceProcessUS = lat_lng_key.split(
                ",")
            try:
                lat = float(lat)
                lng = float(lng)
            except:
                logger.error("Unable to parse lat/lng on key %s", lat_lng_key)
                continue
            day_array = []
            for day_key in sorted(lat_lng_data.keys()):
                day_data = lat_lng_data[day_key]
                if USFileType == "False" and location == "US" and forceProcessUS == "False":
                    # The data for US in this filetype is aggregated, let's not draw it twice
                    # we will send a "hide" flag
                    day_array.append([
                        day_data["cumulative"],
                        day_data["day"],
                        day_data["delta"],
                        1,
                    ])
                else:
                    # Let's rounde the day value by 3 floats to reduce json file size
                    day_array.append([
                        day_data["cumulative"],
                        day_data["day"],
                        day_data["delta"],
                    ])
            location_struct = dict()
            location_struct["lat"] = lat
            location_struct["lng"] = lng
            location_struct["location"] = location
            location_struct["values"] = day_array
            locations.append(location_struct)
        # Now let's push stats for the day
        logger.debug("Daily series identified: %s", daily_series)
        for series in sorted(daily_series):
            day_stats = self.get_stats_for_day(gps_records, series)
            series_stats.append(day_stats)
        logger.info("Finished calculations for JSON structure")
        res = dict()
        res["locations"] = locations
        res["series_stats"] = series_stats
        if pretty_print:
            return json.dumps(res, sort_keys=True, indent=2)
        else:
            return json.dumps(res)

    def merge_gps_records(self, lhs, rhs):
        """
        Merges two dictionaries
        :returns a new dict with the merged keys
        """
        return {**lhs, **rhs}

    def process_confirmed(self):
        """
        Processes the global confirmed file
        """
        date_keys, global_confirmed_gps_data = self.parse_csv_file(
            "../../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv", USFileType=False)
        _date_keys, us_confirmed_gps_data = self.parse_csv_file(
            "../../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv", USFileType=True)
        confirmed_gps_data = self.merge_gps_records(
            global_confirmed_gps_data, us_confirmed_gps_data)
        logging.info("Writing data/confirmed.json")
        with open("data/confirmed.json", "w") as file_handle:
            file_handle.write(self.generate_globe_json_string(
                confirmed_gps_data, date_keys))
        logging.info("Finished writing data/confirmed.json")

    def process_deaths(self):
        """
        Processes the global confirmed file
        """
        date_keys, global_deaths_gps_data = self.parse_csv_file(
            "../../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv", USFileType=False)
        _date_keys, us_deaths_gps_data = self.parse_csv_file(
            "../../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv", USFileType=True, offset_dates=12)
        deaths_gps_data = self.merge_gps_records(
            global_deaths_gps_data, us_deaths_gps_data)
        logging.info("Writing data/deaths.json")
        with open("data/deaths.json", "w") as file_handle:
            file_handle.write(self.generate_globe_json_string(
                deaths_gps_data, date_keys))
        logging.info("Finished writing data/deaths.json")

    def process_recovered(self):
        date_keys, global_recovered_gps_data = self.parse_csv_file(
            "../../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv", USFileType=False, forceProcessUS=True)
        #_date_keys, us_recovered_gps_data = parse_csv_file("../../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_US.csv", USFileType=True)
        # There's no recovered dataset for US
        us_recovered_gps_data = dict()
        recovered_gps_data = self.merge_gps_records(
            global_recovered_gps_data, us_recovered_gps_data)
        logging.info("Writing data/recovered.json")
        with open("data/recovered.json", "w") as file_handle:
            file_handle.write(self.generate_globe_json_string(
                recovered_gps_data, date_keys))
        logging.info("Finished writing data/recovered.json")
