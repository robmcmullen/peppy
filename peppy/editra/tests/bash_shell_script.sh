#!/bin/bash
# Cleans up all the junk files from the project directories

CWD=$(pwd)
EXPATH=$(dirname $0)
SCRIPT=$(basename $0)

BLUE="[34;01m"
CYAN="[36;01m"
GREEN="[32;01m"
RED="[31;01m"
YELLOW="[33;01m"
OFF="[0m"

echo "${YELLOW}**${OFF} Cleaning Project Directories ${YELLOW}**${OFF}"
sleep 2

# Go to the script directory
cd $EXPATH
z
# Go to project
cd ..
PROJDIR=$(pwd)

echo "${YELLOW}**${OFF} Starting from project root $PROJDIR"
ls *~ 2>/dev/null
if [ $? -eq 0 ]; then
   for f in $(ls *~); do
	echo "${RED}Deleting${OFF} $f";
	rm -f "$f";
   done
fi

for item in $(ls -R); do
	if [ "$(echo $item | grep \: )" != "" ]; then
	       dest=$(echo $item | tr -d ":");
       	       echo "${GREEN}Cleaning${OFF} $dest";
	       cd "$dest";
	       ls *~ 2>/dev/null;
	       if [ $? -eq 0 ]; then
                  for f in $(ls *~); do
		       echo "${RED}Deleting${OFF} $f";
	               rm -f $f;
	          done
	       fi
	       ls *.pyc 2>/dev/null
	       if [ $? -eq 0 ]; then
                  for f in $(ls *.pyc); do
		       echo "${RED}Deleting${OFF} $f";
	               rm -f $f;
	          done
	       fi
	       ls *.pyo 2>/dev/null
	       if [ $? -eq 0 ]; then
                  for f in $(ls *.pyo); do
		       echo "${RED}Deleting${OFF} $f";
	               rm -f $f;
	          done
	       fi
	       cd "$PROJDIR"
	fi	       
done
