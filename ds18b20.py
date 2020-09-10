# -*- coding: utf-8 -*-
import core.const as const
import core.temputil as util
#from components import BrewSystem

MIN_TEMP_TARG_C = 0.00
MIN_TEMP_TARG_F = 32.00
MAX_TEMP_TARG_C = 105.00
MAX_TEMP_TARG_F = 221.00 

DEG = '°'
DEG_C = f'{DEG}C'
DEG_F = f'{DEG}F'
PLUSMINUS = '±'

# following unicode must be used as:   print(u'{0}'.format(const.UNI_DEGR))
UNI_DEGR = u'\u00B0'	# °
UNI_DEGR_C = u'\u2103'	# ℃  
UNI_DEGR_F = u'\u2109' 	# ℉

###################################################################################################

def celsius_from_raw(temp_raw):
	tempo = temp_raw & 0x0000FFFF
	return float('%.3f'%(tempo / 16))

def celsius_from_fahr(temp_f):
	tempo = float(temp_f) - 32.0
	return float('%.3f'%(tempo * (5.0 / 9.0)))

def fahr_from_raw(temp_raw):
	return fahr_from_celsius(celsius_from_raw(temp_raw))

def fahr_from_celsius(temp_c):
	tempo = (9.0 / 5.0) * float(temp_c)
	return float('%.3f'%(tempo + 32.0))

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

def clamp_alarm(alm, unit=const.DEG_C):
	alarm = alm
	if not isinstance(alm, float):
		alarm = float(alm)
	if unit == const.DEG_F:
		return const.MIN_TEMP_TARG_F if alarm < const.MIN_TEMP_TARG_F else (const.MAX_TEMP_TARG_F if alarm > const.MAX_TEMP_TARG_F else alarm)
	else:
		return const.MIN_TEMP_TARG_C if alarm < const.MIN_TEMP_TARG_C else (const.MAX_TEMP_TARG_C if alarm > const.MAX_TEMP_TARG_C else alarm)


def time_out(ticks=256):
	for c in range(1, ticks):
		for d in range(1, ticks):
			pass
	return

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

	def __init__(self, rom_hi=0x0, rom_lo=0x0, location=None, last_read=0.00, target=76.667, flux=1.5):
		#self._id = (rom_hi << 32) + rom_lo
		self.__serial_string = util.split_rid_to_string(rom_hi, rom_lo, self)
		self.__location = location
		self.last_read_temp = float(last_read)
		self.__target_temp = float(target)
		self.__temp_flux = float(flux)
		self.alarm_lo = self.__target_temp - self.__temp_flux
		self.alarm_hi = self.__target_temp + self.__temp_flux
		self.log_filepath = ""
		#self._log_dir_path = ""

	def __str__(self):
		return self.__serial_string

	def __repr__(self):
		return self.__serial_string

	def details_string(self):            # TODO: resolve unknown characters displaying w/ DEG and PLUSMINUS
		ss = self.__serial_string
		lrt_c = self.last_read_temp
		lrt_f = util.fahr_from_celsius(lrt_c)
		tt_c = self.__target_temp
		tt_f = util.fahr_from_celsius(tt_c)
		flx_c = self.__temp_flux
		flx_f = util.fahr_from_celsius(flx_c)    # Flux conversion needs to be calibrated more appropriately
		cd = const.DEG
		pm = const.PLUSMINUS
		#id_str = "   Sensor ID        -->  {0}\n"
		#rt_str = "   Most Recent Temp -->  {0}"
		#tt_str = "   Target Temp      -->  {0}"
		return "  Serial ID {0}\n   Most Recent Temp was [{1}{2}C / {3}{4}F]\n   Target Temp set to [({5}{6}{7}){8}C / ({9}{10}{11}){12}F]\n".format(ss,lrt_c,cd,lrt_f,cd,tt_c,pm,flx_c,cd,tt_f,pm,flx_f,cd)
		#return "  Serial ID {0}\n   Most Recent Temp = {1}F\n   Alarm Thresholds from {2}F to {3}F".format(self.serial_string, self.last_read_temp, self.alarm_lo, self.alarm_hi)

	def set_target_temperature_c(self, targ):
		new_t = util.clamp_alarm(targ)
		self.__target_temp = new_t
		self.set_temp_flux_allowance(self.__temp_flux)

	def set_target_temperature_f(self, targ):
		c_targ = util.celsius_from_fahr(targ)
		self.set_target_temperature_c(c_targ)

	def set_temp_flux_allowance(self, flux):
		fl_val = float(flux)
		self.__temp_flux = fl_val
		self.alarm_lo = util.clamp_alarm(self.__target_temp - fl_val)
		self.alarm_hi = util.clamp_alarm(self.__target_temp + fl_val)

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
		#self.__temp_flux = float(value)
		self.set_temp_flux_allowance(value)

	@location.deleter
	def location(self):
		del self.__location

	@property
	def serial_string(self):
		return self.__serial_string

	@serial_string.setter
	def serial_string(self, value):
		self.__serial_string = value

	# @property
	# def last_read_temp(self):
	# 	#print("getter of last_read_temp called")
	# 	return self.last_read_temp

	# @last_read_temp.setter
	# def last_read_temp(self, value):                # Temp in Celsius by default
	# 	#print("setter of last_read_temp called")
	# 	self.last_read_temp = value

	# @property
	# def id(self):
	# 	#print("getter of id called")
	# 	return self._id

	# @id.setter
	# def id(self, value):
	# 	#print("setter of id called")
	# 	self._id = value

	# @id.deleter
	# def id(self):
	# 	#print("deleter of id called")
	# 	del self._id

	# @property
	# def alarm_hi(self):
	# 	#print("getter of alarm_hi called")
	# 	return self._alarm_hi

	# @alarm_hi.setter
	# def alarm_hi(self, value):
	# 	#print("setter of alarm_hi called")
	# 	self._alarm_hi = value

	# @property
	# def alarm_lo(self):
	# 	#print("getter of alarm_lo called")
	# 	return self._alarm_lo

	# @alarm_lo.setter
	# def alarm_lo(self, value):
	# 	#print("setter of alarm_lo called")
	# 	self._alarm_lo = value

	# @property
	# def log_filepath(self):
	# 	return self.log_filepath

	#@property
	#def log_dir_path(self):
	#	return self._log_dir_path
	
	def equals(self, other):
		check1 = isinstance(other, DS18B20)
		check2 = self.__serial_string.upper() == other.serial_string.upper()
		check3 = self.__location.upper() == other.location.upper()
		return check1 and check2 and check3
	