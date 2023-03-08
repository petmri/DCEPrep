#!/bin/bash


# MAKE SURE MATLAB & FREESURFER LICENSE FILES, DATA DIRECTORY, AND /etc/ ARE SHARED TO DOCKER

bozo=$(cat /usr/local/MATLAB/*/licenses/*lic* | grep _HOSTID)

MAC=${bozo#*MATLAB_HOSTID=}
MAC=${MAC%%:*}
MAC=${MAC:0:2}:${MAC:2:2}:${MAC:4:2}:${MAC:6:2}:${MAC:8:2}:${MAC:10:2}
# echo $MAC

MATLAB_PATH=/usr/local/MATLAB/$(ls /usr/local/MATLAB/)
# echo $MATLAB_PATH

LICENSE=$(ls $MATLAB_PATH/licenses)
# echo $LICENSE

export UID=$(id -u)
export GID=$(id -g)

sudo docker run --rm -it -e MLM_LICENSE_FILE=/opt/matlab/licenses/$LICENSE \
    -v /media/network_mriphysics/USC-PPG/docker_test:/data/ \
    -v $FREESURFER_HOME/license.txt:/opt/freesurfer/license.txt \
    -v $MATLAB_PATH/licenses:/opt/matlab/licenses \
    -v /etc/passwd:/etc/passwd:ro \
    --shm-size=512M --mac-address $MAC \
    --user $UID:$GID \
    --gpus all \
    lsaca05/dce
