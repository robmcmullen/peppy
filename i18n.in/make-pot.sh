#!/bin/bash

python pygettext.py -k name -k tooltip -k label -k error -k preferences_tab -k message -o messages.1 ../peppy
msguniq -s messages.1 -o messages.pot

