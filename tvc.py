'''
    Script:  tvc.py
    Author:  Xander Jones (xander@xljones.com)
    Web:     xljones.com
    Date:    7 April 2020
'''
import os
import re
import argparse
import datetime
import time
import curses
import math

'''
    Based on CursesBarGraph (markfickett/fht_curses_graph)
    https://gist.github.com/markfickett/9eb86be659df639b0eee
'''
class CursesBarGraph:
    def __init__(self):
        self._window = None
        self._max = 100

    def __enter__(self):
        self._window = curses.initscr()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        curses.endwin()

    def update(self, values):
        assert self._window
        h, w = self._window.getmaxyx()
        per_bucket = max(1, math.ceil(float(len(values)) / (w - 1)))
        self._window.erase()
        for column_num, v in enumerate(self._averaged_chunks(values, per_bucket)):
            assert column_num < w
            self._draw_bar(column_num, v, h)

        self._draw_axis_labels(h, w, column_num, len(values))
        self._window.refresh()

    def _averaged_chunks(self, iterable, n):
        summed_v = 0
        summed_count = 0
        for v in iterable:
            summed_v += v
            summed_count += 1
            if summed_count >= n:
                yield float(summed_v) / summed_count
                summed_v = 0
                summed_count = 0
        if summed_count > 0:
            yield float(summed_v) / summed_count

    def _draw_bar(self, column_num, value, h):
        bar_len = max(0, min(h - 1, int(h * (value / self._max))))
        # vline draws from the starting coordinate towards positive y (down).
        self._window.vline((h - 1) - bar_len, column_num, ord('|'), bar_len)

    def _draw_axis_labels(self, h, w, max_column, num_values):
        self._window.addstr(0, 0, str(self._max))
        self._window.addstr(h - 1, 0, str(0))
        max_column_str = str(num_values)
        self._window.addstr(
            h - 1,
            min(max_column, w - (len(max_column_str) + 1)),
            max_column_str)


class TemperatureViewController:
    clock_speed = {
        "setpoint": -999,
        "setpoint_last_update": -999,
        "current": -999
    }
    temperature = {
        "current": -999
    }
    _args = []
    _version = 0

    def __init__(self, args, version):
        self._args = args
        self._version = version

    def _print_header(self):
        print("")
        print("     Raspberry Pi Temperature Monitor")
        print("     Xander Jones v{0}".format(self._version))
        print("")

    def _get_temperature(self, fahrenheit):
        system_cmd = os.popen("vcgencmd measure_temp")
        get_str = system_cmd.read()
        regex_pattern = re.compile("temp=([\d\.]+)'[CF]")
        regex_matches = regex_pattern.match(get_str)
        self.temperature["current"] = float(regex_matches.group(1))
        if self._args.fahrenheit:
            self.temperature["current"] = (self.temperature["current"] * (9/5)) + 32
        return(round(self.temperature["current"],1))

    def _get_clock_speed_setpoint(self):
        # Returns clock speed in kHz
        system_cmd = os.popen("vcgencmd get_config arm_freq")
        get_str = system_cmd.read()
        regex_pattern = re.compile("arm_freq=([\d\.]+)")
        regex_matches = regex_pattern.match(get_str)
        self.clock_speed["setpoint"] = float(regex_matches.group(1))/1000 # Command returns in MHz, /1000 convert to GHz
        self.clock_speed["setpoint_last_update"] = datetime.datetime.now()
        return(round(self.clock_speed["setpoint"],1))

    def _get_clock_speed_current(self):
        # Returns clock speed in Hz
        system_cmd = os.popen("vcgencmd measure_clock arm")
        get_str = system_cmd.read()
        regex_pattern = re.compile("frequency\(\d+\)=([\d\.]+)")
        regex_matches = regex_pattern.match(get_str)
        self.clock_speed["current"] = float(regex_matches.group(1))/1000000000 # Command returns in Hz, /1000000 to convert to GHz
        return(round(self.clock_speed["current"],1))

    def _get_timestamp(self):
        now = datetime.datetime.now()
        return (now.strftime("%d/%m//%Y, %H:%M:%S"))

    def graph_temperature(self):
        with CursesBarGraph() as bar_graph:
            while True:
                values = []
                for i in range(200):
                    values.append(100 * (math.sin(0.05 + i/20.0) + 1) / 2.0)
                bar_graph.update(values)

    def text_temperature(self):
        self._print_header()
        output = "     {0} (CPU {1}/{2}GHz): {3}*{4}     "
        if self._args.once:
            print(output.format(self._get_timestamp(), self._get_clock_speed_current(), self._get_clock_speed_setpoint(), self._get_temperature(self._args.fahrenheit), "F" if self._args.fahrenheit else "C"))
            print()
        else:
            while (True):
                print(output.format(self._get_timestamp(), self._get_clock_speed_current(), self._get_clock_speed_setpoint(), self._get_temperature(self._args.fahrenheit), "F" if self._args.fahrenheit else "C"), end="\r")
                time.sleep(1)
