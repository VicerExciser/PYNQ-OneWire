#!/bin/bash
while ! git pull; do echo -e "\n.\n"; sleep 2s; done
