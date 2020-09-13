#!/usr/bin/env python3

# * -- Filename   : onewire.py
# * -- Author     : Austin Condict
# * -- Description: 1-Wire Master Controller Class
import os
import asyncio
import functools
from time import sleep
from pynq import MMIO #, Overlay
from pynq import Clocks
from core.ds18b20 import DS18B20
#import devicemanager
from core.devicemanager import DeviceManager as manager
import core.const as const
import core.temputil as util
import core.userinterface as ui

from pynq.base.overlays import BaseOverlay

OVERLAY_NAME = 'vip.bit' 	## Put this bitstream file in the directory:  /home/xilinx/pynq/overlays/vip/
OVERLAY_PATH = os.path.join(os.environ['HOME'], 'pynq', 'overlays', 'vip', OVERLAY_NAME)
OL = BaseOverlay(OVERLAY_PATH)

	


class OneWire(object):
	'''
	Class representing a programmatic device driver for issuing ROM commands to
	multiple DS18B20 temperature sensors on a 1-Wire protocol bus.
	'''
	AXI_OW_IP_NAME = 'ow_master_top_0'

	# AXI_OW_ADDR = 0x83C20000	# vip.bit OneWire module offset (memory mapped address in the fabric)
	AXI_OW_ADDR = OL.ip_dict[AXI_OW_IP_NAME]['phys_addr']  	   ## 0x83c20000
	# AXI_OW_RANGE = 0xFFFF
	AXI_OW_RANGE = OL.ip_dict[AXI_OW_IP_NAME]['addr_range']    ## 0x10000

	TRANSMIT_BITS = 0x40  # 64-bits to transmit over the bus
	SCRATCH_RD_SIZE = 0x48  # read in 72 bits from scratch reg
	TIMESLOT = 0.00006  # 1 timeslot == 60 micro seconds
	# ^ 1 bit of data is transmitted over the bus per each timeslot
	FAMILY_CODE = 0x28
	T_CONV = 0.750  # Temp conversion time, default value
	T_RW = 0.010  # EEPROM write time, default value


	PERIOD = 1000 	# for HeatingElement PWM period
	CLK_MHZ = 33.33333	# required CPU clock scaling for 1-Wire master
	OW_FCLK_IDX = 3 	# ow_master module is tied to fclk3



	addrs = { 	'CON_ADDR': 0x000,  # Control Reg Offset
				'RDS_ADDR': 0x004,  # Read Size Reg Offset
				'WRS_ADDR': 0x008,  # Write Size Reg Offset
				'CMD_ADDR': 0x00C,  # OW Command Reg Offset
				'CRR_ADDR': 0x010,  # CRC Read Reg Offset
				'CRC_ADDR': 0x014,  # CRC Count Reg Offset
				'CRW_ADDR': 0x018,  # CRC Write Reg Offset
				'WR0_ADDR': 0x01C,  # Write Data Low 32 Reg Offset
				'WR1_ADDR': 0x020,  # Write Data Hi 32 Reg Offset

				'STA_ADDR': 0x040,  # Status Reg Offset
				'RD0_ADDR': 0x044,  # Read Data Lower Offset
				'RD1_ADDR': 0x048,  # Read Data Low Offset
				'RD2_ADDR': 0x04C,  # Read Data High Offset
				'RD3_ADDR': 0x050,  # Read Data Highest Offset
				'FND_ADDR': 0x054,  # Num ROMs Found Reg Offset

				'RM0_ADDR': 0x400,  # Lo 32 of Serial Number of Device Reg Offset
				'RM1_ADDR': 0x404,  # Hi 32 of Device ID Reg Offset
				'RM2_ADDR': 0x408,
				'RM3_ADDR': 0x40C,
				'RM4_ADDR': 0x410,
				'RM5_ADDR': 0x414,
			}

	# Bit masks for the status register
	masks = { 	'STA_SRD': 0x00000001, # status reg search done bit (c_uir_srd)
				'STA_UN1': 0x00000002, # status reg unused (c_uir_nc1)
				'STA_INT': 0x00000004, # status reg 1-Wire interrupt bit (c_uir_int)
				'STA_CMD': 0x00000008, # status reg cmd done bit (c_uir_cmdd)
				'STA_WRD': 0x00000010, # status reg block write done bit (c_uir_wrd)
				'STA_RDD': 0x00000020, # status reg block read done bit (c_uir_rdd)
				'STA_RSD': 0x00000040, # status reg reset done bit (c_uir_rsd)
				'STA_PRE': 0x00000080, # status reg presence pulse after last reset (c_uir_pre)
				'STA_CRC': 0x00000100, # status reg crc error bit (c_uir_crce)
				'STA_SER': 0x00000200, # status reg search error / no response  (c_uir_srche)
				# ^ this bit gets set if no OW devices respond to the search
				'STA_SME': 0x00000400, # status reg search memory error (c_uir_srme)
				'STA_BB' : 0x80000000, # READ ONLY: status register's busy bit (c_uir_busy)
	# Bit masks for the control register
				'CON_SRE': 0x00000001, # control reg search rom/alarm bit (c_uir_srb)
				'CON_SAE': 0x00000002, # control reg unused (c_uir_uu1)
				'CON_CRC': 0x00000004, # control reg append crc bit (c_uir_acrc)
				'CON_CEN': 0x00000008, # control reg command enable bit (c_uir_cmden)
				'CON_WRE': 0x00000010, # control reg write block enable bit (c_uir_wren)
				'CON_RDE': 0x00000020, # control reg read block enable bit (c_uir_rden)
			}
	# ^ these register bits originate from zpack.vhd

	rom_cmds = { 'SRCH_ROM' : 0x000000F0,  # Search Rom
				 'READ_ROM' : 0x00000033,  # Read Rom // can be used in place of search_rom if only 1 slave
				 'MTCH_ROM' : 0x00000055,  # Match Rom
				 'SKIP_ROM' : 0x000000CC,  # Skip Rom
				 'ALRM_SRCH': 0x000000EC,  # Alarm Search
				}

	func_cmds = { 	'CONVT_TEMP' : 0x44,  # Convert Temp
					'SCRATCH_WR' : 0x4E,  # Write Scratchpad: write 3 bytes of data to device scratchpad
					'SCRATCH_RD' : 0xBE,  # Read Scratchpad
					'SCRATCH_CPY': 0x48,  # Copy Scratchpad
					'RECALL_ATV' : 0xB8,  # Recall Alarm Trigger Values
					'POWER_RD'   : 0xB4,  # Read Power Supply
				}

	con_reg_cmds = { 'SERIALIZE'     : 0x00000001,  # send command onto the bus
					 'RESET_PULSE'   : 0x00010000,  # pulls bus low
					 'EXEC_W_PULLUP' : 0x08,
					 'EXEC_WO_PULLUP': 0x18,
					 'RD_TIME_SLOTS' : 0x28,
					}

	bram = MMIO(AXI_OW_ADDR, AXI_OW_RANGE)
	ROMAD_SIZE = 20   # Large enough to hold 10 temp sensor ROM IDs
	num_roms = 0
	romad = [0] * ROMAD_SIZE
	# romad = list()
	# romad = None
	bus_initialized = 0
	search_complete = 0
	__instance = None
	# fm = None

