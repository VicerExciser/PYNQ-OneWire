import re

###################################################################################################

FAMILY_CODE = 0x28
CONV_TIME = 0.750  		## Temp conversion time, default value
RW_TIME = 0.010  			## EEPROM write time, default value
TRANSMIT_BITS = 0x40  	## 64-bits to transmit over the bus
SCRATCH_RD_SIZE = 0x48  ## read in 72 bits from scratch reg


rom_cmds = { 
				'SRCH_ROM' : 0x000000F0,  ## Search Rom
				'READ_ROM' : 0x00000033,  ## Read Rom // can be used in place of search_rom if only 1 slave
				'MTCH_ROM' : 0x00000055,  ## Match Rom
				'SKIP_ROM' : 0x000000CC,  ## Skip Rom
				'ALRM_SRCH': 0x000000EC,  ## Alarm Search
			}

func_cmds = { 	
				'CONVT_TEMP' : 0x44,  ## Convert Temp
				'SCRATCH_WR' : 0x4E,  ## Write Scratchpad: write 3 bytes of data to device scratchpad
				'SCRATCH_RD' : 0xBE,  ## Read Scratchpad
				'SCRATCH_CPY': 0x48,  ## Copy Scratchpad
				'RECALL_ATV' : 0xB8,  ## Recall Alarm Trigger Values
				'POWER_RD'   : 0xB4,  ## Read Power Supply
			}

###################################################################################################

MIN_TEMP_TARG_C = 0.00
MIN_TEMP_TARG_F = 32.00
MAX_TEMP_TARG_C = 105.00
MAX_TEMP_TARG_F = 221.00 

DEG = '°'
DEG_C = f'{DEG}C'
DEG_F = f'{DEG}F'
PLUSMINUS = '±'

# following unicode must be used as:   print(u'{0}'.format(UNI_DEGR))
UNI_DEGR = u'\u00B0'	# °
UNI_DEGR_C = u'\u2103'	# ℃  
UNI_DEGR_F = u'\u2109' 	# ℉


###################################################################################################

def celsius_from_raw(temp_raw):
	return round(float((temp_raw & 0x0000FFFF) / 16.0), 3)

def celsius_from_fahr(temp_f):
	return round(((temp_f - 32.0) * (5.0 / 9.0)), 3)

def fahr_from_raw(temp_raw):
	return fahr_from_celsius(celsius_from_raw(temp_raw))

def fahr_from_celsius(temp_c):
	return round((((9.0 / 5.0) * temp_c) + 32.0), 3)

def avg(sensors):
	tot = 0.0
	if not sensors:
		return tot
	num = len(sensors)	
	for s in sensors:
		tot += s.last_read_temp
	return float(tot / num)


def get_float_input(prompt_text='Enter a floating point number: ', error_text='Invalid Number'):
	regx = re.compile('\d+(\.\d+)?')
	val = None
	while val is None or not regx.match(repr(val)) or float(val) < 0:
		try:
			val = float(input(prompt_text))
		except ValueError:
			print(error_text)
	return val


def clamp_alarm(alarm, unit=DEG_C):
	if not isinstance(alarm, float):
		alarm = float(alarm)
	if unit == DEG_F:
		return MIN_TEMP_TARG_F if alarm < MIN_TEMP_TARG_F else (MAX_TEMP_TARG_F if alarm > MAX_TEMP_TARG_F else alarm)
	else:
		return MIN_TEMP_TARG_C if alarm < MIN_TEMP_TARG_C else (MAX_TEMP_TARG_C if alarm > MAX_TEMP_TARG_C else alarm)





def split_rid_to_string(rom_hi, rom_lo, device=None):
	rid = (rom_hi << 32) + rom_lo
	if device is not None:
		device.id = rid
	return (hex(rid).partition('x'))[2].upper()


###################################################################################################

class DS18B20(object):
	'''
	Each instance of this class will represent an individual temperature sensor
	on the bus. Getters and setters have been implemented for accessing a
	particular sensor's 64-bit serial ROM ID code, the last read-in temperature
	(in Fahrenheit), and the high and low alarm thresholds.
	'''

	def __init__(self, rom_hi, rom_lo, onewire_index=None, last_read=0.00, target=76.667, flux=1.5):
		self.rom_index = onewire_index 	## Index into discoverer OneWire instance's 'rom_addr' array
		self.__rom_id = (rom_hi << 32) + rom_lo
		self.__serial_string = hex(self.rom_id).split('x')[-1].upper()
		self.last_read_temp = float(last_read)
		self.__target_temp = float(target)
		self.__temp_flux = float(flux)
		self.alarm_lo = self.__target_temp - self.__temp_flux
		self.alarm_hi = self.__target_temp + self.__temp_flux

	def __str__(self):
		return self.details_string

	def __repr__(self):
		return self.serial_string

	def details_string(self):
		ss = self.serial_string
		lrt_c = self.last_read_temp
		lrt_f = fahr_from_celsius(lrt_c)
		tt_c = self.target_temp
		tt_f = fahr_from_celsius(tt_c)
		flx_c = self.temp_flux
		flx_f = fahr_from_celsius(flx_c)    ## Flux conversion needs to be calibrated more appropriately
		return f"{self.__class__.__name__}\tSerial ID {ss}\n\tMost Recent Temp was {lrt_c}{DEG_C}  ({lrt_f}{DEG_F})\n\tTarget Temp set to {tt_c} {PLUSMINUS} {flx_c}{DEG_C}  ({tt_f} {PLUSMINUS} {flx_f}{DEG_F})\n"

	def set_target_temperature_c(self, targ):
		new_t = clamp_alarm(targ)
		self.target_temp = new_t
		self.set_temp_flux_allowance(self.temp_flux)

	def set_target_temperature_f(self, targ):
		c_targ = celsius_from_fahr(targ)
		self.set_target_temperature_c(c_targ)

	def set_temp_flux_allowance(self, flux):
		fl_val = float(flux)
		self.temp_flux = fl_val
		self.alarm_lo = clamp_alarm(self.target_temp - fl_val)
		self.alarm_hi = clamp_alarm(self.target_temp + fl_val)

	@property
	def rom_id(self):
		## Returns the literal integer value of the hexadecimal serial_string
		return self.__rom_id

	@property
	def rom_hi(self):
		return self.rom_id >> 32

	@property
	def rom_lo(self):
		return self.rom_id & 0xFFFFFFFF

	@property
	def target_temp(self):
		return self.__target_temp

	@target_temp.setter
	def target_temp(self, value):
		self.set_target_temperature_c(value)

	@property
	def temp_flux(self):
		return self.__temp_flux

	@temp_flux.setter
	def temp_flux(self, value):
		self.set_temp_flux_allowance(value)

	@property
	def serial_string(self):
		return self.__serial_string.upper()

	# @serial_string.setter
	# def serial_string(self, value):
	# 	if isinstance(value, str):
	# 		self.__serial_string = value.upper()
	
	def equals(self, other):
		check1 = isinstance(other, DS18B20)
		check2 = self.rom_id == other.rom_id
		check3 = self.serial_string == other.serial_string
		return check1 and check2 and check3
	
###################################################################################################


