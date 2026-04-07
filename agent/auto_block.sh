#!/bin/bash
cd ~/phishdns
python3 agent/blocker.py
echo "$(date): Bloqueo ejecutado" >> logs/auto_block.log