#------------------------------------------------------------------------------------------------------------

	def __init__(self, base_addr=0x0000, ad_range=0xFFFF):
		if not OneWire.__instance:
			self._initialized = 0
			# OneWire.romad = list()
			if base_addr != OneWire.AXI_OW_ADDR or ad_range != OneWire.AXI_OW_RANGE:
				OneWire.AXI_OW_ADDR = base_addr
				OneWire.AXI_OW_RANGE = ad_range
				OneWire.bram = MMIO(base_addr, ad_range)

			dm = manager.get_instance()
			mgr_ready = dm.initialized
			# Wait for DeviceManager to read in .csv file
			while not mgr_ready:
				mgr_ready = dm.initialized
			self._initialized = 1
			OneWire.bus_initialized = 1
			print('OneWire initialized')
			OneWire.__instance = self 

	@property
	def initialized(self):
		return self._initialized

	@staticmethod
	def get_instance(base_addr=None, ad_range=0xFFFF):
		if not OneWire.__instance:
			if base_addr is None:
				base_addr = const.AXI_OW_ADDR
			OneWire(base_addr, ad_range)
		return OneWire.__instance

# ------------------------------------------------------------------------------------------------------------
	def set_clk(mhz=33.33333):
		cur_freq = Clocks.fclk3_mhz if const.OW_FCLK_IDX is 3 else Clocks.fclk0_mhz
		print(f'Clocks.fclk{const.OW_FCLK_IDX}_mhz = {cur_freq}MHz')
		if abs(cur_freq - mhz) > 1: #1e-6: 		# tests approximate equality for call redundancy 
			print(f"Setting fclk{const.OW_FCLK_IDX} to {mhz}MHz")
			Clocks.set_fclk(clk_idx=const.OW_FCLK_IDX, clk_mhz=mhz)

	def get_id(index):
		rom_hi = OneWire.romad[(index * 2) + 1]
		rom_lo = OneWire.romad[index * 2]
		#rom_long = (rom_hi << 32) + rom_lo
		#rom_tuple = hex(rom_long).partition('x')
		#return rom_tuple[2].upper()
		return util.split_rid_to_string(rom_hi, rom_lo)
	 
	def get_rom_id_index(rid):
		index = OneWire.get_device_index(manager.get_device(rid)) 
		return index if index is not None else -1

	def get_device_index(dev):
		if isinstance(dev, DS18B20):
			rid = dev.serial_string
			index = 0
			while index < OneWire.num_roms:
				rom_i = OneWire.get_id(index)
				if rid == rom_i:
					return index
				index = index + 1
		print("ROMAD INDEX OF DEVICE NOT FOUND")
		return -1
 
	#@asyncio.coroutine
	async def poll_temps(loop=None, use_alarms=True):	
		# from core.components import BrewSystem as bs
		# from routines.controller import Control as ctrl
		# print(f'\nPOLLER:: ctrl.sys_components = {id(ctrl.sys_components)} | bs.sys_components = {id(bs.sys_components)}\n')

		# Remove 'loop' arg ^ and refactor if blocking handler run_in_executor is not needed
		for i in range(OneWire.num_roms):
			rid = OneWire.get_id(i)
			print(f' -- Polling Sensor #[{rid}] -- ')
			dev = manager.get_device(rid)
			#if dev:
			#	old_temp = dev.last_read_temp

			# NOTE: run_in_executor may be unnecessary!

			## new_temp = OneWire.get_temperature(dev)
			#await loop.call_soon(OneWire.get_temperature, dev)
			#await loop.call_soon_threadsafe(OneWire.get_temperature, dev)
			#executor = None
			#get_temperature = OneWire.get_temperature
			#func1 = functools.partial(get_temperature, dev=dev)	# similar to lambda
			#await loop.run_in_executor(executor, func1)
			if loop:
				await loop.run_in_executor(None, functools.partial(OneWire.get_temperature, dev))
			else:
				OneWire.get_temperature(dev)
			#await loop.run_in_executor(None, OneWire.get_temperature, dev)

			# NOTE: Updating sensor data files here is redundant as it is done in get_temperature
			###if new_temp != old_temp:
			## manager.update_device_in_file(dev)
			##await loop.call_soon(manager.update_device_in_file, dev)
			##update_dev = manager.update_device_in_file
			##func2 = functools.partial(update_dev, dev=dev)
			# if loop:
			# 	await loop.run_in_executor(None, functools.partial(manager.append_log, dev))
			# else:	# NOTE: append_log subsequently calls update_device_in_file
			# 	manager.append_log(dev)
			##await loop.run_in_executor(None, manager.update_device_in_file, dev)

			if use_alarms:
				flag = OneWire.check_alarms(dev)
				if flag:
					#from routines.controller import alarm_handler
					from routines.controller import Control
					#alarm_handler(dev, flag)
					await Control.alarm_handler(loop, dev, flag) #, loop)
	
	def check_alarms(dev):
		'''
		Returns:
			-1 if temp < alarm_lo -- should signal heating element to activate
			 0 if no alarms triggered / within threshold limits
			 1 if temp > alarm_hi -- should signal heating element to deactivate
		'''
		sensor = dev
		if isinstance(dev, str):
			sensor = manager.get_device(dev)
		if sensor is None or not isinstance(sensor, DS18B20):
			print('FUBAR')
			return 0
		if sensor.target_temp <= 1:
			return 0
		t = float(sensor.last_read_temp)
		t_min = float(sensor.alarm_lo)
		t_max = float(sensor.alarm_hi)
		if t < t_min:
			print(f' :: WARNING :: \n DEVICE {sensor.serial_string} BELOW TARGET TEMPERATURE \n TURN ON HEAT SOURCE FOR {sensor.location} IN THE PUMP LINE')
			return -1
		elif t > t_max:
			print(f' :: WARNING :: \n DEVICE {sensor.serial_string} ABOVE TARGET TEMPERATURE \n TURN OFF HEAT SOURCE FOR {sensor.location} IN THE PUMP LINE')
			return 1
		else:
			return 0

	def set_location_temperature(self, loc, targ):    # expecting Celsius
		if loc in const.locations:
			sensor_list = manager.get_sensors_for_location(loc)
			if not sensor_list:
				print(f'No sensors found for location {loc}')
				return
			for s in sensor_list:
				if isinstance(s, DS18B20):
					s.set_target_temperature_c(targ)
	 
	def set_location_flux_allowance(self, loc, flux):
		if loc in const.locations:
			sensor_list = manager.get_sensors_for_location(loc)
			if not sensor_list:
				print(f'No sensors found for location {loc}')
				return
			for s in sensor_list:
				if isinstance(s, DS18B20):
					s.set_temp_flux_allowance(flux)

