# pytango_Keithley2460
pytango device to use the Keithley 2460 Sourcemeter as a current source.
Allows setting a current value and provides readback on actual current and voltage.


## Sardana
Works well enough with tangoattributemotorctrl.
In spock, assuming an existing tango attribute motor controller (`tangomotorctrl`):

```
defelem current tangomotorctrl
current.tangoattribute = "<tango fqdn>/current"
current.tangoattributeencoderthreshold = 1e-3  # threshold value to decide when motor is "in position"
```

Similarly for voltage radback as ZeroD element:

```
defelem voltage tangoattrzerodctrl
voltage.tangoattribute = "<tango fqdn>/voltage"
```
