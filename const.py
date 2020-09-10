from pynq import Overlay 	# for debug
from pynq.overlays.base import BaseOverlay

# OVERLAY_PATH = '/home/xilinx/pynq/overlays/base/design_1_wrapper.bit'
# OVERLAY_PATH = '/home/xilinx/pynq/overlays/base/system.bit'
# OVERLAY_PATH = '/home/xilinx/pynq/overlays/base/test17.bit'
# OVERLAY_PATH = '/home/xilinx/pynq/overlays/vip/test17.bit'
OVERLAY_PATH = 'vip.bit'
OVERLAY_PATH_FULL = '/home/xilinx/pynq/overlays/vip/vip.bit'
# BASE = BaseOverlay("base.bit")
#If custom overlay is extension of base.bit (as it truly should be...)
BASE = BaseOverlay(OVERLAY_PATH_FULL)
# BASE = Overlay(OVERLAY_PATH)	# for debug
# BASE = None 	# for testing of 1-Wire only

SAVE_DIRECTORY = '/home/xilinx/Brewery/savefiles'
DEVICES_PATH = '/home/xilinx/Brewery/savefiles/device_data.csv'
CONFIG_PKL = '/home/xilinx/Brewery/savefiles/config.pkl'
SENSOR_PKL = '/home/xilinx/Brewery/savefiles/sensors.pkl'
POLL_SCRIPT = '/home/xilinx/Brewery/routines/polltemps.py'

# AXI_OW_ADDR = 0x43C00000
# AXI_OW_ADDR = 0x43C80000	# top.bit OneWire module offset
AXI_OW_ADDR = 0x83C20000	# vip.bit OneWire module offset
AXI_OW_RANGE = 0xFFFF

TRANSMIT_BITS = 0x40  # 64-bits to transmit over the bus
SCRATCH_RD_SIZE = 0x48  # read in 72 bits from scratch reg
TIMESLOT = 0.00006  # 1 timeslot == 60 micro seconds
# ^ 1 bit of data is transmitted over the bus per each timeslot
FAMILY_CODE = 0x28
T_CONV = 0.750  # Temp conversion time, default value
T_RW = 0.010  # EEPROM write time, default value
MIN_TEMP_TARG_C = 0.00
MIN_TEMP_TARG_F = 32.00
MAX_TEMP_TARG_C = 105.00
MAX_TEMP_TARG_F = 221.00 

PERIOD = 1000 	# for HeatingElement PWM period
CLK_MHZ = 33.33333	# required CPU clock scaling for 1-Wire master
OW_FCLK_IDX = 3 	# ow_master module is tied to fclk3

DEG = '°'
DEG_C = '°C'
DEG_F = '°F'
#DEG = ''
#PLUSMINUS = ''
PLUSMINUS = '±'

# following unicode must be used as:   print(u'{0}'.format(const.UNI_DEGR))
UNI_DEGR = u'\u00B0'	# °
UNI_DEGR_C = u'\u2103'	# ℃  
UNI_DEGR_F = u'\u2109' 	# ℉

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

locations = ['HLT', 'MLT', 'BK', 'HEATEXIN', 'HEATEXOUT', 'WATERPUMP', 'WORTPUMP', 'NONE']
component_keys = ["HLT", "MLT", "BK", "HeatExchanger", "WaterPump", "WortPump"] #, "Comp"]


def loc_full_name(loc):
		if loc == 'HLT':
			return 'Hot Liquor Tank (HLT)'
		elif loc == 'MLT':
			return 'Mash Lauter Tun (MLT)'
		elif loc == 'BK':
			return 'Boiling Kettle (BK)'
		elif loc == 'HEATEXIN':
			return 'Heat Exchanger-Water Input (HEATEXIN)'
		elif loc == 'HEATEXOUT':
			return 'Heat Exchanger-Wort Output (HEATEXOUT)'
		elif loc == 'WATERPUMP':
			return 'Water Pump (WATERPUMP)'
		elif loc == 'WORTPUMP':
			return 'Wort Pump (WORTPUMP)'
		else:
			return 'Unmapped (NONE)'

def loc_to_comp_key(location):
		loc = location.upper()
		if loc == 'HLT' or loc == 'MLT' or loc == 'BK':
			return loc
		elif loc == 'HEATEXIN' or loc == 'HEATEXOUT':
			return 'HeatExchanger'
		elif loc == 'WATERPUMP':
			return 'WaterPump'
		elif loc == 'WORTPUMP':
			return 'WortPump'
		return 'NONE'
