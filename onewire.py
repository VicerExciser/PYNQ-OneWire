import os
import time
from pynq import MMIO, Clocks
from pynq.pl import PL
from pynq.overlays.base import BaseOverlay
import ds18b20

###################################################################################################

OVERLAY_NAME = 'vip.bit' 	## Put this bitstream file in the directory:  /home/xilinx/pynq/overlays/vip/
OVERLAY_DIR = OVERLAY_NAME.replace('.bit', '')
OVERLAY_PATH = os.path.join('/', 'home', 'xilinx', 'pynq', 'overlays', OVERLAY_DIR, OVERLAY_NAME)
OL = BaseOverlay(OVERLAY_PATH, download=(not OVERLAY_NAME == PL.bitfile_name.split('/')[-1]))

AXI_OW_IP_NAME = 'ow_master_top_0'
AXI_OW_ADDR = OL.ip_dict[AXI_OW_IP_NAME]['phys_addr']  	   ## 0x83c20000
AXI_OW_RANGE = OL.ip_dict[AXI_OW_IP_NAME]['addr_range']    ## 0x10000

OW_FCLK_IDX = 3 	## 'ow_master' module is tied to fclk3
PERIOD = 1000 	## for HeatingElement PWM period
CLK_MHZ = 33.33333	## required CPU clock scaling for 1-Wire master
TIMESLOT = 0.00006  	## 1 timeslot == 60 micro seconds
## ^ 1 bit of data is transmitted over the bus per each timeslot

bus_cmds = { 
				'SERIALIZE'     : 0x00000001,  ## send command onto the bus
				'RESET_PULSE'   : 0x00010000,  ## pulls bus low
				'EXEC_W_PULLUP' : 0x08,
				'EXEC_WO_PULLUP': 0x18,
				'RD_TIME_SLOTS' : 0x28,
			}

addr_map = { 	
			'CON_ADDR': 0x000,  ## Control Reg Offset
			'RDS_ADDR': 0x004,  ## Read Size Reg Offset
			'WRS_ADDR': 0x008,  ## Write Size Reg Offset
			'CMD_ADDR': 0x00C,  ## OW Command Reg Offset
			'CRR_ADDR': 0x010,  ## CRC Read Reg Offset
			'CRC_ADDR': 0x014,  ## CRC Count Reg Offset
			'CRW_ADDR': 0x018,  ## CRC Write Reg Offset
			'WR0_ADDR': 0x01C,  ## Write Data Low 32 Reg Offset
			'WR1_ADDR': 0x020,  ## Write Data Hi 32 Reg Offset

			'STA_ADDR': 0x040,  ## Status Reg Offset
			'RD0_ADDR': 0x044,  ## Read Data Lower Offset
			'RD1_ADDR': 0x048,  ## Read Data Low Offset
			'RD2_ADDR': 0x04C,  ## Read Data High Offset
			'RD3_ADDR': 0x050,  ## Read Data Highest Offset
			'FND_ADDR': 0x054,  ## Num ROMs Found Reg Offset

			'RM0_ADDR': 0x400,  ## Lo 32 of Serial Number of Device Reg Offset
			'RM1_ADDR': 0x404,  ## Hi 32 of Device ID Reg Offset
			'RM2_ADDR': 0x408,
			'RM3_ADDR': 0x40C,
			'RM4_ADDR': 0x410,
			'RM5_ADDR': 0x414,
		}

masks = { 	
		## Bit masks for the status register  (from `zpack.vhd`)
			'STA_SRD': 0x00000001,  ## status reg search done bit (c_uir_srd)
			'STA_UN1': 0x00000002,  ## status reg unused (c_uir_nc1)
			'STA_INT': 0x00000004,  ## status reg 1-Wire interrupt bit (c_uir_int)
			'STA_CMD': 0x00000008,  ## status reg cmd done bit (c_uir_cmdd)
			'STA_WRD': 0x00000010,  ## status reg block write done bit (c_uir_wrd)
			'STA_RDD': 0x00000020,  ## status reg block read done bit (c_uir_rdd)
			'STA_RSD': 0x00000040,  ## status reg reset done bit (c_uir_rsd)
			'STA_PRE': 0x00000080,  ## status reg presence pulse after last reset (c_uir_pre)
			'STA_CRC': 0x00000100,  ## status reg crc error bit (c_uir_crce)
			'STA_SER': 0x00000200,  ## status reg search error / no response  (c_uir_srche)
			## ^ this bit gets set if no OW devices respond to the search
			'STA_SME': 0x00000400,  ## status reg search memory error (c_uir_srme)
			'STA_BB' : 0x80000000,  ## READ ONLY: status register's busy bit (c_uir_busy)
		## Bit masks for the control register  (from `zpack.vhd`)
			'CON_SRE': 0x00000001,  ## control reg search rom/alarm bit (c_uir_srb)
			'CON_SAE': 0x00000002,  ## control reg unused (c_uir_uu1)
			'CON_CRC': 0x00000004,  ## control reg append crc bit (c_uir_acrc)
			'CON_CEN': 0x00000008,  ## control reg command enable bit (c_uir_cmden)
			'CON_WRE': 0x00000010,  ## control reg write block enable bit (c_uir_wren)
			'CON_RDE': 0x00000020,  ## control reg read block enable bit (c_uir_rden)
		}


