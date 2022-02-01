#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 14:39:56 2020

Device server to use a Keithley 2460 SourceMeter to drive an electromagnet.
Configures the hardware device to source current and maintains a history of
current setpoints.

@author: Michael Schneider <mschneid@mbi-berlin.de>, Max Born Institut Berlin
"""


import pyvisa as visa
import tango
from tango import DevState
from tango.server import Device, attribute, command
from tango.server import device_property
from tango import READ, READ_WRITE
import sys
import time
import numpy as np


class Keithley2460(Device):

    current = attribute(
        name="current",
        access=READ_WRITE,
        unit="A",
        dtype=tango.DevFloat,
        format="%10.4f",
    )

    voltage = attribute(
        name="voltage",
        access=READ,
        unit="V",
        dtype=tango.DevFloat,
        format="%10.4f",
    )

    curr_hist = attribute(
        name="curr_hist",
        access=READ,
        dtype=(float,),
        max_dim_x=100000,
    )

    output = attribute(
        name="output",
        access=READ_WRITE,
        dtype=tango.DevBoolean,
    )

    host = device_property(
        dtype=str,
        mandatory=True,
        update_db=True,
    )

    def init_device(self):
        Device.init_device(self)
        self.rm = visa.ResourceManager("@py")
        self.inst = self.rm.open_resource(f"TCPIP::{self.host}::INSTR")
        self.inst.clear()
        try:
            # self.inst.write('*RST')  # commented to maintain output state
            self.inst.write("*CLS")
            ans = self.inst.query("*IDN?")
            print(ans)
            if "MODEL 2460" in ans:
                self.source_setup()
                self.set_state(DevState.ON)
                self._current = 0
                self._voltage = 0
                self._output = True
                self._setpoint = self.read_current()
                self._history = [self._setpoint]
                self.write_output(True)
            else:
                print(f"Wrong device at address:\n{ans}", file=self.log_error)
                self.set_state(DevState.FAULT)
                # sys.exit(255)
        except Exception as e:
            print(e, file=self.log_error)
            self.set_state(DevState.FAULT)
            # self.inst.close()
            # sys.exit(255)

    def always_executed_hook(self):
        msg = ':READ? "defbuffer1", READ, SOURCE, SOURSTATUS'
        ans = self.inst.query(msg)
        print(f"always_executed_hook -> {ans}", file=self.log_debug)
        try:
            voltage, current, status = ans.split(",")
            self._voltage = float(voltage)
            self._current = float(current)
            s = int(status)
            self._status = [s >> i & 1 for i in range(8)]
        except Exception as e:
            # likely a timeout occurred - flush buffer
            print(
                f"unexpected {e}: {msg} -> {ans}. Clearing buffer.", file=self.log_warn
            )
            self.inst.clear()
        return

    def read_current(self):
        return self._current

    def read_voltage(self):
        return self._voltage

    def read_output(self):
        return self._status[-1]

    def read_curr_hist(self):
        return self._history

    def write_current(self, value):
        if float(value) == 0:
            value = 1e-7
        self.inst.write(f"SOUR:CURR {value:.8f}")
        self._history.append(value)

    def write_output(self, value):
        val = "ON" if value else "OFF"
        self.inst.write(f"OUTP {val}")

    @command
    def clear_history(self):
        self._history = [
            self._history[-1],
        ]

    def source_setup(self):
        self.inst.write("ROUT:TERM FRON")  # use front terminal out
        self.inst.write('SENS:FUNC "VOLT"')
        self.inst.write("SENS:VOLT:NPLC 1")
        self.inst.write("SENS:VOLT:RANG:AUTO ON")
        self.inst.write("SOUR:FUNC CURR")
        self.inst.write("SOUR:CURR:READ:BACK 1")
        self.inst.write("SOUR:CURR:VLIM 100")

    @command
    def reset_device(self):
        self.inst.write("*RST")
        self.source_setup()
        self.write_output(True)


if __name__ == "__main__":
    Keithley2460.run_server()