# ------------------------------------------------------------------------------------------------------------

	def reset():
		"""
		RESET
		Master sends a reset pulse (by pulling the 1-Wire bus low for at least 8 time slots) 
		and any/all DS18B20 devices respond with a presence pulse.

		NOTE: This MUST be called prior to any ROM commands/device functions as a part of the 
		necessary initialization process
		(exceptions to this are Search ROM and Search Alarms, for which both must re-initialize
		after executing)
		"""
		bram = OneWire.bram
		bram.write(const.addrs['CON_ADDR'], const.con_reg_cmds['RESET_PULSE'])
		r_status = bram.read(const.addrs['STA_ADDR'])
		x = r_status & const.masks['STA_RSD']
		count = 0
		while x == 0:
			r_status = bram.read(const.addrs['STA_ADDR'])
			x = r_status & const.masks['STA_RSD']
			count += 1
			if count > 20:
				print('No presence pulse detected thus no devices on the bus!')
				return False
			util.time_out()
		return True

	def match_rom(ichoice):
		"""
		MATCH ROM [55h]
		The match ROM command allows to address a specific slave device on a multidrop or single-drop bus.
		Only the slave that exactly matches the 64-bit ROM code sequence will respond to the function command
		issued by the master; all other slaves on the bus will wait for a reset pulse.
		"""
		bram = OneWire.bram
		bram.write(const.addrs['CMD_ADDR'], const.rom_cmds['MTCH_ROM'])
		bram.write(const.addrs['WRS_ADDR'], const.TRANSMIT_BITS)
		bram.write(const.addrs['WR0_ADDR'], OneWire.romad[ichoice * 2])
		bram.write(const.addrs['WR1_ADDR'], OneWire.romad[(ichoice * 2) + 1])
		bram.write(const.addrs['CON_ADDR'], const.con_reg_cmds['EXEC_WO_PULLUP'])
		r_status = bram.read(const.addrs['STA_ADDR'])
		x = r_status & const.masks['STA_WRD']
		count = 0
		while x == 0:
			r_status = bram.read(const.addrs['STA_ADDR'])
			x = r_status & const.masks['STA_WRD']
			count += 1
			if (count > 20):
				print('Desired ROM address not matched')
				return False
			util.time_out()
		return True

	def convert_temp():
		"""
		CONVERT T [44h]
		This command initiates a single temperature conversion.
		"""
		bram = OneWire.bram
		bram.write(const.addrs['CMD_ADDR'], const.func_cmds['CONVT_TEMP'])
		bram.write(const.addrs['CON_ADDR'], const.con_reg_cmds['EXEC_W_PULLUP'])
		sleep(const.T_CONV)
		r_status = bram.read(const.addrs['STA_ADDR'])
		return (r_status == 0x8)

	def read_scratch():
		"""
		READ SCRATCHPAD [BEh]
		This command allows the master to read the contents of the scratchpad register.
		Note: master must generate read time slots immediately after issuing the command.
		"""
		bram = OneWire.bram
		bram.write(const.addrs['CMD_ADDR'], const.func_cmds['SCRATCH_RD'])
		bram.write(const.addrs['RDS_ADDR'], const.SCRATCH_RD_SIZE)
		bram.write(const.addrs['CON_ADDR'], const.con_reg_cmds['RD_TIME_SLOTS'])
		r_status = bram.read(const.addrs['STA_ADDR'])
		x = r_status & const.masks['STA_RDD']
		count = 0
		while x == 0:
			r_status = bram.read(const.addrs['STA_ADDR'])
			x = r_status & const.masks['STA_RDD']
			count += 1
			if count > 20:
				print('Scratchpad Read Error')
				return False
			util.time_out()
		return True

	''' Use setattr(object, name, value) for assigning attribute values
	'''
	def search(search_cmd, rom_array, bram=None):
		"""
		SEARCH ROM [F0h]
		The master learns the ROM codes through a process of elimination that requires the master to perform
		a Search ROM cycle as many times as necessary to identify all of the slave devices.

		Returns the count of all device IDs discovered on the bus.

		This function has been configured so that an ALARM SEARCH [ECh] command and an alarms_array may
		be passed in to only collect ROMs of slaves with a set alarm flag.
		"""
		OneWire.set_clk(const.CLK_MHZ)
		if bram is None:
			bram = OneWire.bram
		con_reg = const.addrs['CON_ADDR']
		stat_reg = const.addrs['STA_ADDR']
		cmd_reg = const.addrs['CMD_ADDR']
		fnd_reg = const.addrs['FND_ADDR']
		bram.write(cmd_reg, search_cmd)  # write search command to the command register
		bram.write(con_reg, const.con_reg_cmds['SERIALIZE'])  # serialize command to begin search
		r_status = bram.read(stat_reg)
		print(f"r_status = {hex(r_status)}")
		x = r_status & const.masks['STA_SRD']
		miss_count = 0
		while x != 1 and miss_count < 30:
			r_status = bram.read(stat_reg)
			print(f"r_status = {hex(r_status)}")
			x = r_status & const.masks['STA_SRD']
			util.time_out()
			miss_count+=1
		err = (r_status & const.masks['STA_SER'])
		if err:
			print('SEARCH PROTOCOL ERROR : SEARCH INCOMPLETE DUE TO ONE WIRE PROTOCOL ERROR\n')
			return False
		else:
			if r_status & const.masks['STA_SME']:
				print('SEARCH MEMORY ERROR : NOT ENOUGH FPGA MEMORY ALLOCATED FOR # of OW DEVICES FOUND\n')
				return False
		#OneWire.set_clk(100)
		num_found = bram.read(fnd_reg)
		OneWire.num_roms = num_found
		new_size = num_found * 2
		if new_size > OneWire.ROMAD_SIZE:
			OneWire.ROMAD_SIZE = new_size
		print(f'# ROMS FOUND = {num_found}')
		index = 0
		while index < num_found:
			rp0 = const.addrs['RM0_ADDR'] + (index * 8)
			rp1 = const.addrs['RM1_ADDR'] + (index * 8)
			rom_lo = bram.read(rp0)
			rom_hi = bram.read(rp1)
			rom_tmp = rom_hi << 32
			rom_long = rom_tmp + rom_lo
			rom_array[index * 2] = rom_lo
			# setattr(OneWire, rom_array[index * 2], rom_lo)
			rom_array[(index * 2) + 1] = rom_hi
			# setattr(OneWire, rom_array[(index * 2) + 1], rom_hi)
			id_string = format(rom_long, 'X')
			print(f"ROM {index} ID: {id_string}")
			if not manager.id_exists(id_string):
				new_sensor = DS18B20(rom_hi, rom_lo)
				new_sensor.location = ui.prompt_location(new_sensor)    # future GUI prompt functions
				ui.prompt_target(new_sensor)
				manager.add_device(new_sensor)
				#if new_sensor.last_read_temp == 0.00:
				OneWire.get_temperature(new_sensor)
			index += 1
		OneWire.search_complete = 1
		#OneWire.set_clk(100)
		return (index)

