# PYNQ-OneWire
1-Wire controller IP for the PYNQ-Z1 integrated into the base overlay, including Python drivers for the OneWire bus &amp; connected DS18x20 temperature sensors.

The 1-Wire data bus is tied to digital IO0 of the Arduino header.

`ds18x20.py` should work for DS18B20 and DS18S20 1-Wire digital temperature sensors.

Wiring diagram (where GPIOx == pin 0 of the PYNQ):

![](https://user-images.githubusercontent.com/5904370/68093499-5b310700-fe96-11e9-8d50-2be9982a59f2.png)
