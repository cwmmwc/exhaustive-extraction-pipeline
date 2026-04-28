#!/bin/bash
# Rsync the RG 60 index card collection to HPC.
SRC="$HOME/projects/exhaustive-extraction-pipeline/RG 60 index cards/"
DST='cwm6w@login.hpc.virginia.edu:/project/LawData/exhaustive-extraction-pipeline/RG\ 60\ index\ cards/'
rsync -avh --progress \
  --exclude='.DS_Store' \
  --exclude='DEVONtech_storage' \
  --exclude='desktop.ini' \
  --exclude='*.jpg' \
  --exclude='*.JPG' \
  "$SRC" "$DST"