# ------------------------------------------------------------------------------------------------------------

	# Polls the bus for devices & returns number of slaves
	def search_roms(roms_arr=None):
		if roms_arr is None or isinstance(roms_arr, OneWire):
			roms_arr = OneWire.romad
		while not OneWire.bus_initialized:
			util.time_out()
		OneWire.num_roms = OneWire.search(const.rom_cmds['SRCH_ROM'], roms_arr)
		return OneWire.num_roms
	 
	def get_temperature(dev=None):
		"""
		Calculate temperature from the scratchpad
		"""
		OneWire.set_clk(const.CLK_MHZ)
		bram = OneWire.bram
		if OneWire.num_roms < 1:
			print('\tNo OW devices found on the bus!')
			return False
		ichoice = -1
		if dev is None:
			print('Get temperature of which OW device (enter number):\n')   # GUI
			for i in range(OneWire.num_roms):
				addr_long = OneWire.get_id(i)
				print(f" {i}: {addr_long}")
			print('')
			ichoice = util.getch()
			while ichoice >= OneWire.num_roms:
				print('\nInvalid device number, try again:')
				ichoice = util.getch()
		elif isinstance(dev, DS18B20):
			ichoice = OneWire.get_device_index(dev)
		elif isinstance(dev, str) and len(dev)==16:
			ichoice = OneWire.get_rom_id_index(dev)
		if ichoice < 0:
			print('AN ERROR OCCURRED DURING get_temperature CALL')
			return 0
		''' reset pulse (all devices respond w/ a presence pulse) '''
		success = OneWire.reset()
		if not success:
			print('\n\tAN ERROR OCCURRED DURING RESET\n')
			return 0
		''' match rom '''
		success = OneWire.match_rom(ichoice)
		if not success:
			print('\n\tAN ERROR OCCURRED DURING ROM MATCH\n')
			return 0
		''' convert Temp '''
		success = OneWire.convert_temp()
		if not success:
			print('\n\tAN ERROR OCCURRED DURING TEMPERATURE CONVERSION\n')
			return 0
		''' reset again '''
		success = OneWire.reset()
		if not success:
			print('\n\tAN ERROR OCCURRED DURING RESET\n')
			return 0
		''' match rom again '''
		success = OneWire.match_rom(ichoice)
		if not success:
			print('\n\tAN ERROR OCCURRED DURING ROM MATCH\n')
			return 0
		''' read scratch reg '''
		success = OneWire.read_scratch()
		if not success:
			print('\n\tAN ERROR OCCURRED WHILE READING SCRATCHPAD\n')
			return 0
		tempo = bram.read(const.addrs['RD0_ADDR'])
		cels = util.celsius_from_raw(tempo)
		fahr = util.fahr_from_celsius(cels)
		''' Display Read registers '''
		print(f'\nDEVICE {ichoice} TEMPERATURE = [{cels}{const.DEG}C | {fahr}{const.DEG}F] \n')
		target_id = OneWire.get_id(ichoice)
		sensor = manager.get_device(target_id)
		if sensor is not None:
			#sensor.last_read_temp = fahr
			sensor.last_read_temp = cels
			manager.append_log(sensor)
		else:
			print('devicemanager could not identify the sensor id')
		return cels
 
 #==================================================================================
 # Location-grouped temperature retrieval wrappers
	def hlt_temp(self):
		return util.avg(manager.get_sensors_for_location("HLT"))
			 
	def mlt_temp(self):
		return util.avg(manager.get_sensors_for_location("MLT"))

	def bk_temp(self):
		return util.avg(manager.get_sensors_for_location("BK"))
	 
	def heatex_in_temp(self):
		return util.avg(manager.get_sensors_for_location("HEATEXIN"))
	 
	def heatex_out_temp(self):
		return util.avg(manager.get_sensors_for_location("HEATEXOUT"))
	 
	def unmapped_temp(self):
		return util.avg(manager.get_sensors_for_location("NONE"))
