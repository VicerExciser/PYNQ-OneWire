
import time
import ds18b20
from onewire import OneWire, addr_map, bus_cmds, masks, timeout



class TemperatureController():
	
	def __init__(self, sensor_type=ds18b20.DS18B20):
		self.ow_bus = OneWire.get_instance()
		self.sensor_class = sensor_type
		self.sensors = []
		for sensor in self.ow_bus.search(self.sensor_class, ds18b20.rom_cmds['SRCH_ROM']):
			self.sensors.append(sensor)
			print(f"[{self.__class__.__name__}]\tFound {self.sensor_class.__name__}:  {repr(sensor)}")


	def poll_temperatures(delay=1):
		for sensor in self.sensors:
			temp_c, temp_f = self.get_temperature(sensor)
			print(str(sensor))
			# print()
			time.sleep(delay)



## ---------------------------------------------------------------------------------------------

	def get_temperature(self, sensor):  #=None):
		"""
		Calculate temperature from the scratchpad
		"""

		if OneWire.num_roms < 1:
			print('\tNo OW devices found on the bus!')
			return False

		"""
		ichoice = -1
		if sensor is None:
			print('Get temperature of which OW device (enter number):\n')   # GUI
			for i in range(OneWire.num_roms):
				addr_long = OneWire.get_id(i)
				print(f" {i}: {addr_long}")
			print('')
			ichoice = util.getch()
			while ichoice >= OneWire.num_roms:
				print('\nInvalid device number, try again:')
				ichoice = util.getch()
		elif isinstance(sensor, ds18b20.DS18B20):
			ichoice = OneWire.get_device_index(sensor)
		elif isinstance(sensor, str) and len(sensor)==16:
			ichoice = OneWire.get_rom_id_index(sensor)
		if ichoice < 0:
			print('AN ERROR OCCURRED DURING get_temperature CALL')
			return 0
		"""
		if hasattr(sensor, rom_index):
			ichoice = sensor.rom_index  ## Index of the device on the OneWire bus
		else:
			ichoice = sensor.serial_string

		''' reset pulse (all devices respond w/ a presence pulse) '''
		success = OneWire.reset_pulse()
		if not success:
			print('\n\tAN ERROR OCCURRED DURING RESET\n')
			return 0

		''' match rom '''
		# success = OneWire.match_rom(ichoice)
		success = self.match_rom(sensor.rom_lo, sensor.rom_hi)
		if not success:
			print('\n\tAN ERROR OCCURRED DURING ROM MATCH\n')
			return 0

		''' convert Temp '''
		success = self.convert_temp()
		if not success:
			print('\n\tAN ERROR OCCURRED DURING TEMPERATURE CONVERSION\n')
			return 0

		''' reset again '''
		success = OneWire.reset_pulse()
		if not success:
			print('\n\tAN ERROR OCCURRED DURING RESET\n')
			return 0

		''' match rom again '''
		# success = OneWire.match_rom(ichoice)
		success = self.match_rom(sensor.rom_lo, sensor.rom_hi)
		if not success:
			print('\n\tAN ERROR OCCURRED DURING ROM MATCH\n')
			return 0

		''' read scratch reg '''
		success = self.read_scratch()
		if not success:
			print('\n\tAN ERROR OCCURRED WHILE READING SCRATCHPAD\n')
			return 0

		tempo = OneWire.bram_read(addr_map['RD0_ADDR'])
		cels = ds18b20.celsius_from_raw(tempo)
		fahr = ds18b20.fahr_from_celsius(cels)

		''' Display Read registers '''
		print(f'\nDEVICE {ichoice} TEMPERATURE = [{cels}{ds18b20.DEG_C} | {fahr}{ds18b20.DEG_F}] \n')
		# target_id = OneWire.get_id(ichoice)

		#sensor.last_read_temp = fahr
		sensor.last_read_temp = cels

		return cels, fahr


## ---------------------------------------------------------------------------------------------

	# def match_rom(ichoice):
	def match_rom(rom_lo, rom_hi):
		"""
		MATCH ROM [55h]
		The match ROM command allows to address a specific slave device on a multidrop or single-drop bus.
		Only the slave that exactly matches the 64-bit ROM code sequence will respond to the function command
		issued by the master; all other slaves on the bus will wait for a reset pulse.
		"""
		OneWire.bram_write(addr_map['CMD_ADDR'], ds18b20.rom_cmds['MTCH_ROM'])
		OneWire.bram_write(addr_map['WRS_ADDR'], ds18b20.TRANSMIT_BITS)
		# OneWire.bram_write(addr_map['WR0_ADDR'], OneWire.rom_addrs[ichoice * 2])
		# OneWire.bram_write(addr_map['WR1_ADDR'], OneWire.rom_addrs[(ichoice * 2) + 1])
		OneWire.bram_write(addr_map['WR0_ADDR'], rom_lo)
		OneWire.bram_write(addr_map['WR1_ADDR'], rom_hi)
		OneWire.bram_write(addr_map['CON_ADDR'], bus_cmds['EXEC_WO_PULLUP'])
		r_status = OneWire.bram_read(addr_map['STA_ADDR'])
		x = r_status & masks['STA_WRD']
		count = 0
		while x == 0:
			r_status = OneWire.bram_read(addr_map['STA_ADDR'])
			x = r_status & masks['STA_WRD']
			count += 1
			if (count > 20):
				print('Desired ROM address not matched')
				return False
			timeout()
		return True

## ---------------------------------------------------------------------------------------------

	def convert_temp():
		"""
		CONVERT T [44h]
		This command initiates a single temperature conversion.
		"""
		OneWire.bram_write(addr_map['CMD_ADDR'], ds18b20.func_cmds['CONVT_TEMP'])
		OneWire.bram_write(addr_map['CON_ADDR'], bus_cmds['EXEC_W_PULLUP'])
		time.sleep(ds18b20.T_CONV)
		r_status = OneWire.bram_read(addr_map['STA_ADDR'])
		return r_status == 0x8

	
## ---------------------------------------------------------------------------------------------

	def read_scratch():
		"""
		READ SCRATCHPAD [BEh]
		This command allows the master to read the contents of the scratchpad register.
		Note: master must generate read time slots immediately after issuing the command.
		"""
		OneWire.bram_write(addr_map['CMD_ADDR'], ds18b20.func_cmds['SCRATCH_RD'])
		OneWire.bram_write(addr_map['RDS_ADDR'], ds18b20.SCRATCH_RD_SIZE)
		OneWire.bram_write(addr_map['CON_ADDR'], bus_cmds['RD_TIME_SLOTS'])
		r_status = OneWire.bram_read(addr_map['STA_ADDR'])
		x = r_status & masks['STA_RDD']
		count = 0
		while x == 0:
			r_status = OneWire.bram_read(addr_map['STA_ADDR'])
			x = r_status & masks['STA_RDD']
			count += 1
			if count > 20:
				print('Scratchpad Read Error')
				return False
			timeout()
		return True

## ---------------------------------------------------------------------------------------------

if __name__ == "__main__":
	control = TemperatureController(sensor_type=ds18b20.DS18B20)

	while True:
		try:
			control.poll_temperatures()
			time.sleep(4)
			print('\n============\n')
		except KeyboardInterrupt:
			print(f'\n{__file__} terminating.')
			break
