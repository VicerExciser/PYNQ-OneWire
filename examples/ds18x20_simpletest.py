## Simple demo of printing the temperature from the first found DS18x20 sensor every second.
## Author: Austin Condict

## NOTE:  A 4.7Kohm pullup between DATA and POWER is REQUIRED!

import time
from onewire.bus import OneWireBus
from ds18x20 import DS18X20


## Initialize 1-Wire bus
ow_bus = OneWireBus.get_instance()

## Scan for sensors and grab the first one found
# ds18 = DS18X20(ow_bus, ow_bus.search()[0])
sensors = [DS18X20(ow_bus, address) for address in ow_bus.search()]

## Main loop to print the temperature every second
while True:
	try:
		for index, sensor in enumerate(sensors):
			print("Temperature: {0:0.3f}C".format(ds18.temperature))
			print(f"[{index}]  DS18X20_{hex(sensor.rom_id)}:\tTemperature = {sensor.temperature} °C")
			time.sleep(0.1)
		print('\n')
		time.sleep(1.0)
	except KeyboardInterrupt:
		break
