#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 14:39:56 2020

@author: Michael Schneider <mschneid@mbi-berlin.de>, Max Born Institut Berlin
"""


import visa

import tango
from tango import DevState
from tango.server import Device, attribute, command
from tango.server import device_property
from tango import READ, READ_WRITE

import numpy as np


class Keithley2460(Device):
    
    current = attribute(name='current', access=READ_WRITE, unit='A',
                        dtype=tango.DevFloat, format='%.3f')
    
    output = attribute(name='output', access=READ_WRITE,
                       dtype=tango.DevBoolean)
    
    setpoint_reached = attribute(name='setpoint_reached', access=READ,
                                 dtype=tango.DevBoolean)
    
    host = device_property(dtype=str, mandatory=True, update_db=True)
    
    def init_device(self):
        Device.init_device(self)
        self.rm = visa.ResourceManager('@py')
        self.inst = self.rm.open_resource(f'TCPIP::{self.host}::INSTR')
        try:
            ans = self.inst.query('*IDN?')
            print(ans)
            if 'MODEL 2460' in ans:
                self.source_setup()
                self.set_state(DevState.ON)
            else:
                self.set_state(DevState.FAULT)
        except Exception as e:
            print(e, file=self.error_stream)
            self.inst.close()
            self.set_state(DevState.FAULT)
        self._setpoint = self.read_current()
    
    def read_current(self):
        ans = self.inst.query(':READ?')
        print('current read', ans, file=self.log_debug)
        return float(ans)
    
    def read_setpoint_reached(self):
        in_pos = np.allclose(self.read_current(), self._setpoint,
                             rtol=1e-2, atol=1e-2)
        if in_pos:
            self.set_state(DevState.ON)
        return in_pos
    
    def write_current(self, value):
        if float(value) == 0:
            value = 1e-7
        self.inst.write(f'SOUR:CURR {value:.4f}')
        self._setpoint = value
        self.set_state(DevState.MOVING)
    
    def source_setup(self):
        self.inst.write('ROUT:TERM FRON')  # use front terminal out
        self.inst.write('SENS:FUNC "CURR"')
        self.inst.write('SENS:CURR:RANG:AUTO ON')
        self.inst.write('SOUR:FUNC CURR')
        self.inst.write('SOUR:CURR:VLIM 10')
            
    @command
    def reset_device(self):
        self.inst.write('*RST')
        self.source_setup()
        
    # def read_voltage(self):
    #     ans = self.inst.query(':MEAS:VOLT?')
    #     return float(ans)
        
    def read_output(self):
        ans = self.inst.query('OUTP?').strip()
        return True if ans == '1' else False
    
    def write_output(self, value):
        val = {True: 'ON', False: 'OFF'}[value]
        self.inst.write('OUTP ' + val)
           

if __name__ == "__main__":
    Keithley2460.run_server()