###################################################################################################

def timeout(ticks=256):
	for c in range(1, ticks):
		for d in range(1, ticks):
			pass
	return

###################################################################################################

class OneWire():
	""" Singleton
	"""
	
	ROMAD_SIZE = 20 	## Large enough to hold 10 temp. sensor ROM IDs
	BRAM = None  #MMIO(AXI_OW_ADDR, AXI_OW_RANGE)
	
	__instance = None 
	__bus_initialized = False 
	search_complete = False 
	rom_addrs = [0] * ROMAD_SIZE
	num_roms = 0


	@staticmethod
	# def get_instance(**kwargs):
	# 	if OneWire.__instance is None:
	# 		OneWire(base_addr=kwargs['base_addr'], addr_range=kwargs['addr_range'])
	def get_instance(base_addr=AXI_OW_ADDR, addr_range=AXI_OW_RANGE):
		if AXI_OW_ADDR != base_addr or AXI_OW_RANGE != addr_range:
			OneWire.__instance = None
		if OneWire.__instance is None:
			# OneWire(base_addr=kwargs['base_addr'], addr_range=kwargs['addr_range'])
			OneWire(base_addr=base_addr, addr_range=addr_range)			
		return OneWire.__instance


	def __init__(self, base_addr=AXI_OW_ADDR, addr_range=AXI_OW_RANGE):
		""" Virtually private constructor for singleton OneWire class. """
		if OneWire.__instance is None:
			OneWire.BRAM = MMIO(base_addr, addr_range)
			# if base_addr != AXI_OW_ADDR:
			AXI_OW_ADDR = base_addr
			# if addr_range != AXI_OW_RANGE:
			AXI_OW_RANGE = addr_range
			
			OneWire.__instance = self 
			OneWire.search_complete = True 
			OneWire.rom_addrs = list()
			OneWire.num_roms = 0
			OneWire.set_clk()		## Set the PL function clock tied to the ow_master IP to 33 MHz

			OneWire.__bus_initialized = True 
			print(f"New '{self.__class__.__name__}' singleton instance has been instantiated.")


	@property
	def initialized(self):
		return self.__bus_initialized

	@staticmethod
	def initialized():
		return OneWire.__bus_initialized

	
## ---------------------------------------------------------------------------------------------

	@staticmethod
	def set_clk(mhz=CLK_MHZ, idx=OW_FCLK_IDX):
		if idx == 3:
			cur_freq = Clocks.fclk3_mhz 
		elif idx == 2:
			cur_freq = Clocks.fclk2_mhz
		elif idx == 1:
			cur_freq = Clocks.fclk1_mhz  
		elif idx == 0:
			cur_freq = Clocks.fclk0_mhz
		else:
			 print(f"[set_clk]  Invalid PL clock index: idx={idx} (must be value in range [0, 3])")
			 return
		print(f"[set_clk]  Clocks.fclk{idx}_mhz = {cur_freq}MHz")
		if abs(cur_freq - mhz) > 1: 		## Tests approximate equality to prevent call redundancy 
			print(f"[set_clk]  Setting fclk{idx} to {mhz}MHz")
			# Clocks.set_fclk(clk_idx=idx, clk_mhz=mhz)
			Clocks.set_pl_clk(idx, clk_mhz=mhz)


	@staticmethod
	def bram_write(reg_addr, cmd):
		OneWire.BRAM.write(reg_addr, cmd)

	@staticmethod
	def bram_read(reg_addr):
		return OneWire.BRAM.read(reg_addr)


	@staticmethod
	def reset_pulse():
		"""
		RESET
		Master sends a reset pulse (by pulling the 1-Wire bus low for at least 8 time slots) 
		and any/all [DS18B20] devices respond with a presence pulse.

		NOTE: This MUST be called prior to any ROM commands/device functions as a part of the 
		necessary initialization process
		(exceptions to this are Search ROM and Search Alarms, for which both must re-initialize
		after executing)
		"""

		OneWire.bram_write(addr_map['CON_ADDR'], bus_cmds['RESET_PULSE'])
		r_status = OneWire.bram_read(addr_map['STA_ADDR'])
		x = r_status & masks['STA_RSD']
		count = 0
		while x == 0:
			r_status = OneWire.bram_read(addr_map['STA_ADDR'])
			x = r_status & masks['STA_RSD']
			count += 1
			if count > 20:
				print('No presence pulse detected thus no devices on the bus!')
				return False
			timeout()
		return True

	'''
	@staticmethod
	def match_rom(ichoice):
		"""
		MATCH ROM [55h]
		The match ROM command allows to address a specific slave device on a multidrop or single-drop bus.
		Only the slave that exactly matches the 64-bit ROM code sequence will respond to the function command
		issued by the master; all other slaves on the bus will wait for a reset pulse.
		"""
		OneWire.bram_write(addr_map['CMD_ADDR'], ds18b20.rom_cmds['MTCH_ROM'])
		OneWire.bram_write(addr_map['WRS_ADDR'], ds18b20.TRANSMIT_BITS)
		OneWire.bram_write(addr_map['WR0_ADDR'], OneWire.rom_addrs[ichoice * 2])
		OneWire.bram_write(addr_map['WR1_ADDR'], OneWire.rom_addrs[(ichoice * 2) + 1])
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
	'''
	
	def get_rom_id(sensor_index):
		if 0 <= sensor_index < OneWire.ROMAD_SIZE:  #len(OneWire.rom_addrs):
			true_idx = sensor_index * 2
			rom_lo = OneWire.rom_addrs[true_idx]
			rom_hi = OneWire.rom_addrs[true_idx + 1]
			rom_id = (rom_hi << 32) + rom_lo
			return hex(rom_id).split('x')[-1].upper()
			# return OneWire.rom_addrs[sensor_index]
		return None
	
	
