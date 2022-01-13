# pytango_Keithley2460
a quick-and-dirty tango device for the Keithley 2460


## Sardana
Works well enough with tangoattributemotorctrl
- set `tangoattribute` to `<host>:<port>/<domain>/<family>/<member>/current`
- set `tangoattributeencoderthreshold` to 0.001 (i.e., wait for current to be within 1 mA of setpoint value)
