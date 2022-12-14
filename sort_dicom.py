#!/usr/bin/python3


from datetime import time, timedelta, datetime
from statistics import mean
import json
import pydicom
import subprocess
import os
import shutil
import sys

sort_dir = "/media/network_mriphysics/USC-PPG/bids_test/sourcedata/dicom"
output_dir = "/media/network_mriphysics/USC-PPG/bids_test/derivatives"
#sort_dir = "/media/network_mriphysics/barnes/peanut/dicom/~original_data/"
#sort_dir = "/media/network_mriphysics/barnes/peanut/nifti"

print(sort_dir)
directory = os.fsencode(sort_dir)
dir_str = os.fsdecode(directory)

subfolders = [ f for f in os.scandir(directory) if f.is_dir() ]
for subfolder in subfolders:  
    new_dir = os.fsdecode(subfolder.path)
    subname = os.fsdecode(subfolder.name)
    new_7z = os.path.join(dir_str,subname+".7z")
    if not "_s2" in subname.lower():
        session_id = '01'
        subject_id = subname
    else:
        session_id = '02'
        subject_id = subname.replace("_s2","")
        subject_id = subject_id.replace("_S2","") #cover both cases

    print("Processing ", subject_id, " session ", session_id)
    
    
    #7zip
    try:
        #output = subprocess.check_output(['7z',"a",new_7z,new_dir+"/*"])
        print("7z successful")
    except:
        print(subname + " failed 7zip")
    
    #find dicom and log directories
    file_list = os.listdir(new_dir)
    #folder should only have a "dicom" folder and a "log" folder
    if not len(file_list)==2:
        sys.exit("warning: folder has wrong structure (doesn't have only 2 subdirectories), exiting")
    dicom_dir = ""
    log_dir = ""
    if os.path.isdir(os.path.join(new_dir,file_list[0])):
        if file_list[0].lower()=='dicom':
            dicom_dir = os.path.join(new_dir,file_list[0])
        if file_list[0].lower()=='log':
            log_dir = os.path.join(new_dir,file_list[0])
    if os.path.isdir(os.path.join(new_dir,file_list[1])):
        if file_list[1].lower()=='dicom':
            dicom_dir = os.path.join(new_dir,file_list[1])
        if file_list[1].lower()=='log':
            log_dir = os.path.join(new_dir,file_list[1])
    if dicom_dir=="" or log_dir=="":
        sys.exit("warning: cannot find DICOM or LOG folder, exiting")

    # Calculate temporal resolution from difference between acquisition times
    # dce_dir = dicom_dir + "/I1164341/dicom"
    
    # ac_time = []
    # for i in range(1,2000,40):
    #     file = dce_dir + "/15-" + str(i) + ".dcm"
    #     dataset = pydicom.dcmread(file, specific_tags=["AcquisitionTime"])
    #     formatted_time = dataset.AcquisitionTime
    #     formatted_time = formatted_time[0:2] + ':' + formatted_time[2:4] + ':' + formatted_time[4:]
    #     struct = time.fromisoformat(formatted_time)
    #     bozo = timedelta(hours=struct.hour, minutes=struct.minute, seconds=struct.second, microseconds=struct.microsecond)
    #     ac_time.append(datetime.strptime(formatted_time, '%H:%M:%S.%f'))
    # # diff = []
    # # for i in range(1,50):
    # #     diff.append(float(str(ac_time[i] - ac_time[i-1])[5:]))
    # diff = ac_time[1] - ac_time[0]
    # TemporalResolution = str(diff)[5:]
    #
    # with open('config.json', 'r+') as f:
    #     data = json.load(f)
    #     data['descriptions'][1]['sidecarChanges']['TemporalResolution'] = str(TemporalResolution)
    #     f.seek(0)
    #     json.dump(data,f,indent=4)
    #     f.truncate()
    
    #DICOM to BIDS conversion
    try:
        
        output = subprocess.check_output(['dcm2bids',
                                          "-d", dicom_dir,
                                          "-p", subject_id,
                                          "-s", session_id,
                                          "-c", "config.json",
                                          "-o", output_dir])
        print("dcm2bids successful")
    except:
        print(subname+" failed dcm2bids")
    print("Files sorted")
    #remove unsorted files
    #shutil.rmtree(dicom_dir)
    
    #move log files
    bids_dir = os.path.join(output_dir,"sub-"+subject_id,"ses-"+session_id,"logs")
    os.makedirs(bids_dir,exist_ok=True)
    for root, dirs, files in os.walk(log_dir):  
        for f in files:  
            shutil.copy(os.path.join(root,f),bids_dir)
    
    
    #move unzipped files
    move_dir = new_dir
    dest_dir = os.path.join(dir_str,"..")
    shutil.move(move_dir,dest_dir)

    print("Completed")