## ---------------------------------------------------------------------------------------------

	## Polls the bus for devices & returns number of slaves

	@staticmethod
	def search(SensorClass, search_cmd):
		"""
		SEARCH ROM [F0h]
		The master learns the ROM codes through a process of elimination that requires the master to perform
		a Search ROM cycle as many times as necessary to identify all of the slave devices.

		Returns the count of all device IDs discovered on the bus.

		This function has been configured so that an ALARM SEARCH [ECh] command and an alarms_array may
		be passed in to only collect ROMs of slaves with a set alarm flag.
		"""

		if not OneWire.initialized():
			OneWire()

		while OneWire.search_complete == False:
			print('.', end='')
			timeout()

		OneWire.search_complete = False

		con_reg = addr_map['CON_ADDR']
		stat_reg = addr_map['STA_ADDR']
		cmd_reg = addr_map['CMD_ADDR']
		fnd_reg = addr_map['FND_ADDR']
		OneWire.bram_write(cmd_reg, search_cmd)  # write search command to the command register
		OneWire.bram_write(con_reg, bus_cmds['SERIALIZE'])  # serialize command to begin search

		r_status = OneWire.bram_read(stat_reg)
		print(f"r_status = {hex(r_status)}")
		x = r_status & masks['STA_SRD']
		miss_count = 0
		while x != 1 and miss_count < 30:
			r_status = OneWire.bram_read(stat_reg)
			print(f"r_status = {hex(r_status)}")
			x = r_status & masks['STA_SRD']
			timeout()
			miss_count += 1

		err = (r_status & masks['STA_SER'])
		if err:
			print('SEARCH PROTOCOL ERROR : SEARCH INCOMPLETE DUE TO ONE WIRE PROTOCOL ERROR\n')
			return False
		else:
			if r_status & masks['STA_SME']:
				print('SEARCH MEMORY ERROR : NOT ENOUGH FPGA MEMORY ALLOCATED FOR # of OW DEVICES FOUND\n')
				return False

		num_found = OneWire.bram_read(fnd_reg)
		OneWire.num_roms = num_found
		new_size = num_found * 2
		if new_size > OneWire.ROMAD_SIZE:
			OneWire.ROMAD_SIZE = new_size
			OneWire.rom_addrs = [0] * new_size
		print(f'# ROMS FOUND = {num_found}')

		index = 0
		while index < num_found:
			rom_lo = OneWire.bram_read((addr_map['RM0_ADDR'] + (index << 3)))
			rom_hi = OneWire.bram_read((addr_map['RM1_ADDR'] + (index << 3)))
			rom_long = (rom_hi << 32) + rom_lo
			OneWire.rom_addrs[index * 2] = rom_lo
			OneWire.rom_addrs[(index * 2) + 1] = rom_hi
			print(f"ROM {index} ID: {hex(rom_long)}")

			new_sensor = SensorClass(rom_hi, rom_lo, onewire_index=index)
			yield new_sensor 

			index += 1

		OneWire.search_complete = True
		# return (index)

## ---------------------------------------------------------------------------------------------

if __name__ == "__main__":
	ow_bus = OneWire.get_instance()



