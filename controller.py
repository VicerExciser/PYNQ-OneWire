
import sys
import time
import ds18b20
from onewire import OneWire, addr_map, bus_cmds, masks, timeout



class TemperatureController():
	
	def __init__(self, sensor_type=ds18b20.DS18B20):
		self.ow_bus = OneWire.get_instance()
		self.sensor_class = sensor_type
		self.sensors = []

		self.rom_cmds = sys.modules[self.sensor_class.__module__].rom_cmds 
		self.func_cmds = sys.modules[self.sensor_class.__module__].func_cmds 

		self.family_code = sys.modules[self.sensor_class.__module__].FAMILY_CODE
		self.temp_convert_time = sys.modules[self.sensor_class.__module__].T_CONV_TIME 
		self.rw_time = sys.modules[self.sensor_class.__module__].RW_TIME 
		self.transmit_bits = sys.modules[self.sensor_class.__module__].TRANSMIT_BITS
		self.scratch_rd_size = sys.modules[self.sensor_class.__module__].SCRATCH_RD_SIZE

		for sensor in self.ow_bus.search(self.sensor_class, self.rom_cmds['SRCH_ROM']):
			self.sensors.append(sensor)
			print(f"\n[{self.__class__.__name__}]\tFound {self.sensor_class.__name__}:  {repr(sensor)}")


		if self.ow_bus.num_roms == 0:
		#if OneWire.num_roms == 0:
			print(f"\n[{self.__class__.__name__}]\tERROR: No sensors found on the OneWire bus!\n ~ A B O R T I N G ~ \n")
			sys.exit(0)

	def poll_temperatures(self, delay=1):
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
		if hasattr(sensor, 'rom_index'):
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
		print(f'\nDEVICE {ichoice} TEMPERATURE = [{cels}°C | {fahr}°F] \n')
		# target_id = OneWire.get_id(ichoice)

		#sensor.last_read_temp = fahr
		sensor.last_read_temp = cels

		return cels, fahr


## ---------------------------------------------------------------------------------------------

	# def match_rom(ichoice):
	def match_rom(self, rom_lo, rom_hi):
		"""
		MATCH ROM [55h]
		The match ROM command allows to address a specific slave device on a multidrop or single-drop bus.
		Only the slave that exactly matches the 64-bit ROM code sequence will respond to the function command
		issued by the master; all other slaves on the bus will wait for a reset pulse.
		"""
		OneWire.bram_write(addr_map['CMD_ADDR'], self.rom_cmds['MTCH_ROM'])
		OneWire.bram_write(addr_map['WRS_ADDR'], self.transmit_bits)
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

	def convert_temp(self):
		"""
		CONVERT T [44h]
		This command initiates a single temperature conversion.
		"""
		OneWire.bram_write(addr_map['CMD_ADDR'], self.func_cmds['CONVT_TEMP'])
		OneWire.bram_write(addr_map['CON_ADDR'], bus_cmds['EXEC_W_PULLUP'])
		time.sleep(self.temp_convert_time)
		r_status = OneWire.bram_read(addr_map['STA_ADDR'])
		return r_status == 0x8

	
## ---------------------------------------------------------------------------------------------

	def read_scratch(self):
		"""
		READ SCRATCHPAD [BEh]
		This command allows the master to read the contents of the scratchpad register.
		Note: master must generate read time slots immediately after issuing the command.
		"""
		OneWire.bram_write(addr_map['CMD_ADDR'], self.func_cmds['SCRATCH_RD'])
		OneWire.bram_write(addr_map['RDS_ADDR'], self.scratch_rd_size)
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
