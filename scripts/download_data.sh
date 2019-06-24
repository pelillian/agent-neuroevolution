#!/bin/bash

s=$1

d=$( date +"%Y-%m-%d_%H-%M-%S" )
d=$(echo ${d} | tr '[:upper:]' '[:lower:]')
echo ${d}

mkdir ~/Git/neuroevolved-agents/run/${d}
scp -i ~/Scripts/neuro.pem ubuntu@${s}:~/Git/neuroevolved-agents/snapshot_iter000\*.h5 ~/Git/neuroevolved-agents/run/${d}
scp -i ~/Scripts/neuro.pem ubuntu@${s}:~/user_data.log ~/Git/neuroevolved-agents/run/${d}
