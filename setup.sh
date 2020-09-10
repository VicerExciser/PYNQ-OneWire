#!/bin/bash

OL_NAME='vip.bit'
TCL_NAME='vip.tcl'
OL_PATH_SRC="$(pwd)/overlay/"
OL_PATH_DST="${HOME}/pynq/overlays/vip/"

if [ $HOME = '/home/xilinx' ]; then
	echo Correct path.
	if [ ! -d $OL_PATH_DST ]; then
		echo -e "--> Creating directory '${OL_PATH_DST}' ..."
		mkdir -p $OL_PATH_DST
	fi
	echo -e "Linking source '${OL_PATH_SRC}${OL_NAME}' to destination '${OL_PATH_DST}${OL_NAME}' ..."
	ln -f "${OL_PATH_SRC}${OL_NAME}" "${OL_PATH_DST}"

	echo -e "Linking source '${OL_PATH_SRC}${TCL_NAME}' to destination '${OL_PATH_DST}${TCL_NAME}' ..."
	ln -f "${OL_PATH_SRC}${TCL_NAME}" "${OL_PATH_DST}"

	echo -e "Done.\n\n${OL_PATH_DST}:\n"
	ls -alhF $OL_PATH_DST
fi
