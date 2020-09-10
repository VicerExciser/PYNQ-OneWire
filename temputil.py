import sys, re
import core.const as const

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
