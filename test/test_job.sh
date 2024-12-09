#!/bin/bash
SLEEP_SECONDS=$((1 + $RANDOM % 10))
echo "Starting job, sleeping for $SLEEP_SECONDS seconds"
sleep $SLEEP_SECONDS
echo "Job finished"