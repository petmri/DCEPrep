import jinja2
import json
import os
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
import datetime
import subprocess
import threading
import time
from sys import argv
from concurrent.futures import ThreadPoolExecutor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from concurrent.futures import as_completed
from utils.constants import KTRANS_MIN_THRESHOLD

dir = argv[1]
try:
    output_dir = argv[2]
except:
    output_dir = ""

dceprep_dir = argv[1] + "/dceprep"

try:
    ROCKETSHIP_dir = argv[3]
except IndexError:
    ROCKETSHIP_dir = argv[2]
    output_dir = ""

if output_dir != "":
    output_dir = "-" + output_dir
    dceprep_dir = dceprep_dir + output_dir

# Load MRI population data dict with keys as subject IDs and values as gm and wm data
population_data = {}
population_data_exclude = {}
population_data_failed = {}
population_data_missing = {}
# list directories in dir
if not os.path.isdir(dceprep_dir):
    print(f"{dceprep_dir} does not exist, trying current working directory")
    dir_list = os.listdir(os.getcwd())
else:
    dir_list = os.listdir(dceprep_dir)
# filter out non-directories
subjects = [subject for subject in dir_list if os.path.isdir(os.path.join(dceprep_dir, subject)) and not subject.startswith("figures") and not subject.startswith("logs")]
subjects.sort()
# use text file list for subjects, format is subject date timepoint
# get list of subjects
# subjects = [f"sub-{line.split(' ')[0]}" for line in open(os.path.join(dir, "../code/CBF_list.txt"), "r").readlines()]
# get list of timepoints
# timepoints = [line.split(" ")[2][:-1] for line in open(os.path.join(dir, "../code/CBF_list.txt"), "r").readlines()]
# print(timepoints)
# go into each subject directory and count number of successful_timepoints
# for subject_id in subjects:
#     # list _timepoint directories in subject directory
#     for timepoint in os.listdir(os.path.join(dir, subject_id)):
#         if timepoint.endswith("_timepoint"):
#             successful_timepoints.append(subject_id + '/' + timepoint)
manual_aif_status = "AUTO"
# read log file for command used to run dceprep
# log is preprocessing_log_{date}.txt, use latest log
logs = os.listdir(os.path.join(dir, "logs"))
logs = [log for log in logs if log.startswith("preprocessing_log")]
logs.sort()
log = logs[-1]
log = os.path.join(dir, "logs", log)
command = ""
with open(log, "r") as f:
    for line in f:
        if "Command: " in line:
            command = line
            break
use_manual_aif = False
if "-A M" in command or "-A T" in command:
    use_manual_aif = True

# Outlier and tracking lists
Ktrans_wm_outliers, Ktrans_gm_outliers = [], []
whole_hippo_outliers, whole_phg_outliers, whole_putamen_outliers = [], [], []
whole_pallidum_outliers, whole_thalamus_outliers, whole_caudate_outliers = [], [], []
whole_amygdala_outliers, whole_entorhinal_cortex_outliers = [], []
whole_fusiform_gyrus_cortex_outliers, whole_fusiform_gyrus_WM_outliers = [], []
whole_insula_WM_outliers, whole_superior_temporal_cortex_outliers = [], []
whole_inferior_temporal_cortex_outliers, whole_posterior_cingulate_cortex_outliers = [], []
whole_medial_temporal_cortex_outliers = []

wm_outliers_exclude, gm_outliers_exclude = [], []
whole_hippo_outliers_exclude, whole_phg_outliers_exclude, whole_putamen_outliers_exclude = [], [], []
whole_pallidum_outliers_exclude, whole_thalamus_outliers_exclude, whole_caudate_outliers_exclude = [], [], []
whole_amygdala_outliers_exclude, whole_entorhinal_cortex_outliers_exclude = [], []
whole_fusiform_gyrus_cortex_outliers_exclude, whole_fusiform_gyrus_WM_outliers_exclude = [], []
whole_insula_WM_outliers_exclude, whole_superior_temporal_cortex_outliers_exclude = [], []
whole_inferior_temporal_cortex_outliers_exclude, whole_posterior_cingulate_cortex_outliers_exclude = [], []
whole_medial_temporal_cortex_outliers_exclude = []

total_timepoints, successful_timepoints = [], []
popAIF_curves, aif_curves = [], []
def get_case_stats(subject_id, timepoint):
        wmparc_failed = False
        stats_failed = False
        missing = False
        AIFitness = aif_fitted_r2 = max_disp = T1_wm_median = T1_wm_std = T1_gm_median = T1_gm_std = Ktrans_wm_mean = Ktrans_wm_median = Ktrans_wm_std = Ktrans_gm_mean = Ktrans_gm_median = Ktrans_gm_std = 0
        hippo_vol = phg_vol = putamen_vol = pallidum_vol = thalamus_vol = caudate_vol = amygdala_vol = -1
        entorhinal_cortex_vol = fusiform_gyrus_cortex_vol = fusiform_gyrus_wm_vol = insula_wm_vol = -1
        superior_temporal_cortex_vol = inferior_temporal_cortex_vol = posterior_cingulate_cortex_vol = medial_temporal_cortex_vol = -1
        Ktrans_Hippo_median = Ktrans_PhG_median = Ktrans_Putamen_median = Ktrans_Pallidum_median = -1
        Ktrans_Thalamus_median = Ktrans_Caudate_median = Ktrans_Amygdala_median = Ktrans_Entorhinal_cortex_median = -1
        Ktrans_Fusiform_gyrus_cortex_median = Ktrans_Fusiform_gyrus_WM_median = Ktrans_Insula_WM_median = -1
        Ktrans_Superior_temporal_cortex_median = Ktrans_Inferior_temporal_cortex_median = Ktrans_Posterior_cingulate_cortex_median = Ktrans_Medial_temporal_cortex_median = -1
        Vp_Hippo_median = Vp_PhG_median = Vp_Putamen_median = Vp_Pallidum_median = Vp_Thalamus_median = -1
        Vp_Caudate_median = Vp_Amygdala_median = Vp_Entorhinal_cortex_median = Vp_Fusiform_gyrus_cortex_median = -1
        Vp_Fusiform_gyrus_WM_median = Vp_Insula_WM_median = Vp_Superior_temporal_cortex_median = Vp_Inferior_temporal_cortex_median = -1
        Vp_Posterior_cingulate_cortex_median = Vp_Medial_temporal_cortex_median = SNR = -1
        bankssts_thickness_avg = bankssts_thickness_std = caudalanteriorcingulate_thickness_avg = caudalanteriorcingulate_thickness_std = -1
        caudalmiddlefrontal_thickness_avg = caudalmiddlefrontal_thickness_std = cuneus_thickness_avg = cuneus_thickness_std = -1
        entorhinal_thickness_avg = entorhinal_thickness_std = fusiform_thickness_avg = fusiform_thickness_std = -1
        inferiorparietal_thickness_avg = inferiorparietal_thickness_std = inferiortemporal_thickness_avg = inferiortemporal_thickness_std = -1
        insula_thickness_avg = insula_thickness_std = isthmuscingulate_thickness_avg = isthmuscingulate_thickness_std = -1
        lateraloccipital_thickness_avg = lateraloccipital_thickness_std = lateralorbitofrontal_thickness_avg = lateralorbitofrontal_thickness_std = -1
        lingual_thickness_avg = lingual_thickness_std = medialorbitofrontal_thickness_avg = medialorbitofrontal_thickness_std = -1
        middletemporal_thickness_avg = middletemporal_thickness_std = parahippocampal_thickness_avg = parahippocampal_thickness_std = -1
        paracentral_thickness_avg = paracentral_thickness_std = parsopercularis_thickness_avg = parsopercularis_thickness_std = -1
        parsorbitalis_thickness_avg = parsorbitalis_thickness_std = parstriangularis_thickness_avg = parstriangularis_thickness_std = -1
        pericalcarine_thickness_avg = pericalcarine_thickness_std = postcentral_thickness_avg = postcentral_thickness_std = -1
        posteriorcingulate_thickness_avg = posteriorcingulate_thickness_std = precentral_thickness_avg = precentral_thickness_std = -1
        precuneus_thickness_avg = precuneus_thickness_std = rostralanteriorcingulate_thickness_avg = rostralanteriorcingulate_thickness_std = -1
        rostralmiddlefrontal_thickness_avg = rostralmiddlefrontal_thickness_std = superiorfrontal_thickness_avg = superiorfrontal_thickness_std = -1
        superiorparietal_thickness_avg = superiorparietal_thickness_std = superiortemporal_thickness_avg = superiortemporal_thickness_std = -1
        frontalpole_thickness_avg = frontalpole_thickness_std = supramarginal_thickness_avg = supramarginal_thickness_std = -1
        temporalpole_thickness_avg = temporalpole_thickness_std = transversetemporal_thickness_avg = transversetemporal_thickness_std = -1

        if timepoint.startswith("ses-"):
            total_timepoints.append(subject_id + '/' + timepoint)
            # Check for missing data in rawdata folder
            prefix = f"{subject_id}_{timepoint}"
            rawdata_dir = os.path.join(dir, "../rawdata", subject_id, timepoint)
            missing_files = []
            # Check for anat/prefix_T1w.nii.gz
            t1w_path = os.path.join(rawdata_dir, f"anat/{prefix}_T1w.nii.gz")
            if not os.path.exists(t1w_path):
                missing_files.append("anat/" + os.path.basename(t1w_path))
            # Check for at least one anat/prefix_*_VFA.nii.gz
            anat_dir = os.path.join(rawdata_dir, "anat")
            vfa_files = []
            if os.path.isdir(anat_dir):
                vfa_files = [f for f in os.listdir(anat_dir) if f.startswith(prefix) and "_VFA" in f and f.endswith(".nii.gz")]
            if len(vfa_files) == 0:
                missing_files.append("anat/*_VFA.nii.gz")
            # Check for dce/prefix_DCE.nii.gz
            dce_path = os.path.join(rawdata_dir, f"dce/{prefix}_DCE.nii.gz")
            if not os.path.exists(dce_path):
                missing_files.append("dce/" + os.path.basename(dce_path))
            if missing_files:
                print(f"Missing rawdata for {subject_id} {timepoint}: {', '.join(missing_files)}")
                population_data_missing[subject_id + "_" + timepoint] = {"Missing_files": missing_files}
                missing = True
                return
            else:
                missing = False
            # read AIF curve by applying aif.nii to dce.nii
            try:
                dce = os.path.join(dceprep_dir, subject_id, timepoint, f"dce/{subject_id}_{timepoint}_desc-bfcz_DCE.nii.gz")
                aif = os.path.join(dceprep_dir, subject_id, timepoint, f"dce/{subject_id}_{timepoint}_desc-AIF_T1map.nii.gz")
                if os.path.exists(dce) and os.path.exists(aif):
                    # load files
                    dce_img = nib.load(dce)
                    aif_img = nib.load(aif)

                    # get data from file
                    aif = aif_img.get_fdata()
                    dce = dce_img.get_fdata()

                    # binarize aif
                    aif = aif > 400

                    # get curve from masked dce
                    aif = aif.reshape(aif.shape[0], aif.shape[1], aif.shape[2], 1)
                    roi_ = dce * aif
                    num = np.sum(roi_, axis = (0, 1, 2), keepdims=False)
                    den = np.sum(aif, axis = (0, 1, 2), keepdims=False)

                    # normalize to baseline
                    intensities = num/(den+1e-8)
                    intensities = np.asarray(intensities)
                    intensities = intensities/intensities[0]
                    if intensities[0] != 1:
                        print("error")
                    # if intensities[1] < 3 and intensities[2] < 3:
                    #     print(file + " has a weak AIF curve with " + str(intensities[1]) + " and " + str(intensities[2]))
                    # if intensities[2] > intensities[1] or intensities[3] > intensities[2]+.5:
                    #     print(file + " has a delayed injection with " + str(intensities[1]) + " and " + str(intensities[2]) + " and " + str(intensities[3]))
                    # if any(intensities[10:30] < 2):
                    #     print(subject_id, timepoint, "has an intensity < 2")
                    # line up curve peaks
                    max_index = np.argmax(intensities)
                    # intensities = np.roll(intensities, -max_index+2)
                    if intensities.shape[0] < 40:
                        mean_last_7 = np.mean(intensities[-7:])
                        intensities = np.pad(intensities, (0, 40-intensities.shape[0]), 'constant', constant_values=(mean_last_7))
                    aif_curves.append(intensities[0:40])
                    intensities = np.roll(intensities, -max_index)
                    if intensities.shape[0] == 64:
                        # make last five values 0 then roll back
                        intensities[-5:] = 1
                        intensities = np.roll(intensities, 5)
                        if not np.isnan(intensities).any():
                            popAIF_curves.append(intensities)
                else:
                    print("DCE or AIF file does not exist for", subject_id, timepoint)
                    return
            except Exception as e:
                print("Error reading DCE or AIF for", subject_id, timepoint)
                print(e)
                return

            # if use manual AIF and file exists, mark as manual
            manual_aif_path = os.path.join(dceprep_dir, subject_id, timepoint, f"dce/{subject_id}_{timepoint}_desc-AIF_mask.nii.gz")
            if use_manual_aif and os.path.isfile(manual_aif_path):
                manual_aif_status = "MANUAL"
            elif not use_manual_aif and os.path.isfile(manual_aif_path):
                manual_aif_status = "OMITTED"
            else:
                manual_aif_status = "AUTO"
            # get fields we want from json
            json_file = os.path.join(dir, "../rawdata", subject_id, timepoint, f"dce/{subject_id}_{timepoint}_DCE.json")
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    manufacturer = data.get("Manufacturer", "json field error")
                    field_strength = data.get("MagneticFieldStrength", "json field error")
                    machine = data.get("ManufacturersModelName", "json field error")
                    institution = data.get("InstitutionName", "json field error")
                    date = data.get("AcquisitionDateTime", "json field error").split("T")[0]
                    if date != "json field error":
                        date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%m/%d/%Y")
                        date = datetime.datetime.strptime(date, "%m/%d/%Y")
                    sex = data.get("PatientSex", "json field error")
                    age = data.get("PatientAge", "json field error")
                    if "ReceiveCoilName" in data:
                        coil = data.get("ReceiveCoilName", "json field error")
                    else:
                        coil = data.get("CoilString", "json field error")
                    scan_options = data.get("ScanOptions", "json field error")
                    TE = data.get("EchoTime", "json field error")
                    # flip_angle = data.get("FlipAngle", "json field error")
                    # if "RepetitionTimeExcitation" in data:
                    #     # TR = data.get("RepetitionTimeExcitation", "json field error")
                    #     time_resolution = data.get("RepetitionTime", "json field error")
                    # else:
                    #     # TR = data.get("RepetitionTime", "json field error")
                    #     time_resolution = "not in header"
            except Exception as e:
                print("Error reading " + json_file)
                print(e)
                manufacturer = field_strength = machine = institution = date = sex = age = coil = scan_options = TE = flip_angle = TR = time_resolution = "json read error"

            if not missing:
                # read wm and gm data from html file
                filename = os.path.join(dceprep_dir, subject_id, timepoint, f"reports/{subject_id}_{timepoint}_desc-casereport.html")
                if os.path.exists(filename):
                    try:
                        with open(filename, "r") as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines):
                                if "T1 wm median:" in line:
                                    T1_wm_median = float(line.split(":")[-1].strip()[:-5])
                                if "T1 gm median:" in line:
                                    T1_gm_median = float(line.split(":")[-1].strip()[:-5])
                                if "Blood T1: " in line:
                                    T1_blood = float(line.split(":")[-1].strip()[:-6])
                                if "Median wm Ktrans" in line:
                                    Ktrans_wm_median = float(line.split()[-1][:-5])
                                if "Median gm Ktrans" in line:
                                    Ktrans_gm_median = float(line.split()[-1][:-5])
                                if "AIFitness" in line:
                                    AIFitness = line.split(":")[-1].strip()[:-4]
                                    AIFitness = float(AIFitness)
                                    AIFitness = round(AIFitness, 4)
                                if Ktrans_wm_median > 5:
                                    if subject_id + "_" + timepoint not in Ktrans_wm_outliers:
                                        Ktrans_wm_outliers.append(subject_id + "_" + timepoint)
                                if Ktrans_gm_median > 5:
                                    if subject_id + "_" + timepoint not in Ktrans_gm_outliers:
                                        Ktrans_gm_outliers.append(subject_id + "_" + timepoint)
                    except Exception as e:
                        print("Error reading " + filename)
                        print(e)
                        T1_wm_median = T1_gm_median = T1_blood = Ktrans_wm_median = Ktrans_gm_median = AIFitness = -1
                else:
                    print(f"{filename} does not exist")
                    T1_wm_median = T1_gm_median = T1_blood = Ktrans_wm_median = Ktrans_gm_median = AIFitness = -1

                A_log = os.path.join(dceprep_dir, subject_id, timepoint, "dce/A_dceR1info.log")
                try:
                    with open(A_log, 'r') as f:
                        for line in f:
                            if "User selected TR (ms):" in line:
                                TR = next(f).strip()
                                TR = float(TR)
                            if "User selected FA (degrees):" in line:
                                flip_angle = next(f).strip()
                                flip_angle = float(flip_angle)
                            if "time points = " in line:
                                n_reps = line.split(" ")[-1]
                                n_reps = int(n_reps)
                except Exception as e:
                    print("Error reading " + A_log)
                    print(e)
                    TR = -1
                    flip_angle = -1

                # read lines after "AIF mmol:"
                aif_mmol = []
                B_log = os.path.join(dceprep_dir, subject_id, timepoint, "dce/B_dcefitted_R1info.log")
                B_imported_log = os.path.join(dceprep_dir, subject_id, timepoint, "dce/B_dceimported_R1info.log")
                try:
                    if os.path.isfile(B_log):
                        with open(B_log, 'r') as f:
                            fitted_done = False
                            for line in f:
                                if "User selected time resolution (sec)" in line:
                                    # take next line as time resolution
                                    time_resolution = next(f).strip()
                                    time_resolution = float(time_resolution)
                                if "AIF mmol:" in line:
                                    aif_mmol = f.readlines()
                                    # find index of line after last numbers ("MAT results saved to: \n")
                                    try:
                                        lastline = aif_mmol.index("MAT results saved to: \n")
                                    except ValueError:
                                        lastline = aif_mmol.index("Finished B\n")
                                    aif_mmol = aif_mmol[:lastline-1]
                                    # remove \n and \t
                                    aif_mmol = [i[2:-2] for i in aif_mmol]
                                    # split each item into list
                                    aif_mmol = [i.split() for i in aif_mmol]
                                    # unite all lists into one
                                    aif_mmol = [item for sublist in aif_mmol for item in sublist]
                                    # convert to float
                                    aif_mmol = [float(i) for i in aif_mmol]
                                    # take last 33% of aif
                                    aif_mmol = aif_mmol[int(len(aif_mmol) * 0.66):]
                                    # convert to numpy array
                                    aif_mmol = np.array(aif_mmol)
                                    # take mean
                                    aif_mmol = np.mean(aif_mmol)
                                if "Adjusted R^2 of AIF fit = " in line and not fitted_done:
                                    aif_fitted_r2 = line.split()[-1]
                                    aif_fitted_r2 = float(aif_fitted_r2)
                                    fitted_done = True
                    elif os.path.isfile(B_imported_log):
                        with open(B_imported_log, 'r') as f:
                            for line in f:
                                if "User selected time resolution (sec)" in line:
                                    # take next line as time resolution
                                    time_resolution = next(f).strip()
                                    time_resolution = float(time_resolution)
                                if "AIF mmol:" in line:
                                    aif_mmol = f.readlines()
                                    # find index of line after last numbers ("MAT results saved to: \n")
                                    try:
                                        lastline = aif_mmol.index("MAT results saved to: \n")
                                    except ValueError:
                                        lastline = aif_mmol.index("Finished B\n")
                                    aif_mmol = aif_mmol[:lastline-1]
                                    # remove \n and \t
                                    aif_mmol = [i[2:-2] for i in aif_mmol]
                                    # split each item into list
                                    aif_mmol = [i.split() for i in aif_mmol]
                                    # unite all lists into one
                                    aif_mmol = [item for sublist in aif_mmol for item in sublist]
                                    # convert to float
                                    aif_mmol = [float(i) for i in aif_mmol]
                                    # take last 33% of aif
                                    aif_mmol = aif_mmol[int(len(aif_mmol) * 0.66):]
                                    # convert to numpy array
                                    aif_mmol = np.array(aif_mmol)
                                    # take mean
                                    aif_mmol = np.mean(aif_mmol)
                except Exception as e:
                    print("Error reading " + B_log)
                    print(e)
                    aif_mmol = -1
                    aif_fitted_r2 = -1
                # get max_disp from {prefix}_desc-hmcmaxdisp.txt
                max_disp_path = os.path.join(dceprep_dir, subject_id, timepoint, f"dce/{subject_id}_{timepoint}_desc-hmc_maxdisp.txt")
                if os.path.exists(max_disp_path):
                    try:
                        with open(max_disp_path, 'r') as f:
                            for line in f:
                                if "Max displacement" in line:
                                    max_disp = line.split(":")[-1].strip()
                                    max_disp = max_disp.split("mm")[0]
                                    max_disp = float(max_disp)
                                    break
                    except Exception as e:
                        print("Error reading " + max_disp_path)
                        print(e)
                        max_disp = -1
                else:
                    print(f"{max_disp_path} does not exist")
                    max_disp = -1
            else:
                print(f"Skipping stats for {subject_id} {timepoint} due to missing rawdata")
                return
            # read ktrans map
            try:
                ktrans_map = os.path.join(dceprep_dir, subject_id, timepoint, f"dce/{subject_id}_{timepoint}_Ktrans.nii")
                ktrans_map = nib.load(ktrans_map)
                ktrans_map = ktrans_map.get_fdata()
            except:
                print("Error reading " + ktrans_map)
                wmparc_failed = True
                stats_failed = True
                return

            # read Vp map
            try:
                Vp_map = os.path.join(dceprep_dir, subject_id, timepoint, f"dce/{subject_id}_{timepoint}_Vp.nii")
                Vp_map = nib.load(Vp_map)
                Vp_map = Vp_map.get_fdata()
            except:
                print("Error reading " + Vp_map)
                stats_failed = True
                return
            # Numbers are locations of regions in freesurfer wmparc.mgz
            regions = {
                "HIPPO": (17, 53),
                "PHG": (1016, 2016),
                "PUTAMEN": (12, 51),
                "PALLIDUM": (13, 52),
                "THALAMUS": (10, 49),
                "CAUDATE": (11, 50),
                "AMYGDALA": (18, 54),
                "ENTORHINAL_CORTEX": (1006, 2006),
                "FUSIFORM_GYRUS_CORTEX": (1007, 2007),
                "FUSIFORM_GYRUS_WM": (3007, 4007),
                "INSULA_WM": (3035, 4035),
                "SUPERIOR_TEMPORAL_CORTEX": (1030, 2030),
                "INFERIOR_TEMPORAL_CORTEX": (1009, 2009),
                "POSTERIOR_CINGULATE_CORTEX": (1023, 2023)
            }

            # atlas file is where this script is located
            # atlas = os.path.join(os.path.dirname(os.path.realpath(__file__)), "BN_Atlas_246_1mm.nii.gz")
            # atlas = nib.load(atlas)
            # atlas = atlas.get_fdata()
            # atlas = ktrans_map_hippo
            # atlas = atlas[:,110,:]
            error = ""
            try:
                prefix = f"{subject_id}_{timepoint}"
                wmparc_path = os.path.join(dceprep_dir, subject_id, timepoint, f"anat/{prefix}_space-DCEref_desc-wmparc.nii.gz")
                if os.path.isfile(wmparc_path):
                    wmparc = nib.load(wmparc_path)
                    wmparc = wmparc.get_fdata()
                else:
                    print(f"{wmparc_path} does not exist")
                    error = "anat/wmparc does not exist"
                    wmparc_failed = True
                    stats_failed = True
                # read stats from tsv
                freesurfer_path = os.path.join(dir, 'freesurfer', subject_id, timepoint, "stats")
                if os.path.isfile(os.path.join(freesurfer_path, "wmparc.stats")) and os.path.isfile(os.path.join(freesurfer_path, "aseg.stats")) and os.path.isfile(os.path.join(freesurfer_path, "lh.aparc.stats")) and os.path.isfile(os.path.join(freesurfer_path, "rh.aparc.stats")):
                    wmparc_stats = os.path.join(freesurfer_path, "wmparc.stats")
                    aseg_stats = os.path.join(freesurfer_path, "aseg.stats")
                    lh_aparc_stats = os.path.join(freesurfer_path, "lh.aparc.stats")
                    rh_aparc_stats = os.path.join(freesurfer_path, "rh.aparc.stats")
                    # fastsurfer = False
                # elif os.path.isfile(os.path.join(freesurfer_path, "wmparc.DKTatlas.mapped.stats")):
                #     # fastsurfer outputs
                #     wmparc_stats = os.path.join(freesurfer_path, "wmparc.DKTatlas.mapped.stats")
                #     aseg_stats = os.path.join(freesurfer_path, "aseg.stats")
                #     lh_aparc_stats = os.path.join(freesurfer_path, "lh.aparc.DKTatlas.mapped.stats")
                #     rh_aparc_stats = os.path.join(freesurfer_path, "rh.aparc.DKTatlas.mapped.stats")
                #     fastsurfer = True
                else:
                    print("wmparc stats do not exist for", prefix)
                    if error == "":
                        error = "stats files are missing"
                    wmparc_failed = True
                    stats_failed = True
                    # fastsurfer = False

            except Exception as e:
                print("Error reading freesurfer stats for", subject_id, timepoint)
                print(e)
                error = "stats error"
                wmparc_failed = True
                stats_failed = True
            if not stats_failed:
                with open(wmparc_stats, 'r') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if line.startswith("# ColHeaders"):
                            break
                    lines = lines[i:]
                    # remove # from beginning of each line
                    lines_split = [line.replace('#','').strip().split() for line in lines]

                    df_wmparc = pd.DataFrame(lines_split)
                    # Convert only numeric columns (skip first column and header row)
                    # First, set column names from the first row (shifted)
                    df_wmparc.columns = df_wmparc.iloc[0].shift(-1)
                    df_wmparc = df_wmparc.drop(df_wmparc.index[0])
                    # Identify numeric columns (skip 'StructName')
                    numeric_cols = [col for col in df_wmparc.columns if col != 'StructName']
                    df_wmparc[numeric_cols] = df_wmparc[numeric_cols].apply(pd.to_numeric)
                    df_wmparc = df_wmparc.set_index(df_wmparc.iloc[:, 0])
                    # drop first column
                    df_wmparc = df_wmparc.drop(df_wmparc.columns[0], axis=1)
                
                # fraudsurfer thalamus name varies
                right_thalamus = ''
                left_thalamus = ''
                with open(aseg_stats, 'r') as f:
                    # find line starting with # ColHeaders, skip up to that line
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if line.startswith("# ColHeaders"):
                            break
                    lines = lines[i:]
                    # remove # from beginning of each line
                    lines_split = [line.replace('#','').strip().split() for line in lines]

                    # find name of thalamus column labels
                    left_thalamus = [line for line in lines if 'Left-Thalamus' in line]
                    # split thalamus line and take element with 'Thalamus' in it
                    left_thalamus = left_thalamus[0].split()
                    left_thalamus = [col for col in left_thalamus if 'Left-Thalamus' in col][0]
                    # left_thalamus = left_thalamus.split('-')[-1]

                    right_thalamus = [line for line in lines if 'Right-Thalamus' in line]
                    right_thalamus = right_thalamus[0].split()
                    right_thalamus = [col for col in right_thalamus if 'Right-Thalamus' in col][0]
                    # right_thalamus = right_thalamus.split('-')[-1]

                    df_aseg = pd.DataFrame(lines_split)
                    # Set column names from the first row (shifted)
                    df_aseg.columns = df_aseg.iloc[0].shift(-1)
                    df_aseg = df_aseg.drop(df_aseg.index[0])
                    # Identify numeric columns (skip 'StructName')
                    numeric_cols = [col for col in df_aseg.columns if col != 'StructName']
                    df_aseg[numeric_cols] = df_aseg[numeric_cols].apply(pd.to_numeric)
                    # df_aseg = df_aseg.set_index(df_aseg.iloc[:, 0])
                    # drop first column
                    df_aseg = df_aseg.drop(df_aseg.columns[0], axis=1)

                with open(lh_aparc_stats, 'r') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if line.startswith("# ColHeaders"):
                            break
                    lines = lines[i:]
                    # remove # from beginning of each line
                    lines_split = [line.replace('#','').strip().split() for line in lines]

                    df_lh_aparc = pd.DataFrame(lines_split)
                    # Shift column names left by 1 to remove 'ColHeaders' and align 'StructName'
                    df_lh_aparc.columns = df_lh_aparc.iloc[0].shift(-1)
                    df_lh_aparc = df_lh_aparc.drop(df_lh_aparc.index[0])
                    # Identify numeric columns (skip 'StructName')
                    numeric_cols = [col for col in df_lh_aparc.columns if col != 'StructName']
                    df_lh_aparc[numeric_cols] = df_lh_aparc[numeric_cols].apply(pd.to_numeric)
                    # df_lh_aparc = df_lh_aparc.set_index(df_lh_aparc.iloc[:, 0])
                
                with open(rh_aparc_stats, 'r') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if line.startswith("# ColHeaders"):
                            break
                    lines = lines[i:]
                    # remove # from beginning of each line
                    lines_split = [line.replace('#','').strip().split() for line in lines]

                    df_rh_aparc = pd.DataFrame(lines_split)
                    # Shift column names left by 1 to remove 'ColHeaders' and align 'StructName'
                    df_rh_aparc.columns = df_rh_aparc.iloc[0].shift(-1)
                    df_rh_aparc = df_rh_aparc.drop(df_rh_aparc.index[0])
                    # Identify numeric columns (skip 'StructName')
                    numeric_cols = [col for col in df_rh_aparc.columns if col != 'StructName']
                    df_rh_aparc[numeric_cols] = df_rh_aparc[numeric_cols].apply(pd.to_numeric)
                    # df_rh_aparc = df_rh_aparc.set_index(df_rh_aparc.iloc[:, 0])
                # assign regional volumes to variables
                hippo_vol = float(df_aseg.loc[df_aseg['StructName'] == 'Left-Hippocampus', 'Volume_mm3'].values[0]) + float(df_aseg.loc[df_aseg['StructName'] == 'Right-Hippocampus', 'Volume_mm3'].values[0])
                phg_vol = float(df_wmparc.loc[df_wmparc['StructName'] == 'wm-lh-parahippocampal', 'Volume_mm3'].values[0]) + float(df_wmparc.loc[df_wmparc['StructName'] == 'wm-rh-parahippocampal', 'Volume_mm3'].values[0])
                putamen_vol = float(df_aseg.loc[df_aseg['StructName'] == 'Left-Putamen', 'Volume_mm3'].values[0]) + float(df_aseg.loc[df_aseg['StructName'] == 'Right-Putamen', 'Volume_mm3'].values[0])
                pallidum_vol = float(df_aseg.loc[df_aseg['StructName'] == 'Left-Pallidum', 'Volume_mm3'].values[0]) + float(df_aseg.loc[df_aseg['StructName'] == 'Right-Pallidum', 'Volume_mm3'].values[0])
                thalamus_vol = float(df_aseg.loc[df_aseg['StructName'] == left_thalamus, 'Volume_mm3'].values[0]) + float(df_aseg.loc[df_aseg['StructName'] == right_thalamus, 'Volume_mm3'].values[0])
                caudate_vol = float(df_aseg.loc[df_aseg['StructName'] == 'Left-Caudate', 'Volume_mm3'].values[0]) + float(df_aseg.loc[df_aseg['StructName'] == 'Right-Caudate', 'Volume_mm3'].values[0])
                amygdala_vol = float(df_aseg.loc[df_aseg['StructName'] == 'Left-Amygdala', 'Volume_mm3'].values[0]) + float(df_aseg.loc[df_aseg['StructName'] == 'Right-Amygdala', 'Volume_mm3'].values[0])
                entorhinal_cortex_vol = float(df_lh_aparc.loc[df_lh_aparc['StructName'] == 'entorhinal', 'GrayVol'].values[0]) + float(df_rh_aparc.loc[df_rh_aparc['StructName'] == 'entorhinal', 'GrayVol'].values[0])
                fusiform_gyrus_cortex_vol = float(df_lh_aparc.loc[df_lh_aparc['StructName'] == 'fusiform', 'GrayVol'].values[0]) + float(df_rh_aparc.loc[df_rh_aparc['StructName'] == 'fusiform', 'GrayVol'].values[0])
                fusiform_gyrus_wm_vol = float(df_wmparc.loc[df_wmparc['StructName'] == 'wm-lh-fusiform', 'Volume_mm3'].values[0]) + float(df_wmparc.loc[df_wmparc['StructName'] == 'wm-rh-fusiform', 'Volume_mm3'].values[0])
                insula_wm_vol = float(df_wmparc.loc[df_wmparc['StructName'] == 'wm-lh-insula', 'Volume_mm3'].values[0]) + float(df_wmparc.loc[df_wmparc['StructName'] == 'wm-rh-insula', 'Volume_mm3'].values[0])
                superior_temporal_cortex_vol = float(df_lh_aparc.loc[df_lh_aparc['StructName'] == 'superiortemporal', 'GrayVol'].values[0]) + float(df_rh_aparc.loc[df_rh_aparc['StructName'] == 'superiortemporal', 'GrayVol'].values[0])
                inferior_temporal_cortex_vol = float(df_lh_aparc.loc[df_lh_aparc['StructName'] == 'inferiortemporal', 'GrayVol'].values[0]) + float(df_rh_aparc.loc[df_rh_aparc['StructName'] == 'inferiortemporal', 'GrayVol'].values[0])
                posterior_cingulate_cortex_vol = float(df_lh_aparc.loc[df_lh_aparc['StructName'] == 'posteriorcingulate', 'GrayVol'].values[0]) + float(df_rh_aparc.loc[df_rh_aparc['StructName'] == 'posteriorcingulate', 'GrayVol'].values[0])
                medial_temporal_cortex_vol = hippo_vol + phg_vol + entorhinal_cortex_vol
                # get all cortical thickness values from left and right aparc
                cortical_thickness_lh = df_lh_aparc[['StructName', 'NumVert', 'ThickAvg', 'ThickStd']].values.tolist()
                cortical_thickness_rh = df_rh_aparc[['StructName', 'NumVert', 'ThickAvg', 'ThickStd']].values.tolist()
                # for each region, get whole-brain mean cortical thickness, weighted by number of vertices in region
                cortical_thickness = {}
                for lh, rh in zip(cortical_thickness_lh, cortical_thickness_rh):
                    # print(lh, rh)
                    if lh[0] == rh[0] and lh[0] not in cortical_thickness:
                        region = lh[0]
                        num_vert = int(lh[1]) + int(rh[1])
                        thickness = (float(lh[1])*float(lh[2]) + float(rh[1])*float(rh[2])) / num_vert
                        thickness_std = np.sqrt((float(lh[1]) * float(lh[3])**2 + float(rh[1]) * float(rh[3])**2) / num_vert)
                        cortical_thickness[region] = {
                            "thickness": thickness,
                            "thickness_std": thickness_std,
                        }
                bankssts_thickness_avg = cortical_thickness.get('bankssts', {}).get('thickness', -1)
                bankssts_thickness_std = cortical_thickness.get('bankssts', {}).get('thickness_std', -1)
                caudalanteriorcingulate_thickness_avg = cortical_thickness.get('caudalanteriorcingulate', {}).get('thickness', -1)
                caudalanteriorcingulate_thickness_std = cortical_thickness.get('caudalanteriorcingulate', {}).get('thickness_std', -1)
                caudalmiddlefrontal_thickness_avg = cortical_thickness.get('caudalmiddlefrontal', {}).get('thickness', -1)
                caudalmiddlefrontal_thickness_std = cortical_thickness.get('caudalmiddlefrontal', {}).get('thickness_std', -1)
                cuneus_thickness_avg = cortical_thickness.get('cuneus', {}).get('thickness', -1)
                cuneus_thickness_std = cortical_thickness.get('cuneus', {}).get('thickness_std', -1)
                entorhinal_thickness_avg = cortical_thickness.get('entorhinal', {}).get('thickness', -1)
                entorhinal_thickness_std = cortical_thickness.get('entorhinal', {}).get('thickness_std', -1)
                fusiform_thickness_avg = cortical_thickness.get('fusiform', {}).get('thickness', -1)
                fusiform_thickness_std = cortical_thickness.get('fusiform', {}).get('thickness_std', -1)
                inferiorparietal_thickness_avg = cortical_thickness.get('inferiorparietal', {}).get('thickness', -1)
                inferiorparietal_thickness_std = cortical_thickness.get('inferiorparietal', {}).get('thickness_std', -1)
                inferiortemporal_thickness_avg = cortical_thickness.get('inferiortemporal', {}).get('thickness', -1)
                inferiortemporal_thickness_std = cortical_thickness.get('inferiortemporal', {}).get('thickness_std', -1)
                isthmuscingulate_thickness_avg = cortical_thickness.get('isthmuscingulate', {}).get('thickness', -1)
                isthmuscingulate_thickness_std = cortical_thickness.get('isthmuscingulate', {}).get('thickness_std', -1)
                lateraloccipital_thickness_avg = cortical_thickness.get('lateraloccipital', {}).get('thickness', -1)
                lateraloccipital_thickness_std = cortical_thickness.get('lateraloccipital', {}).get('thickness_std', -1)
                lateralorbitofrontal_thickness_avg = cortical_thickness.get('lateralorbitofrontal', {}).get('thickness', -1)
                lateralorbitofrontal_thickness_std = cortical_thickness.get('lateralorbitofrontal', {}).get('thickness_std', -1)
                lingual_thickness_avg = cortical_thickness.get('lingual', {}).get('thickness', -1)
                lingual_thickness_std = cortical_thickness.get('lingual', {}).get('thickness_std', -1)
                medialorbitofrontal_thickness_avg = cortical_thickness.get('medialorbitofrontal', {}).get('thickness', -1)
                medialorbitofrontal_thickness_std = cortical_thickness.get('medialorbitofrontal', {}).get('thickness_std', -1)
                middletemporal_thickness_avg = cortical_thickness.get('middletemporal', {}).get('thickness', -1)
                middletemporal_thickness_std = cortical_thickness.get('middletemporal', {}).get('thickness_std', -1)
                parahippocampal_thickness_avg = cortical_thickness.get('parahippocampal', {}).get('thickness', -1)
                parahippocampal_thickness_std = cortical_thickness.get('parahippocampal', {}).get('thickness_std', -1)
                paracentral_thickness_avg = cortical_thickness.get('paracentral', {}).get('thickness', -1)
                paracentral_thickness_std = cortical_thickness.get('paracentral', {}).get('thickness_std', -1)
                parsopercularis_thickness_avg = cortical_thickness.get('parsopercularis', {}).get('thickness', -1)
                parsopercularis_thickness_std = cortical_thickness.get('parsopercularis', {}).get('thickness_std', -1)
                parsorbitalis_thickness_avg = cortical_thickness.get('parsorbitalis', {}).get('thickness', -1)
                parsorbitalis_thickness_std = cortical_thickness.get('parsorbitalis', {}).get('thickness_std', -1)
                parstriangularis_thickness_avg = cortical_thickness.get('parstriangularis', {}).get('thickness', -1)
                parstriangularis_thickness_std = cortical_thickness.get('parstriangularis', {}).get('thickness_std', -1)
                pericalcarine_thickness_avg = cortical_thickness.get('pericalcarine', {}).get('thickness', -1)
                pericalcarine_thickness_std = cortical_thickness.get('pericalcarine', {}).get('thickness_std', -1)
                postcentral_thickness_avg = cortical_thickness.get('postcentral', {}).get('thickness', -1)
                postcentral_thickness_std = cortical_thickness.get('postcentral', {}).get('thickness_std', -1)
                posteriorcingulate_thickness_avg = cortical_thickness.get('posteriorcingulate', {}).get('thickness', -1)
                posteriorcingulate_thickness_std = cortical_thickness.get('posteriorcingulate', {}).get('thickness_std', -1)
                precentral_thickness_avg = cortical_thickness.get('precentral', {}).get('thickness', -1)
                precentral_thickness_std = cortical_thickness.get('precentral', {}).get('thickness_std', -1)
                precuneus_thickness_avg = cortical_thickness.get('precuneus', {}).get('thickness', -1)
                precuneus_thickness_std = cortical_thickness.get('precuneus', {}).get('thickness_std', -1)
                rostralanteriorcingulate_thickness_avg = cortical_thickness.get('rostralanteriorcingulate', {}).get('thickness', -1)
                rostralanteriorcingulate_thickness_std = cortical_thickness.get('rostralanteriorcingulate', {}).get('thickness_std', -1)
                rostralmiddlefrontal_thickness_avg = cortical_thickness.get('rostralmiddlefrontal', {}).get('thickness', -1)
                rostralmiddlefrontal_thickness_std = cortical_thickness.get('rostralmiddlefrontal', {}).get('thickness_std', -1)
                superiorfrontal_thickness_avg = cortical_thickness.get('superiorfrontal', {}).get('thickness', -1)
                superiorfrontal_thickness_std = cortical_thickness.get('superiorfrontal', {}).get('thickness_std', -1)
                superiorparietal_thickness_avg = cortical_thickness.get('superiorparietal', {}).get('thickness', -1)
                superiorparietal_thickness_std = cortical_thickness.get('superiorparietal', {}).get('thickness_std', -1)
                superiortemporal_thickness_avg = cortical_thickness.get('superiortemporal', {}).get('thickness', -1)
                superiortemporal_thickness_std = cortical_thickness.get('superiortemporal', {}).get('thickness_std', -1)
                inferiortemporal_thickness_avg = cortical_thickness.get('inferiortemporal', {}).get('thickness', -1)
                inferiortemporal_thickness_std = cortical_thickness.get('inferiortemporal', {}).get('thickness_std', -1)
                supramarginal_thickness_avg = cortical_thickness.get('supramarginal', {}).get('thickness', -1)
                supramarginal_thickness_std = cortical_thickness.get('supramarginal', {}).get('thickness_std', -1)
                frontalpole_thickness_avg = cortical_thickness.get('frontalpole', {}).get('thickness', -1)
                frontalpole_thickness_std = cortical_thickness.get('frontalpole', {}).get('thickness_std', -1)
                temporalpole_thickness_avg = cortical_thickness.get('temporalpole', {}).get('thickness', -1)
                temporalpole_thickness_std = cortical_thickness.get('temporalpole', {}).get('thickness_std', -1)
                transversetemporal_thickness_avg = cortical_thickness.get('transversetemporal', {}).get('thickness', -1)
                transversetemporal_thickness_std = cortical_thickness.get('transversetemporal', {}).get('thickness_std', -1)
                insula_thickness_avg = cortical_thickness.get('insula', {}).get('thickness', -1)
                insula_thickness_std = cortical_thickness.get('insula', {}).get('thickness_std', -1)

            if not wmparc_failed:
                HIPPO_INDICES = np.where(((wmparc == regions["HIPPO"][0]) | (wmparc == regions["HIPPO"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                PHG_INDICES = np.where(((wmparc == regions["PHG"][0]) | (wmparc == regions["PHG"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                PUTAMEN_INDICES = np.where(((wmparc == regions["PUTAMEN"][0]) | (wmparc == regions["PUTAMEN"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                PALLIDUM_INDICES = np.where(((wmparc == regions["PALLIDUM"][0]) | (wmparc == regions["PALLIDUM"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                THALAMUS_INDICES = np.where(((wmparc == regions["THALAMUS"][0]) | (wmparc == regions["THALAMUS"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                CAUDATE_INDICES = np.where(((wmparc == regions["CAUDATE"][0]) | (wmparc == regions["CAUDATE"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                AMYGDALA_INDICES = np.where(((wmparc == regions["AMYGDALA"][0]) | (wmparc == regions["AMYGDALA"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                ENTORHINAL_CORTEX_INDICES = np.where(((wmparc == regions["ENTORHINAL_CORTEX"][0]) | (wmparc == regions["ENTORHINAL_CORTEX"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                FUSIFORM_GYRUS_CORTEX_INDICES = np.where(((wmparc == regions["FUSIFORM_GYRUS_CORTEX"][0]) | (wmparc == regions["FUSIFORM_GYRUS_CORTEX"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                FUSIFORM_GYRUS_WM_INDICES = np.where(((wmparc == regions["FUSIFORM_GYRUS_WM"][0]) | (wmparc == regions["FUSIFORM_GYRUS_WM"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                INSULA_WM_INDICES = np.where(((wmparc == regions["INSULA_WM"][0]) | (wmparc == regions["INSULA_WM"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                SUPERIOR_TEMPORAL_CORTEX_INDICES = np.where(((wmparc == regions["SUPERIOR_TEMPORAL_CORTEX"][0]) | (wmparc == regions["SUPERIOR_TEMPORAL_CORTEX"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                INFERIOR_TEMPORAL_CORTEX_INDICES = np.where(((wmparc == regions["INFERIOR_TEMPORAL_CORTEX"][0]) | (wmparc == regions["INFERIOR_TEMPORAL_CORTEX"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                POSTERIOR_CINGULATE_CORTEX_INDICES = np.where(((wmparc == regions["POSTERIOR_CINGULATE_CORTEX"][0]) | (wmparc == regions["POSTERIOR_CINGULATE_CORTEX"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
                MEDIAL_TEMPORAL_CORTEX_INDICES = np.where(((wmparc == regions["HIPPO"][0]) | (wmparc == regions["HIPPO"][1]) | (wmparc == regions["PHG"][0]) | (wmparc == regions["PHG"][1]) | (wmparc == regions["ENTORHINAL_CORTEX"][0]) | (wmparc == regions["ENTORHINAL_CORTEX"][1])) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            
                Ktrans_Hippo = ktrans_map[HIPPO_INDICES]*1000
                Ktrans_PhG = ktrans_map[PHG_INDICES]*1000
                Ktrans_Putamen = ktrans_map[PUTAMEN_INDICES]*1000
                Ktrans_Pallidum = ktrans_map[PALLIDUM_INDICES]*1000
                Ktrans_Thalamus = ktrans_map[THALAMUS_INDICES]*1000
                Ktrans_Caudate = ktrans_map[CAUDATE_INDICES]*1000
                Ktrans_Amygdala = ktrans_map[AMYGDALA_INDICES]*1000
                Ktrans_Entorhinal_cortex = ktrans_map[ENTORHINAL_CORTEX_INDICES]*1000
                Ktrans_Fusiform_gyrus_cortex = ktrans_map[FUSIFORM_GYRUS_CORTEX_INDICES]*1000
                Ktrans_Fusiform_gyrus_WM = ktrans_map[FUSIFORM_GYRUS_WM_INDICES]*1000
                Ktrans_Insula_WM = ktrans_map[INSULA_WM_INDICES]*1000
                Ktrans_Superior_temporal_cortex = ktrans_map[SUPERIOR_TEMPORAL_CORTEX_INDICES]*1000
                Ktrans_Inferior_temporal_cortex = ktrans_map[INFERIOR_TEMPORAL_CORTEX_INDICES]*1000
                Ktrans_Posterior_cingulate_cortex = ktrans_map[POSTERIOR_CINGULATE_CORTEX_INDICES]*1000
                Ktrans_Medial_temporal_cortex = ktrans_map[MEDIAL_TEMPORAL_CORTEX_INDICES]*1000
                Vp_Hippo = Vp_map[HIPPO_INDICES]
                Vp_PhG = Vp_map[PHG_INDICES]
                Vp_Putamen = Vp_map[PUTAMEN_INDICES]
                Vp_Pallidum = Vp_map[PALLIDUM_INDICES]
                Vp_Thalamus = Vp_map[THALAMUS_INDICES]
                Vp_Caudate = Vp_map[CAUDATE_INDICES]
                Vp_Amygdala = Vp_map[AMYGDALA_INDICES]
                Vp_Entorhinal_cortex = Vp_map[ENTORHINAL_CORTEX_INDICES]
                Vp_Fusiform_gyrus_cortex = Vp_map[FUSIFORM_GYRUS_CORTEX_INDICES]
                Vp_Fusiform_gyrus_WM = Vp_map[FUSIFORM_GYRUS_WM_INDICES]
                Vp_Insula_WM = Vp_map[INSULA_WM_INDICES]
                Vp_Superior_temporal_cortex = Vp_map[SUPERIOR_TEMPORAL_CORTEX_INDICES]
                Vp_Inferior_temporal_cortex = Vp_map[INFERIOR_TEMPORAL_CORTEX_INDICES]
                Vp_Posterior_cingulate_cortex = Vp_map[POSTERIOR_CINGULATE_CORTEX_INDICES]
                Vp_Medial_temporal_cortex = Vp_map[MEDIAL_TEMPORAL_CORTEX_INDICES]
            
                Ktrans_Hippo_median = np.nanmedian(Ktrans_Hippo)
                Ktrans_PhG_median = np.nanmedian(Ktrans_PhG)
                Ktrans_Putamen_median = np.nanmedian(Ktrans_Putamen)
                Ktrans_Pallidum_median = np.nanmedian(Ktrans_Pallidum)
                Ktrans_Thalamus_median = np.nanmedian(Ktrans_Thalamus)
                Ktrans_Caudate_median = np.nanmedian(Ktrans_Caudate)
                Ktrans_Amygdala_median = np.nanmedian(Ktrans_Amygdala)
                Ktrans_Entorhinal_cortex_median = np.nanmedian(Ktrans_Entorhinal_cortex)
                Ktrans_Fusiform_gyrus_cortex_median = np.nanmedian(Ktrans_Fusiform_gyrus_cortex)
                Ktrans_Fusiform_gyrus_WM_median = np.nanmedian(Ktrans_Fusiform_gyrus_WM)
                Ktrans_Insula_WM_median = np.nanmedian(Ktrans_Insula_WM)
                Ktrans_Superior_temporal_cortex_median = np.nanmedian(Ktrans_Superior_temporal_cortex)
                Ktrans_Inferior_temporal_cortex_median = np.nanmedian(Ktrans_Inferior_temporal_cortex)
                Ktrans_Posterior_cingulate_cortex_median = np.nanmedian(Ktrans_Posterior_cingulate_cortex)
                Ktrans_Medial_temporal_cortex_median = np.nanmedian(Ktrans_Medial_temporal_cortex)
                Vp_Hippo_median = np.nanmedian(Vp_Hippo)
                Vp_PhG_median = np.nanmedian(Vp_PhG)
                Vp_Putamen_median = np.nanmedian(Vp_Putamen)
                Vp_Pallidum_median = np.nanmedian(Vp_Pallidum)
                Vp_Thalamus_median = np.nanmedian(Vp_Thalamus)
                Vp_Caudate_median = np.nanmedian(Vp_Caudate)
                Vp_Amygdala_median = np.nanmedian(Vp_Amygdala)
                Vp_Entorhinal_cortex_median = np.nanmedian(Vp_Entorhinal_cortex)
                Vp_Fusiform_gyrus_cortex_median = np.nanmedian(Vp_Fusiform_gyrus_cortex)
                Vp_Fusiform_gyrus_WM_median = np.nanmedian(Vp_Fusiform_gyrus_WM)
                Vp_Insula_WM_median = np.nanmedian(Vp_Insula_WM)
                Vp_Superior_temporal_cortex_median = np.nanmedian(Vp_Superior_temporal_cortex)
                Vp_Inferior_temporal_cortex_median = np.nanmedian(Vp_Inferior_temporal_cortex)
                Vp_Posterior_cingulate_cortex_median = np.nanmedian(Vp_Posterior_cingulate_cortex)
                Vp_Medial_temporal_cortex_median = np.nanmedian(Vp_Medial_temporal_cortex)
            
                if Ktrans_Hippo_median > 5:
                    if subject_id + "_" + timepoint not in whole_hippo_outliers:
                        whole_hippo_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_PhG_median > 5:
                    if subject_id + "_" + timepoint not in whole_phg_outliers:
                        whole_phg_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Putamen_median > 5:
                    if subject_id + "_" + timepoint not in whole_putamen_outliers:
                        whole_putamen_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Pallidum_median > 5:
                    if subject_id + "_" + timepoint not in whole_pallidum_outliers:
                        whole_pallidum_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Thalamus_median > 5:
                    if subject_id + "_" + timepoint not in whole_thalamus_outliers:
                        whole_thalamus_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Caudate_median > 5:
                    if subject_id + "_" + timepoint not in whole_caudate_outliers:
                        whole_caudate_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Amygdala_median > 5:
                    if subject_id + "_" + timepoint not in whole_amygdala_outliers:
                        whole_amygdala_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Entorhinal_cortex_median > 5:
                    if subject_id + "_" + timepoint not in whole_entorhinal_cortex_outliers:
                        whole_entorhinal_cortex_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Fusiform_gyrus_cortex_median > 5:
                    if subject_id + "_" + timepoint not in whole_fusiform_gyrus_cortex_outliers:
                        whole_fusiform_gyrus_cortex_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Fusiform_gyrus_WM_median > 5:
                    if subject_id + "_" + timepoint not in whole_fusiform_gyrus_WM_outliers:
                        whole_fusiform_gyrus_WM_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Insula_WM_median > 5:
                    if subject_id + "_" + timepoint not in whole_insula_WM_outliers:
                        whole_insula_WM_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Superior_temporal_cortex_median > 5:
                    if subject_id + "_" + timepoint not in whole_superior_temporal_cortex_outliers:
                        whole_superior_temporal_cortex_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Inferior_temporal_cortex_median > 5:
                    if subject_id + "_" + timepoint not in whole_inferior_temporal_cortex_outliers:
                        whole_inferior_temporal_cortex_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Posterior_cingulate_cortex_median > 5:
                    if subject_id + "_" + timepoint not in whole_posterior_cingulate_cortex_outliers:
                        whole_posterior_cingulate_cortex_outliers.append(subject_id + "_" + timepoint)
                if Ktrans_Medial_temporal_cortex_median > 5:
                    if subject_id + "_" + timepoint not in whole_medial_temporal_cortex_outliers:
                        whole_medial_temporal_cortex_outliers.append(subject_id + "_" + timepoint)

                # Calculate SNR from getting mean SI in DCE thalamus then stdev of the difference between the last 2 DCE measures
                DCE_img_path = os.path.join(dceprep_dir, subject_id, timepoint, f"dce/{subject_id}_{timepoint}_desc-bfcz_DCE.nii.gz")
                if os.path.exists(DCE_img_path):
                    try:
                        # DCE_img = nib.load(DCE_img_path)
                        # DCE_img = DCE_img.get_fdata()
                        SI_Thalamus_DCE = dce[THALAMUS_INDICES]

                        SI_Thalamus_DCE_mean = np.mean(SI_Thalamus_DCE)
                        SI_Thalamus_DCE_last = SI_Thalamus_DCE[:,-1]
                        SI_Thalamus_DCE_penultimate = SI_Thalamus_DCE[:,-2]
                        SI_Thalamus_DCE_last2_difference = SI_Thalamus_DCE_last - SI_Thalamus_DCE_penultimate
                        SI_Thalamus_DCE_noise_stdev = np.std(SI_Thalamus_DCE_last2_difference)
                        # calculate SNR
                        SNR = SI_Thalamus_DCE_mean / SI_Thalamus_DCE_noise_stdev
                    except Exception as e:
                        SNR = -1
                        print(f"Could not calculate SNR for {subject_id} {timepoint}: {e}")
                else:
                    SNR = -1
            
            entry = subject_id + "_" + timepoint
            # Common data for both success and fail
            case_data = {
                "AIFitness": AIFitness,
                "aif_mmol": aif_mmol,
                "aif_fitted_r2": aif_fitted_r2,
                "T1_wm_median": T1_wm_median,
                "T1_gm_median": T1_gm_median,
                "T1_blood": T1_blood,
                "Ktrans_wm_median": Ktrans_wm_median,
                "Ktrans_gm_median": Ktrans_gm_median,
                "max_disp": max_disp,
                "Manufacturer": manufacturer,
                "Field_strength": field_strength,
                "Machine": machine,
                "Institution": institution,
                "Date": date,
                "Sex": sex,
                "Age": age,
                "Coil": coil,
                "Scan_options": scan_options,
                "TE": TE,
                "Time_resolution": time_resolution,
                "Flip_angle": flip_angle,
                "TR": TR,
                "n_reps": n_reps,
                "Approximate SNR": SNR,
                "Ktrans_Hippo_median": Ktrans_Hippo_median,
                "Ktrans_PhG_median": Ktrans_PhG_median,
                "Ktrans_Putamen_median": Ktrans_Putamen_median,
                "Ktrans_Pallidum_median": Ktrans_Pallidum_median,
                "Ktrans_Thalamus_median": Ktrans_Thalamus_median,
                "Ktrans_Caudate_median": Ktrans_Caudate_median,
                "Ktrans_Amygdala_median": Ktrans_Amygdala_median,
                "Ktrans_Entorhinal_cortex_median": Ktrans_Entorhinal_cortex_median,
                "Ktrans_Fusiform_gyrus_cortex_median": Ktrans_Fusiform_gyrus_cortex_median,
                "Ktrans_Fusiform_gyrus_WM_median": Ktrans_Fusiform_gyrus_WM_median,
                "Ktrans_Insula_WM_median": Ktrans_Insula_WM_median,
                "Ktrans_Superior_temporal_cortex_median": Ktrans_Superior_temporal_cortex_median,
                "Ktrans_Inferior_temporal_cortex_median": Ktrans_Inferior_temporal_cortex_median,
                "Ktrans_Posterior_cingulate_cortex_median": Ktrans_Posterior_cingulate_cortex_median,
                "Ktrans_Medial_temporal_cortex_median": Ktrans_Medial_temporal_cortex_median,
                "Vp_Hippo_median": Vp_Hippo_median,
                "Vp_PhG_median": Vp_PhG_median,
                "Vp_Putamen_median": Vp_Putamen_median,
                "Vp_Pallidum_median": Vp_Pallidum_median,
                "Vp_Thalamus_median": Vp_Thalamus_median,
                "Vp_Caudate_median": Vp_Caudate_median,
                "Vp_Amygdala_median": Vp_Amygdala_median,
                "Vp_Entorhinal_cortex_median": Vp_Entorhinal_cortex_median,
                "Vp_Fusiform_gyrus_cortex_median": Vp_Fusiform_gyrus_cortex_median,
                "Vp_Fusiform_gyrus_WM_median": Vp_Fusiform_gyrus_WM_median,
                "Vp_Insula_WM_median": Vp_Insula_WM_median,
                "Vp_Superior_temporal_cortex_median": Vp_Superior_temporal_cortex_median,
                "Vp_Inferior_temporal_cortex_median": Vp_Inferior_temporal_cortex_median,
                "Vp_Posterior_cingulate_cortex_median": Vp_Posterior_cingulate_cortex_median,
                "Vp_Medial_temporal_cortex_median": Vp_Medial_temporal_cortex_median,
                "hippo_vol": hippo_vol,
                "phg_vol": phg_vol,
                "putamen_vol": putamen_vol,
                "pallidum_vol": pallidum_vol,
                "thalamus_vol": thalamus_vol,
                "caudate_vol": caudate_vol,
                "amygdala_vol": amygdala_vol,
                "entorhinal_cortex_vol": entorhinal_cortex_vol,
                "fusiform_gyrus_cortex_vol": fusiform_gyrus_cortex_vol,
                "fusiform_gyrus_wm_vol": fusiform_gyrus_wm_vol,
                "insula_wm_vol": insula_wm_vol,
                "superior_temporal_cortex_vol": superior_temporal_cortex_vol,
                "inferior_temporal_cortex_vol": inferior_temporal_cortex_vol,
                "posterior_cingulate_cortex_vol": posterior_cingulate_cortex_vol,
                "medial_temporal_cortex_vol": medial_temporal_cortex_vol,
                "manual_aif_status": manual_aif_status,
                "bankssts_thickness_avg": bankssts_thickness_avg,
                "bankssts_thickness_std": bankssts_thickness_std,
                "caudalanteriorcingulate_thickness_avg": caudalanteriorcingulate_thickness_avg,
                "caudalanteriorcingulate_thickness_std": caudalanteriorcingulate_thickness_std,
                "caudalmiddlefrontal_thickness_avg": caudalmiddlefrontal_thickness_avg,
                "caudalmiddlefrontal_thickness_std": caudalmiddlefrontal_thickness_std,
                "cuneus_thickness_avg": cuneus_thickness_avg,
                "cuneus_thickness_std": cuneus_thickness_std,
                "entorhinal_thickness_avg": entorhinal_thickness_avg,
                "entorhinal_thickness_std": entorhinal_thickness_std,
                "fusiform_thickness_avg": fusiform_thickness_avg,
                "fusiform_thickness_std": fusiform_thickness_std,
                "inferiorparietal_thickness_avg": inferiorparietal_thickness_avg,
                "inferiorparietal_thickness_std": inferiorparietal_thickness_std,
                "inferiortemporal_thickness_avg": inferiortemporal_thickness_avg,
                "inferiortemporal_thickness_std": inferiortemporal_thickness_std,
                "isthmuscingulate_thickness_avg": isthmuscingulate_thickness_avg,
                "isthmuscingulate_thickness_std": isthmuscingulate_thickness_std,
                "lateraloccipital_thickness_avg": lateraloccipital_thickness_avg,
                "lateraloccipital_thickness_std": lateraloccipital_thickness_std,
                "lateralorbitofrontal_thickness_avg": lateralorbitofrontal_thickness_avg,
                "lateralorbitofrontal_thickness_std": lateralorbitofrontal_thickness_std,
                "lingual_thickness_avg": lingual_thickness_avg,
                "lingual_thickness_std": lingual_thickness_std,
                "medialorbitofrontal_thickness_avg": medialorbitofrontal_thickness_avg,
                "medialorbitofrontal_thickness_std": medialorbitofrontal_thickness_std,
                "middletemporal_thickness_avg": middletemporal_thickness_avg,
                "middletemporal_thickness_std": middletemporal_thickness_std,
                "parahippocampal_thickness_avg": parahippocampal_thickness_avg,
                "parahippocampal_thickness_std": parahippocampal_thickness_std,
                "paracentral_thickness_avg": paracentral_thickness_avg,
                "paracentral_thickness_std": paracentral_thickness_std,
                "parsopercularis_thickness_avg": parsopercularis_thickness_avg,
                "parsopercularis_thickness_std": parsopercularis_thickness_std,
                "parsorbitalis_thickness_avg": parsorbitalis_thickness_avg,
                "parsorbitalis_thickness_std": parsorbitalis_thickness_std,
                "parstriangularis_thickness_avg": parstriangularis_thickness_avg,
                "parstriangularis_thickness_std": parstriangularis_thickness_std,
                "pericalcarine_thickness_avg": pericalcarine_thickness_avg,
                "pericalcarine_thickness_std": pericalcarine_thickness_std,
                "postcentral_thickness_avg": postcentral_thickness_avg,
                "postcentral_thickness_std": postcentral_thickness_std,
                "posteriorcingulate_thickness_avg": posteriorcingulate_thickness_avg,
                "posteriorcingulate_thickness_std": posteriorcingulate_thickness_std,
                "precentral_thickness_avg": precentral_thickness_avg,
                "precentral_thickness_std": precentral_thickness_std,
                "precuneus_thickness_avg": precuneus_thickness_avg,
                "precuneus_thickness_std": precuneus_thickness_std,
                "rostralanteriorcingulate_thickness_avg": rostralanteriorcingulate_thickness_avg,
                "rostralanteriorcingulate_thickness_std": rostralanteriorcingulate_thickness_std,
                "rostralmiddlefrontal_thickness_avg": rostralmiddlefrontal_thickness_avg,
                "rostralmiddlefrontal_thickness_std": rostralmiddlefrontal_thickness_std,
                "superiorfrontal_thickness_avg": superiorfrontal_thickness_avg,
                "superiorfrontal_thickness_std": superiorfrontal_thickness_std,
                "superiorparietal_thickness_avg": superiorparietal_thickness_avg,
                "superiorparietal_thickness_std": superiorparietal_thickness_std,
                "superiortemporal_thickness_avg": superiortemporal_thickness_avg,
                "superiortemporal_thickness_std": superiortemporal_thickness_std,
                "supramarginal_thickness_avg": supramarginal_thickness_avg,
                "supramarginal_thickness_std": supramarginal_thickness_std,
                "frontalpole_thickness_avg": frontalpole_thickness_avg,
                "frontalpole_thickness_std": frontalpole_thickness_std,
                "temporalpole_thickness_avg": temporalpole_thickness_avg,
                "temporalpole_thickness_std": temporalpole_thickness_std,
                "transversetemporal_thickness_avg": transversetemporal_thickness_avg,
                "transversetemporal_thickness_std": transversetemporal_thickness_std,
                "insula_thickness_avg": insula_thickness_avg,
                "insula_thickness_std": insula_thickness_std
            }

            if wmparc_failed is False:
                # case_data["fastsurfer"] = fastsurfer
                successful_timepoints.append(entry.replace("_", "/"))
                population_data[entry] = case_data
            else:
                case_data["Reason"] = error
                population_data_failed[entry] = case_data

# time
# start = time.time()
# lock = threading.Lock()
subject_timepoints = {subject_id: sorted(os.listdir(os.path.join(dceprep_dir, subject_id))) for subject_id in subjects}

with ThreadPoolExecutor() as executor:
    futures = [executor.submit(get_case_stats, subject_id, timepoint) for subject_id, timepoints in subject_timepoints.items() for timepoint in timepoints]
    for future in futures:
        try:
            future.result()
        except Exception as e:
            print(f"Error in future: {future}, {e}")
# end = time.time()
# print(f"Time taken: {end - start} seconds")
# get flagged cases
flagged_cases = []
flagged_links = []
MOTION_THRESHOLD = 3.8
AIFITNESS_THRESHOLD = 59
for entry in successful_timepoints:
    flag_str = ""
    subject = entry.split('/')[0]
    session = entry.split('/')[1]
    save_name = f"{output_dir}/{entry}/reports/{subject}_{session}_desc-casereport.html"
    flag = False
    entry = subject + "_" + session
    if entry in population_data.keys() and population_data[entry]['max_disp'] > MOTION_THRESHOLD:
        flag = True
        flag_str += "motion"
        save_name += "#MCFLIRT"
    if entry in population_data.keys() and population_data[entry]['AIFitness'] < AIFITNESS_THRESHOLD:
        flag = True
        if flag_str != "":
            flag_str += ", "
        flag_str += "AIFitness"
        if not save_name[-1].endswith("MCFLIRT"):
            save_name += "#AIF"
    if flag_str != "":
        flagged_cases.append(f'{entry} ({flag_str})')
        flagged_links.append(save_name)
    if flag:
        # move to population_data_exclude
        # put AUTO at beginning of flag_str
        flag_str = "AUTO: " + flag_str
        population_data_exclude[entry] = population_data.pop(entry)
        population_data_exclude[entry]['Reason'] = flag_str
        # move outliers to exclude
        if entry in whole_hippo_outliers:
            whole_hippo_outliers_exclude.append(whole_hippo_outliers.pop(whole_hippo_outliers.index(entry)))
        if entry in whole_phg_outliers:
            whole_phg_outliers_exclude.append(whole_phg_outliers.pop(whole_phg_outliers.index(entry)))
        if entry in whole_putamen_outliers:
            whole_putamen_outliers_exclude.append(whole_putamen_outliers.pop(whole_putamen_outliers.index(entry)))
        if entry in whole_pallidum_outliers:
            whole_pallidum_outliers_exclude.append(whole_pallidum_outliers.pop(whole_pallidum_outliers.index(entry)))
        if entry in whole_thalamus_outliers:
            whole_thalamus_outliers_exclude.append(whole_thalamus_outliers.pop(whole_thalamus_outliers.index(entry)))
        if entry in whole_caudate_outliers:
            whole_caudate_outliers_exclude.append(whole_caudate_outliers.pop(whole_caudate_outliers.index(entry)))
        if entry in whole_amygdala_outliers:
            whole_amygdala_outliers_exclude.append(whole_amygdala_outliers.pop(whole_amygdala_outliers.index(entry)))
        if entry in whole_entorhinal_cortex_outliers:
            whole_entorhinal_cortex_outliers_exclude.append(whole_entorhinal_cortex_outliers.pop(whole_entorhinal_cortex_outliers.index(entry)))
        if entry in whole_fusiform_gyrus_cortex_outliers:
            whole_fusiform_gyrus_cortex_outliers_exclude.append(whole_fusiform_gyrus_cortex_outliers.pop(whole_fusiform_gyrus_cortex_outliers.index(entry)))
        if entry in whole_fusiform_gyrus_WM_outliers:
            whole_fusiform_gyrus_WM_outliers_exclude.append(whole_fusiform_gyrus_WM_outliers.pop(whole_fusiform_gyrus_WM_outliers.index(entry)))
        if entry in whole_insula_WM_outliers:
            whole_insula_WM_outliers_exclude.append(whole_insula_WM_outliers.pop(whole_insula_WM_outliers.index(entry)))
        if entry in whole_superior_temporal_cortex_outliers:
            whole_superior_temporal_cortex_outliers_exclude.append(whole_superior_temporal_cortex_outliers.pop(whole_superior_temporal_cortex_outliers.index(entry)))
        if entry in whole_inferior_temporal_cortex_outliers:
            whole_inferior_temporal_cortex_outliers_exclude.append(whole_inferior_temporal_cortex_outliers.pop(whole_inferior_temporal_cortex_outliers.index(entry)))
        if entry in whole_posterior_cingulate_cortex_outliers:
            whole_posterior_cingulate_cortex_outliers_exclude.append(whole_posterior_cingulate_cortex_outliers.pop(whole_posterior_cingulate_cortex_outliers.index(entry)))
        if entry in whole_medial_temporal_cortex_outliers:
            whole_medial_temporal_cortex_outliers_exclude.append(whole_medial_temporal_cortex_outliers.pop(whole_medial_temporal_cortex_outliers.index(entry)))

# remove cases with Machine == Signa HDxt from population_data_exclude and population_data
# population_data_exclude_signa = {}
# for entry in list(population_data_exclude.keys()):
#     if population_data_exclude[entry]["Machine"] == "Signa HDxt":
#         population_data_exclude_signa[entry] = population_data_exclude.pop(entry)
#         population_data_exclude_signa[entry]['Reason'] = "AUTO: Crazy GE Data"

# for entry in list(population_data.keys()):
#     if population_data[entry]["Machine"] == "Signa HDxt":
#         population_data_exclude_signa[entry] = population_data.pop(entry)
#         population_data_exclude_signa[entry]['Reason'] = "AUTO: Crazy GE Data"

try:
    AIFitness_values = [float(population_data[entry]["AIFitness"]) for entry in population_data]
    AIFitness_mean = np.mean(AIFitness_values)
    AIFitness_median = np.median(AIFitness_values)
    AIFitness_std = np.std(AIFitness_values)
    AIFitness_5th_percentile = np.percentile(AIFitness_values, 5)
except Exception as e:
    print("AIFitness issue.", e)
    AIFitness_mean = -1
    AIFitness_median = -1
    AIFitness_std = -1
    AIFitness_5th_percentile = -1

try:
    AIFitness_exclude = [float(population_data_exclude[entry]["AIFitness"]) for entry in population_data_exclude]
    AIFitness_exclude_mean = np.mean(AIFitness_exclude)
    AIFitness_exclude_median = np.median(AIFitness_exclude)
    AIFitness_exclude_std = np.std(AIFitness_exclude)
    AIFitness_exclude_5th_percentile = np.percentile(AIFitness_exclude, 5)
except Exception as e:
    print("AIFitness issue.", e)
    AIFitness_exclude_mean = -1
    AIFitness_exclude_median = -1
    AIFitness_exclude_std = -1
    AIFitness_exclude_5th_percentile = -1

try:
    aif_mmol_mean = np.mean([population_data[entry]["aif_mmol"] for entry in population_data])
    aif_mmol_median = np.median([population_data[entry]["aif_mmol"] for entry in population_data])
    aif_mmol_std = np.std([population_data[entry]["aif_mmol"] for entry in population_data])
    aif_mmol_5th_percentile = np.percentile([population_data[entry]["aif_mmol"] for entry in population_data], 5)
    aif_mmol_95th_percentile = np.percentile([population_data[entry]["aif_mmol"] for entry in population_data], 95)
except Exception as e:
    print(e)
    aif_mmol_mean = -1
    aif_mmol_median = -1
    aif_mmol_std = -1
    aif_mmol_5th_percentile = -1
    aif_mmol_95th_percentile = -1

try:
    aif_mmol_exclude = [population_data_exclude[entry]["aif_mmol"] for entry in population_data_exclude]
    aif_mmol_mean_exclude = np.mean(aif_mmol_exclude)
    aif_mmol_median_exclude = np.median(aif_mmol_exclude)
    aif_mmol_std_exclude = np.std(aif_mmol_exclude)
    aif_mmol_5th_percentile_exclude = np.percentile(aif_mmol_exclude, 5)
    aif_mmol_95th_percentile_exclude = np.percentile(aif_mmol_exclude, 95)
except Exception as e:
    print(e)
    aif_mmol_mean_exclude = -1
    aif_mmol_median_exclude = -1
    aif_mmol_std_exclude = -1
    aif_mmol_5th_percentile_exclude = -1
    aif_mmol_95th_percentile_exclude = -1

try:
    T1_wm_mean = np.mean([population_data[entry]["T1_wm_median"] for entry in population_data])
    T1_wm_median = np.median([population_data[entry]["T1_wm_median"] for entry in population_data])
    T1_wm_std = np.std([population_data[entry]["T1_wm_median"] for entry in population_data])
    T1_wm_5th_percentile = np.percentile([population_data[entry]["T1_wm_median"] for entry in population_data], 5)
    T1_wm_95th_percentile = np.percentile([population_data[entry]["T1_wm_median"] for entry in population_data], 95)
except Exception as e:
    print(e)
    T1_wm_mean = -1
    T1_wm_median = -1
    T1_wm_std = -1
    T1_wm_5th_percentile = -1
    T1_wm_95th_percentile = -1

try:
    T1_wm_mean_exclude = np.mean([population_data_exclude[entry]["T1_wm_median"] for entry in population_data_exclude])
    T1_wm_median_exclude = np.median([population_data_exclude[entry]["T1_wm_median"] for entry in population_data_exclude])
    T1_wm_std_exclude = np.std([population_data_exclude[entry]["T1_wm_median"] for entry in population_data_exclude])
    T1_wm_5th_percentile_exclude = np.percentile([population_data_exclude[entry]["T1_wm_median"] for entry in population_data_exclude], 5)
    T1_wm_95th_percentile_exclude = np.percentile([population_data_exclude[entry]["T1_wm_median"] for entry in population_data_exclude], 95)
except Exception as e:
    print(e)
    T1_wm_mean_exclude = -1
    T1_wm_median_exclude = -1
    T1_wm_std_exclude = -1
    T1_wm_5th_percentile_exclude = -1
    T1_wm_95th_percentile_exclude = -1

try:
    T1_gm_mean = np.mean([population_data[entry]["T1_gm_median"] for entry in population_data])
    T1_gm_median = np.median([population_data[entry]["T1_gm_median"] for entry in population_data])
    T1_gm_std = np.std([population_data[entry]["T1_gm_median"] for entry in population_data])
    T1_gm_5th_percentile = np.percentile([population_data[entry]["T1_gm_median"] for entry in population_data], 5)
    T1_gm_95th_percentile = np.percentile([population_data[entry]["T1_gm_median"] for entry in population_data], 95)
except Exception as e:
    print(e)
    T1_gm_mean = -1
    T1_gm_median = -1
    T1_gm_std = -1
    T1_gm_5th_percentile = -1
    T1_gm_95th_percentile = -1

try:
    T1_gm_mean_exclude = np.mean([population_data_exclude[entry]["T1_gm_median"] for entry in population_data_exclude])
    T1_gm_median_exclude = np.median([population_data_exclude[entry]["T1_gm_median"] for entry in population_data_exclude])
    T1_gm_std_exclude = np.std([population_data_exclude[entry]["T1_gm_median"] for entry in population_data_exclude])
    T1_gm_5th_percentile_exclude = np.percentile([population_data_exclude[entry]["T1_gm_median"] for entry in population_data_exclude], 5)
    T1_gm_95th_percentile_exclude = np.percentile([population_data_exclude[entry]["T1_gm_median"] for entry in population_data_exclude], 95)
except Exception as e:
    print(e)
    T1_gm_mean_exclude = -1
    T1_gm_median_exclude = -1
    T1_gm_std_exclude = -1
    T1_gm_5th_percentile_exclude = -1
    T1_gm_95th_percentile_exclude = -1

try:
    T1_blood_mean = np.mean([population_data[entry]["T1_blood"] for entry in population_data])
    T1_blood_median = np.median([population_data[entry]["T1_blood"] for entry in population_data])
    T1_blood_std = np.std([population_data[entry]["T1_blood"] for entry in population_data])
    T1_blood_5th_percentile = np.percentile([population_data[entry]["T1_blood"] for entry in population_data], 5)
    T1_blood_95th_percentile = np.percentile([population_data[entry]["T1_blood"] for entry in population_data], 95)
except Exception as e:
    print(e)
    T1_blood_mean = -1
    T1_blood_median = -1
    T1_blood_std = -1
    T1_blood_5th_percentile = -1
    T1_blood_95th_percentile = -1

try:
    T1_blood_mean_exclude = np.mean([population_data_exclude[entry]["T1_blood"] for entry in population_data_exclude])
    T1_blood_median_exclude = np.median([population_data_exclude[entry]["T1_blood"] for entry in population_data_exclude])
    T1_blood_std_exclude = np.std([population_data_exclude[entry]["T1_blood"] for entry in population_data_exclude])
    T1_blood_5th_percentile_exclude = np.percentile([population_data_exclude[entry]["T1_blood"] for entry in population_data_exclude], 5)
    T1_blood_95th_percentile_exclude = np.percentile([population_data_exclude[entry]["T1_blood"] for entry in population_data_exclude], 95)
except Exception as e:
    print(e)
    T1_blood_mean_exclude = -1
    T1_blood_median_exclude = -1
    T1_blood_std_exclude = -1
    T1_blood_5th_percentile_exclude = -1
    T1_blood_95th_percentile_exclude = -1

try:
    Ktrans_wm_mean = np.nanmean([population_data[entry]["Ktrans_wm_median"] for entry in population_data])
    Ktrans_wm_median = np.nanmedian([population_data[entry]["Ktrans_wm_median"] for entry in population_data])
    Ktrans_wm_std = np.nanstd([population_data[entry]["Ktrans_wm_median"] for entry in population_data])
    Ktrans_gm_mean = np.nanmean([population_data[entry]["Ktrans_gm_median"] for entry in population_data])
    Ktrans_gm_median = np.nanmedian([population_data[entry]["Ktrans_gm_median"] for entry in population_data])
    Ktrans_gm_std = np.nanstd([population_data[entry]["Ktrans_gm_median"] for entry in population_data])
except Exception as e:
    print(e)
    Ktrans_wm_mean = -1
    Ktrans_wm_median = -1
    Ktrans_wm_std = -1
    Ktrans_gm_mean = -1
    Ktrans_gm_median = -1
    Ktrans_gm_std = -1

try:
    wm_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_wm_median"] for entry in population_data_exclude])
    wm_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_wm_median"] for entry in population_data_exclude])
    wm_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_wm_median"] for entry in population_data_exclude])
    gm_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_gm_median"] for entry in population_data_exclude])
    gm_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_gm_median"] for entry in population_data_exclude])
    gm_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_gm_median"] for entry in population_data_exclude])
except Exception as e:
    print(e)
    wm_mean_exclude = -1
    wm_median_exclude = -1
    wm_std_exclude = -1
    gm_mean_exclude = -1
    gm_median_exclude = -1
    gm_std_exclude = -1

whole_hippo_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Hippo_median"] for entry in population_data])
whole_hippo_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Hippo_median"] for entry in population_data])
whole_hippo_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Hippo_median"] for entry in population_data])

whole_hippo_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Hippo_median"] for entry in population_data_exclude])
whole_hippo_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Hippo_median"] for entry in population_data_exclude])
whole_hippo_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Hippo_median"] for entry in population_data_exclude])

whole_phg_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_PhG_median"] for entry in population_data])
whole_phg_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_PhG_median"] for entry in population_data])
whole_phg_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_PhG_median"] for entry in population_data])

whole_phg_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_PhG_median"] for entry in population_data_exclude])
whole_phg_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_PhG_median"] for entry in population_data_exclude])
whole_phg_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_PhG_median"] for entry in population_data_exclude])

whole_putamen_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Putamen_median"] for entry in population_data])
whole_putamen_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Putamen_median"] for entry in population_data])
whole_putamen_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Putamen_median"] for entry in population_data])

whole_putamen_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Putamen_median"] for entry in population_data_exclude])
whole_putamen_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Putamen_median"] for entry in population_data_exclude])
whole_putamen_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Putamen_median"] for entry in population_data_exclude])

whole_pallidum_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Pallidum_median"] for entry in population_data])
whole_pallidum_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Pallidum_median"] for entry in population_data])
whole_pallidum_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Pallidum_median"] for entry in population_data])

whole_pallidum_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Pallidum_median"] for entry in population_data_exclude])
whole_pallidum_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Pallidum_median"] for entry in population_data_exclude])
whole_pallidum_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Pallidum_median"] for entry in population_data_exclude])

whole_thalamus_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Thalamus_median"] for entry in population_data])
whole_thalamus_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Thalamus_median"] for entry in population_data])
whole_thalamus_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Thalamus_median"] for entry in population_data])

whole_thalamus_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Thalamus_median"] for entry in population_data_exclude])
whole_thalamus_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Thalamus_median"] for entry in population_data_exclude])
whole_thalamus_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Thalamus_median"] for entry in population_data_exclude])

whole_caudate_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Caudate_median"] for entry in population_data])
whole_caudate_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Caudate_median"] for entry in population_data])
whole_caudate_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Caudate_median"] for entry in population_data])

whole_caudate_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Caudate_median"] for entry in population_data_exclude])
whole_caudate_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Caudate_median"] for entry in population_data_exclude])
whole_caudate_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Caudate_median"] for entry in population_data_exclude])

whole_amygdala_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Amygdala_median"] for entry in population_data])
whole_amygdala_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Amygdala_median"] for entry in population_data])
whole_amygdala_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Amygdala_median"] for entry in population_data])

whole_amygdala_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Amygdala_median"] for entry in population_data_exclude])
whole_amygdala_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Amygdala_median"] for entry in population_data_exclude])
whole_amygdala_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Amygdala_median"] for entry in population_data_exclude])

whole_entorhinal_cortex_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data])
whole_entorhinal_cortex_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data])
whole_entorhinal_cortex_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data])

whole_entorhinal_cortex_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data_exclude])
whole_entorhinal_cortex_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data_exclude])
whole_entorhinal_cortex_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data_exclude])

whole_fusiform_gyrus_cortex_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data])
whole_fusiform_gyrus_cortex_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data])
whole_fusiform_gyrus_cortex_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data])

whole_fusiform_gyrus_cortex_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data_exclude])
whole_fusiform_gyrus_cortex_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data_exclude])
whole_fusiform_gyrus_cortex_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data_exclude])

whole_fusiform_gyrus_WM_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data])
whole_fusiform_gyrus_WM_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data])
whole_fusiform_gyrus_WM_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data])

whole_fusiform_gyrus_WM_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data_exclude])
whole_fusiform_gyrus_WM_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data_exclude])
whole_fusiform_gyrus_WM_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data_exclude])

whole_insula_WM_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Insula_WM_median"] for entry in population_data])
whole_insula_WM_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Insula_WM_median"] for entry in population_data])
whole_insula_WM_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Insula_WM_median"] for entry in population_data])

whole_insula_WM_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Insula_WM_median"] for entry in population_data_exclude])
whole_insula_WM_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Insula_WM_median"] for entry in population_data_exclude])
whole_insula_WM_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Insula_WM_median"] for entry in population_data_exclude])

whole_superior_temporal_cortex_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data])
whole_superior_temporal_cortex_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data])
whole_superior_temporal_cortex_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data])

whole_superior_temporal_cortex_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data_exclude])
whole_superior_temporal_cortex_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data_exclude])
whole_superior_temporal_cortex_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data_exclude])

whole_inferior_temporal_cortex_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Inferior_temporal_cortex_median"] for entry in population_data])
whole_inferior_temporal_cortex_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Inferior_temporal_cortex_median"] for entry in population_data])
whole_inferior_temporal_cortex_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Inferior_temporal_cortex_median"] for entry in population_data])

whole_inferior_temporal_cortex_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Inferior_temporal_cortex_median"] for entry in population_data_exclude])
whole_inferior_temporal_cortex_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Inferior_temporal_cortex_median"] for entry in population_data_exclude])
whole_inferior_temporal_cortex_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Inferior_temporal_cortex_median"] for entry in population_data_exclude])

whole_posterior_cingulate_cortex_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Posterior_cingulate_cortex_median"] for entry in population_data])
whole_posterior_cingulate_cortex_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Posterior_cingulate_cortex_median"] for entry in population_data])
whole_posterior_cingulate_cortex_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Posterior_cingulate_cortex_median"] for entry in population_data])

whole_posterior_cingulate_cortex_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Posterior_cingulate_cortex_median"] for entry in population_data_exclude])
whole_posterior_cingulate_cortex_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Posterior_cingulate_cortex_median"] for entry in population_data_exclude])
whole_posterior_cingulate_cortex_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Posterior_cingulate_cortex_median"] for entry in population_data_exclude])

whole_medial_temporal_cortex_Ktrans_mean = np.nanmean([population_data[entry]["Ktrans_Medial_temporal_cortex_median"] for entry in population_data])
whole_medial_temporal_cortex_Ktrans_median = np.nanmedian([population_data[entry]["Ktrans_Medial_temporal_cortex_median"] for entry in population_data])
whole_medial_temporal_cortex_Ktrans_std = np.nanstd([population_data[entry]["Ktrans_Medial_temporal_cortex_median"] for entry in population_data])

whole_medial_temporal_cortex_Ktrans_mean_exclude = np.nanmean([population_data_exclude[entry]["Ktrans_Medial_temporal_cortex_median"] for entry in population_data_exclude])
whole_medial_temporal_cortex_Ktrans_median_exclude = np.nanmedian([population_data_exclude[entry]["Ktrans_Medial_temporal_cortex_median"] for entry in population_data_exclude])
whole_medial_temporal_cortex_Ktrans_std_exclude = np.nanstd([population_data_exclude[entry]["Ktrans_Medial_temporal_cortex_median"] for entry in population_data_exclude])

# if no outliers, set to "None"
if len(Ktrans_wm_outliers) == 0:
    Ktrans_wm_outliers = "None"
if len(Ktrans_gm_outliers) == 0:
    Ktrans_gm_outliers = "None"

# make figures directory if it doesn't exist
if not os.path.exists(os.path.join("figures/")):
    os.makedirs(os.path.join("figures/"))

# make T1 blood histogram
T1_blood_histogram = []
for entry in population_data.keys():
    T1_blood_histogram.append(population_data[entry]["T1_blood"])

date_filename = datetime.datetime.now().strftime("%Y-%m-%d")

# plot histogram
plt.hist(T1_blood_histogram, bins=30)
plt.title("T1 Blood")
plt.xlabel("T1 Blood")
T1_blood_histogram_path = os.path.join("figures/", "T1_blood_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(T1_blood_histogram_path, bbox_inches='tight')
plt.close()

T1_blood_histogram_exclude = []
for entry in population_data_exclude.keys():
    T1_blood_histogram_exclude.append(population_data_exclude[entry]["T1_blood"])

# plot histogram
plt.hist(T1_blood_histogram_exclude, bins=30)
plt.title("T1 Blood (Exclude)")
plt.xlabel("T1 Blood")
T1_blood_histogram_exclude_path = os.path.join("figures/", "T1_blood_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(T1_blood_histogram_exclude_path, bbox_inches='tight')
plt.close()

# make AIFitness histogram
plt.hist(AIFitness_values, bins=30)
plt.title("AIFitness Median")
plt.xlabel("AIFitness")
aifitness_histogram_path = os.path.join("figures/", "aifitness_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(aifitness_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(AIFitness_exclude, bins=30)
plt.title("AIFitness Median (Exclude)")
plt.xlabel("AIFitness")
aifitness_histogram_exclude_path = os.path.join("figures/", "aifitness_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(aifitness_histogram_exclude_path, bbox_inches='tight')
plt.close()

# make aif_mmol histogram
aif_mmol_histogram = []
for entry in population_data.keys():
    aif_mmol_histogram.append(population_data[entry]["aif_mmol"])

# plot histogram
plt.hist(aif_mmol_histogram, bins=30)
plt.title("AIF mmol (mean of last 1/3)")
plt.xlabel("AIF mmol")
aif_mmol_histogram_path = os.path.join("figures/", "aif_mmol_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(aif_mmol_histogram_path, bbox_inches='tight')
plt.close()

aif_mmol_histogram_exclude = []
for entry in population_data_exclude.keys():
    aif_mmol_histogram_exclude.append(population_data_exclude[entry]["aif_mmol"])

# plot histogram
plt.hist(aif_mmol_histogram_exclude, bins=30)
plt.title("AIF mmol (mean of last 1/3) (Exclude)")
plt.xlabel("AIF mmol")
aif_mmol_histogram_exclude_path = os.path.join("figures/", "aif_mmol_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(aif_mmol_histogram_exclude_path, bbox_inches='tight')
plt.close()

# make ktrans histograms from each timepoint mean
wm_histogram = []
for entry in population_data.keys():
    wm_histogram.append(population_data[entry]["Ktrans_wm_median"])

# plot histogram
plt.hist(wm_histogram, bins=50, range=(0, 5))
plt.title("White Matter Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
ktrans_wm_histogram_path = os.path.join("figures/", "wm_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(ktrans_wm_histogram_path, bbox_inches='tight')
plt.close()

ktrans_wm_histogram_exclude = []
for entry in population_data_exclude.keys():
    ktrans_wm_histogram_exclude.append(population_data_exclude[entry]["Ktrans_wm_median"])

# plot histogram
plt.hist(ktrans_wm_histogram_exclude, bins=50, range=(0, 5))
plt.title("White Matter Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
ktrans_wm_histogram_exclude_path = os.path.join("figures/", "wm_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(ktrans_wm_histogram_exclude_path, bbox_inches='tight')
plt.close()

# now get gm mean histogram
gm_histogram = []
for entry in population_data.keys():
    gm_histogram.append(population_data[entry]["Ktrans_gm_median"])

# plot histogram
plt.hist(gm_histogram, bins=50, range=(0, 5))
plt.title("Gray Matter Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
ktrans_gm_histogram_path = os.path.join("figures/", "gm_histogram" + output_dir + "_" + date_filename + ".png")
# save range of histogram for later use
gm_histogram_range = plt.xlim()
plt.savefig(ktrans_gm_histogram_path, bbox_inches='tight')
plt.close()

ktrans_gm_histogram_exclude = []
for entry in population_data_exclude.keys():
    ktrans_gm_histogram_exclude.append(population_data_exclude[entry]["Ktrans_gm_median"])

# plot histogram
plt.hist(ktrans_gm_histogram_exclude, bins=50, range=(0, 5))
plt.title("Gray Matter Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
ktrans_gm_histogram_exclude_path = os.path.join("figures/", "gm_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.xlim(gm_histogram_range)
plt.savefig(ktrans_gm_histogram_exclude_path, bbox_inches='tight')
plt.close()

try:
    pop_avg_AIF = np.asarray(popAIF_curves)
    pop_avg_AIF = np.mean(pop_avg_AIF, axis=0)
    # save average curve to export into MATLAB
    np.savetxt("average_aif_curve.csv", pop_avg_AIF, delimiter=",")
    for aif in popAIF_curves:
        plt.plot(aif, linewidth=0.5, color='grey', alpha=0.5)
    plt.plot(pop_avg_AIF, linewidth=1, color='black')
    # plot stdev per timepoint
    plt.fill_between(np.arange(0, len(pop_avg_AIF)), pop_avg_AIF - np.std(popAIF_curves, axis=0), pop_avg_AIF + np.std(popAIF_curves, axis=0), alpha=0.3)
    plt.xlabel('Time (s)')
    plt.ylabel('Normalized Intensity')
    plt.title('AIF Curves (Modified for MATLAB Import)')
    aif_pop_avg_path = os.path.join("figures/", "aif_pop_avg_AIF" + output_dir + "_" + date_filename + ".png")
    plt.savefig(aif_pop_avg_path, bbox_inches='tight', dpi=300)  # Increase dpi for higher resolution
    plt.close()
except Exception as e:
    print("Error plotting population AIF curve.", e)
    aif_pop_avg_path = "Error plotting population average AIF curve."

try:
    # plot true AIFs
    aif_curves = np.asarray(aif_curves)
    aif_curves_avg = np.nanmean(aif_curves, axis=0)
    for aif in aif_curves:
        plt.plot(aif, linewidth=0.5, color='grey', alpha=0.5)
    plt.plot(aif_curves_avg, linewidth=1, color='black')
    # plot 95% confidence interval
    plt.fill_between(np.arange(0, len(aif_curves_avg)), aif_curves_avg - np.std(aif_curves, axis=0), aif_curves_avg + np.std(aif_curves, axis=0), alpha=0.3)
    plt.xlabel('Time (s)')
    plt.ylabel('Normalized Intensity')
    plt.title('AIF Curves')
    aif_curves_path = os.path.join("figures/", "aif_pop_AIF" + output_dir + "_" + date_filename + ".png")
    plt.savefig(aif_curves_path, bbox_inches='tight', dpi=300)  # Increase dpi for higher resolution
    plt.close()
except Exception as e:
    print("Error plotting population AIF curve.", e)
    aif_curves_path = "Error plotting population AIF curves."

Ktrans_histograms = {
    "whole_hippo": [],
    "whole_phg": [],
    "whole_putamen": [],
    "whole_pallidum": [],
    "whole_thalamus": [],
    "whole_caudate": [],
    "whole_amygdala": [],
    "whole_entorhinal_cortex": [],
    "whole_fusiform_gyrus_cortex": [],
    "whole_fusiform_gyrus_WM": [],
    "whole_insula_WM": [],
    "whole_superior_temporal_cortex": [],
    "whole_inferior_temporal_cortex": [],
    "whole_posterior_cingulate_cortex": [],
    "whole_medial_temporal_cortex": []
}

Vp_histograms = {
    "whole_hippo": [],
    "whole_phg": [],
    "whole_putamen": [],
    "whole_pallidum": [],
    "whole_thalamus": [],
    "whole_caudate": [],
    "whole_amygdala": [],
    "whole_entorhinal_cortex": [],
    "whole_fusiform_gyrus_cortex": [],
    "whole_fusiform_gyrus_WM": [],
    "whole_insula_WM": [],
    "whole_superior_temporal_cortex": [],
    "whole_inferior_temporal_cortex": [],
    "whole_posterior_cingulate_cortex": [],
    "whole_medial_temporal_cortex": []
}
for entry in population_data.keys():
    Ktrans_histograms["whole_hippo"].append(population_data[entry]["Ktrans_Hippo_median"])
    Ktrans_histograms["whole_phg"].append(population_data[entry]["Ktrans_PhG_median"])
    Ktrans_histograms["whole_putamen"].append(population_data[entry]["Ktrans_Putamen_median"])
    Ktrans_histograms["whole_pallidum"].append(population_data[entry]["Ktrans_Pallidum_median"])
    Ktrans_histograms["whole_thalamus"].append(population_data[entry]["Ktrans_Thalamus_median"])
    Ktrans_histograms["whole_caudate"].append(population_data[entry]["Ktrans_Caudate_median"])
    Ktrans_histograms["whole_amygdala"].append(population_data[entry]["Ktrans_Amygdala_median"])
    Ktrans_histograms["whole_entorhinal_cortex"].append(population_data[entry]["Ktrans_Entorhinal_cortex_median"])
    Ktrans_histograms["whole_fusiform_gyrus_cortex"].append(population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"])
    Ktrans_histograms["whole_fusiform_gyrus_WM"].append(population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"])
    Ktrans_histograms["whole_insula_WM"].append(population_data[entry]["Ktrans_Insula_WM_median"])
    Ktrans_histograms["whole_superior_temporal_cortex"].append(population_data[entry]["Ktrans_Superior_temporal_cortex_median"])
    Ktrans_histograms["whole_inferior_temporal_cortex"].append(population_data[entry]["Ktrans_Inferior_temporal_cortex_median"])
    Ktrans_histograms["whole_posterior_cingulate_cortex"].append(population_data[entry]["Ktrans_Posterior_cingulate_cortex_median"])
    Ktrans_histograms["whole_medial_temporal_cortex"].append(population_data[entry]["Ktrans_Medial_temporal_cortex_median"])
    Vp_histograms["whole_hippo"].append(population_data[entry]["Vp_Hippo_median"])
    Vp_histograms["whole_phg"].append(population_data[entry]["Vp_PhG_median"])
    Vp_histograms["whole_putamen"].append(population_data[entry]["Vp_Putamen_median"])
    Vp_histograms["whole_pallidum"].append(population_data[entry]["Vp_Pallidum_median"])
    Vp_histograms["whole_thalamus"].append(population_data[entry]["Vp_Thalamus_median"])
    Vp_histograms["whole_caudate"].append(population_data[entry]["Vp_Caudate_median"])
    Vp_histograms["whole_amygdala"].append(population_data[entry]["Vp_Amygdala_median"])
    Vp_histograms["whole_entorhinal_cortex"].append(population_data[entry]["Vp_Entorhinal_cortex_median"])
    Vp_histograms["whole_fusiform_gyrus_cortex"].append(population_data[entry]["Vp_Fusiform_gyrus_cortex_median"])
    Vp_histograms["whole_fusiform_gyrus_WM"].append(population_data[entry]["Vp_Fusiform_gyrus_WM_median"])
    Vp_histograms["whole_insula_WM"].append(population_data[entry]["Vp_Insula_WM_median"])
    Vp_histograms["whole_superior_temporal_cortex"].append(population_data[entry]["Vp_Superior_temporal_cortex_median"])
    Vp_histograms["whole_inferior_temporal_cortex"].append(population_data[entry]["Vp_Inferior_temporal_cortex_median"])
    Vp_histograms["whole_posterior_cingulate_cortex"].append(population_data[entry]["Vp_Posterior_cingulate_cortex_median"])
    Vp_histograms["whole_medial_temporal_cortex"].append(population_data[entry]["Vp_Medial_temporal_cortex_median"])

whole_hippo_histogram_exclude = []
whole_phg_histogram_exclude = []
whole_putamen_histogram_exclude = []
whole_pallidum_histogram_exclude = []
whole_thalamus_histogram_exclude = []
whole_caudate_histogram_exclude = []
whole_amygdala_histogram_exclude = []
whole_entorhinal_cortex_histogram_exclude = []
whole_fusiform_gyrus_cortex_histogram_exclude = []
whole_fusiform_gyrus_WM_histogram_exclude = []
whole_insula_WM_histogram_exclude = []
whole_superior_temporal_cortex_histogram_exclude = []
whole_inferior_temporal_cortex_histogram_exclude = []
whole_posterior_cingulate_cortex_histogram_exclude = []
whole_medial_temporal_cortex_histogram_exclude = []
for entry in population_data_exclude.keys():
    whole_hippo_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Hippo_median"])
    whole_phg_histogram_exclude.append(population_data_exclude[entry]["Ktrans_PhG_median"])
    whole_putamen_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Putamen_median"])
    whole_pallidum_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Pallidum_median"])
    whole_thalamus_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Thalamus_median"])
    whole_caudate_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Caudate_median"])
    whole_amygdala_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Amygdala_median"])
    whole_entorhinal_cortex_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Entorhinal_cortex_median"])
    whole_fusiform_gyrus_cortex_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Fusiform_gyrus_cortex_median"])
    whole_fusiform_gyrus_WM_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Fusiform_gyrus_WM_median"])
    whole_insula_WM_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Insula_WM_median"])
    whole_superior_temporal_cortex_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Superior_temporal_cortex_median"])
    whole_inferior_temporal_cortex_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Inferior_temporal_cortex_median"])
    whole_posterior_cingulate_cortex_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Posterior_cingulate_cortex_median"])
    whole_medial_temporal_cortex_histogram_exclude.append(population_data_exclude[entry]["Ktrans_Medial_temporal_cortex_median"])

plt.hist(Ktrans_histograms["whole_hippo"], bins=50, range=(0, 5))
plt.title("Whole Hippocampus Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_hippo_histogram_path = os.path.join("figures/", "Ktrans_whole_hippo_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_hippo_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_phg"], bins=50, range=(0, 5))
plt.title("Whole Parahippocampal Gyrus Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_phg_histogram_path = os.path.join("figures/", "Ktrans_whole_phg_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_phg_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_putamen"], bins=50, range=(0, 5))
plt.title("Whole Putamen Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_putamen_histogram_path = os.path.join("figures/", "Ktrans_whole_putamen_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_putamen_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_pallidum"], bins=50, range=(0, 5))
plt.title("Whole Pallidum Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_pallidum_histogram_path = os.path.join("figures/", "Ktrans_whole_pallidum_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_pallidum_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_thalamus"], bins=50, range=(0, 5))
plt.title("Whole Thalamus Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_thalamus_histogram_path = os.path.join("figures/", "Ktrans_whole_thalamus_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_thalamus_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_caudate"], bins=50, range=(0, 5))
plt.title("Whole Caudate Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_caudate_histogram_path = os.path.join("figures/", "Ktrans_whole_caudate_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_caudate_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_amygdala"], bins=50, range=(0, 5))
plt.title("Whole Amygdala Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_amygdala_histogram_path = os.path.join("figures/", "Ktrans_whole_amygdala_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_amygdala_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_entorhinal_cortex"], bins=50, range=(0, 5))
plt.title("Whole Entorhinal Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_entorhinal_cortex_histogram_path = os.path.join("figures/", "Ktrans_whole_entorhinal_cortex_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_entorhinal_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_fusiform_gyrus_cortex"], bins=50, range=(0, 5))
plt.title("Whole Fusiform Gyrus Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_fusiform_gyrus_cortex_histogram_path = os.path.join("figures/", "Ktrans_whole_fusiform_gyrus_cortex_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_fusiform_gyrus_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_fusiform_gyrus_WM"], bins=50, range=(0, 5))
plt.title("Whole Fusiform Gyrus WM Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_fusiform_gyrus_WM_histogram_path = os.path.join("figures/", "Ktrans_whole_fusiform_gyrus_WM_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_fusiform_gyrus_WM_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_insula_WM"], bins=50, range=(0, 5))
plt.title("Whole Insula WM Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_insula_WM_histogram_path = os.path.join("figures/", "Ktrans_whole_insula_WM_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_insula_WM_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_superior_temporal_cortex"], bins=50, range=(0, 5))
plt.title("Whole Superior Temporal Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_superior_temporal_cortex_histogram_path = os.path.join("figures/", "Ktrans_whole_superior_temporal_cortex_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_superior_temporal_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_inferior_temporal_cortex"], bins=50, range=(0, 5))
plt.title("Whole Inferior Temporal Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_inferior_temporal_cortex_histogram_path = os.path.join("figures/", "Ktrans_whole_inferior_temporal_cortex_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_inferior_temporal_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_posterior_cingulate_cortex"], bins=50, range=(0, 5))
plt.title("Whole Posterior Cingulate Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_posterior_cingulate_cortex_histogram_path = os.path.join("figures/", "Ktrans_whole_posterior_cingulate_cortex_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_posterior_cingulate_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(Ktrans_histograms["whole_medial_temporal_cortex"], bins=50, range=(0, 5))
plt.title("Whole Medial Temporal Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
Ktrans_whole_medial_temporal_cortex_histogram_path = os.path.join("figures/", "Ktrans_whole_medial_temporal_cortex_histogram" + output_dir + "_" + date_filename + ".png")
plt.savefig(Ktrans_whole_medial_temporal_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_hippo_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Hippocampus Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_hippo_histogram_exclude_path = os.path.join("figures/", "whole_hippo_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_hippo_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_phg_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Parahippocampal Gyrus Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_phg_histogram_exclude_path = os.path.join("figures/", "whole_phg_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_phg_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_putamen_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Putamen Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_putamen_histogram_exclude_path = os.path.join("figures/", "whole_putamen_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_putamen_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_pallidum_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Pallidum Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_pallidum_histogram_exclude_path = os.path.join("figures/", "whole_pallidum_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_pallidum_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_thalamus_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Thalamus Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_thalamus_histogram_exclude_path = os.path.join("figures/", "whole_thalamus_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_thalamus_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_caudate_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Caudate Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_caudate_histogram_exclude_path = os.path.join("figures/", "whole_caudate_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_caudate_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_amygdala_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Amygdala Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_amygdala_histogram_exclude_path = os.path.join("figures/", "whole_amygdala_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_amygdala_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_entorhinal_cortex_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Entorhinal Cortex Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_entorhinal_cortex_histogram_exclude_path = os.path.join("figures/", "whole_entorhinal_cortex_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_entorhinal_cortex_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_fusiform_gyrus_cortex_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Fusiform Gyrus Cortex Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_fusiform_gyrus_cortex_histogram_exclude_path = os.path.join("figures/", "whole_fusiform_gyrus_cortex_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_fusiform_gyrus_cortex_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_fusiform_gyrus_WM_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Fusiform Gyrus WM Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_fusiform_gyrus_WM_histogram_exclude_path = os.path.join("figures/", "whole_fusiform_gyrus_WM_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_fusiform_gyrus_WM_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_insula_WM_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Insula WM Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_insula_WM_histogram_exclude_path = os.path.join("figures/", "whole_insula_WM_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_insula_WM_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_superior_temporal_cortex_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Superior Temporal Cortex Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_superior_temporal_cortex_histogram_exclude_path = os.path.join("figures/", "whole_superior_temporal_cortex_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_superior_temporal_cortex_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_inferior_temporal_cortex_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Inferior Temporal Cortex Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_inferior_temporal_cortex_histogram_exclude_path = os.path.join("figures/", "whole_inferior_temporal_cortex_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_inferior_temporal_cortex_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_posterior_cingulate_cortex_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Posterior Cingulate Cortex Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_posterior_cingulate_cortex_histogram_exclude_path = os.path.join("figures/", "whole_posterior_cingulate_cortex_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_posterior_cingulate_cortex_histogram_exclude_path, bbox_inches='tight')
plt.close()

plt.hist(whole_medial_temporal_cortex_histogram_exclude, bins=50, range=(0, 5))
plt.title("Whole Medial Temporal Cortex Median Ktrans (Exclude)")
plt.xlabel("Ktrans (10^-3/min)")
whole_medial_temporal_cortex_histogram_exclude_path = os.path.join("figures/", "whole_medial_temporal_cortex_histogram_exclude" + output_dir + "_" + date_filename + ".png")
plt.savefig(whole_medial_temporal_cortex_histogram_exclude_path, bbox_inches='tight')
plt.close()

# round to 4 decimal places
Ktrans_wm_mean = round(Ktrans_wm_mean, 4)
Ktrans_wm_median = round(Ktrans_wm_median, 4)
Ktrans_wm_std = round(Ktrans_wm_std, 4)
Ktrans_gm_mean = round(Ktrans_gm_mean, 4)
Ktrans_gm_median = round(Ktrans_gm_median, 4)
Ktrans_gm_std = round(Ktrans_gm_std, 4)

wm_mean_exclude = round(wm_mean_exclude, 4)
wm_median_exclude = round(wm_median_exclude, 4)
wm_std_exclude = round(wm_std_exclude, 4)
gm_mean_exclude = round(gm_mean_exclude, 4)
gm_median_exclude = round(gm_median_exclude, 4)
gm_std_exclude = round(gm_std_exclude, 4)

# use jinja2 to generate html
env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(os.path.realpath(__file__))))
template = env.get_template('population_template.html')

# get date
date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# get commit hash for this repo
try:
    commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(os.path.realpath(__file__))).decode('ascii').strip()
except Exception as e:
    print("Git didn't work correctly. Trying a different way of getting latest dev branch commit hash...")
    command = ['cat', '.git/refs/heads/dev']
    commit_hash = subprocess.check_output(command, cwd=os.path.dirname(os.path.realpath(__file__))).decode('ascii').strip()

# get commit hash for ROCKETSHIP repo
try:
    ROCKETSHIP_commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROCKETSHIP_dir).decode('ascii').strip()
except Exception as e:
    print("Could not get ROCKETSHIP commit hash:", e)
    ROCKETSHIP_commit_hash = "N/A"

# make dict of manufacturer, field strength, machine, and institution
manufacturers = {}
field_strengths = {}
machines = {}
institutions = {}
try:
    for entry in population_data.keys():
        manufacturer = population_data[entry]["Manufacturer"]
        field_strength = population_data[entry]["Field_strength"]
        machine = population_data[entry]["Machine"]
        institution = population_data[entry]["Institution"]
        if manufacturer in manufacturers.keys():
            manufacturers[manufacturer] += 1
        else:
            manufacturers[manufacturer] = 1
        if field_strength in field_strengths.keys():
            field_strengths[field_strength] += 1
        else:
            field_strengths[field_strength] = 1
        if machine in machines.keys():
            machines[machine] += 1
        else:
            machines[machine] = 1
        if institution in institutions.keys():
            institutions[institution] += 1
        else:
            institutions[institution] = 1
except Exception as e:
    print("Error in getting manufacturer, field strength, machine, and institution data.")
    print(e)

manufacturers_exclude = {}
field_strengths_exclude = {}
machines_exclude = {}
institutions_exclude = {}
try:
    for entry in population_data_exclude.keys():
        manufacturer = population_data_exclude[entry]["Manufacturer"]
        field_strength = population_data_exclude[entry]["Field_strength"]
        machine = population_data_exclude[entry]["Machine"]
        institution = population_data_exclude[entry]["Institution"]
        if manufacturer in manufacturers_exclude.keys():
            manufacturers_exclude[manufacturer] += 1
        else:
            manufacturers_exclude[manufacturer] = 1
        if field_strength in field_strengths_exclude.keys():
            field_strengths_exclude[field_strength] += 1
        else:
            field_strengths_exclude[field_strength] = 1
        if machine in machines_exclude.keys():
            machines_exclude[machine] += 1
        else:
            machines_exclude[machine] = 1
        if institution in institutions_exclude.keys():
            institutions_exclude[institution] += 1
        else:
            institutions_exclude[institution] = 1
except Exception as e:
    print("Error in getting manufacturer, field strength, machine, and institution data.")
    print(e)

successful_timepoints = list(set(successful_timepoints))
successful_timepoints.sort()
# num_timepoints = len(successful_timepoints)
# remove output_dir from successful_timepoints
cases = [timepoint for timepoint in successful_timepoints]
successful_links = []
for timepoint in successful_timepoints:
    subject = timepoint.split('/')[0]
    session = timepoint.split('/')[1]
    successful_links.append(f"dceprep{output_dir}/{subject}/{session}/reports/{subject}_{session}_desc-casereport.html")
# get failed cases from total_timepoints not in successful_timepoints
failed_cases = [timepoint for timepoint in total_timepoints if timepoint not in successful_timepoints]
# get links for each failed case's directory
failed_links = [os.path.join(dceprep_dir, case) for case in failed_cases]

# read ROCKETSHIP preference file
with open(ROCKETSHIP_dir + "/script_preferences.txt", "r") as f:
    lines = f.readlines()
    for line in lines:
        if "tr =" in line:
            pref_tr = line.split("= ")[1].strip()
        elif "fa =" in line:
            pref_fa = line.split("= ")[1].strip()
        elif "hematocrit =" in line:
            pref_hematocrit = line.split("= ")[1].strip()
        elif "snr_filter =" in line:
            pref_SNR = line.split("= ")[1].strip()
        elif "relaxivity =" in line and "pref_relaxivity" not in locals():
            pref_relaxivity = line.split("= ")[1].strip()
        elif "blood_t1 =" in line:
            pref_t1blood = line.split("= ")[1].strip()
        elif "start_t =" in line:
            pref_start_t = line.split("= ")[1].strip()
        elif "end_t =" in line:
            pref_end_t = line.split("= ")[1].strip()
        elif "time_resolution =" in line:
            pref_timeres = line.split("= ")[1].strip()
        elif "tofts = 1" in line:
            DCE_model = "Tofts"
        elif "ex_tofts = 1" in line:
            DCE_model = "Tofts Extended"
        elif "patlak = 1" in line:
            DCE_model = "Patlak"
        elif "tissue_uptake = 1" in line:
            DCE_model = "Tissue Uptake"
        elif "two_cxm = 1" in line:
            DCE_model = "Two Compartment Exchange"

data = {
    'Subjects' : subjects,
    # 'base_url': dceprep_dir,
    'Links': successful_links,
    'Failed_links': failed_links,
    'Cases': cases,
    'Failed_cases': failed_cases,
    'Flagged_cases': flagged_cases,
    'Combo': zip(successful_links, cases),
    'Failed_combo': zip(failed_links, failed_cases),
    'Motion_threshold': MOTION_THRESHOLD,
    'AIFitness_threshold': AIFITNESS_THRESHOLD,
    'Flagged_combo': zip(flagged_links, flagged_cases),
    'Subject_count': len(subjects),
    'Successes': str(len(population_data)) + '/' + str(len(total_timepoints)) + ' (' + str(round((len(population_data) / len(total_timepoints)) * 100, 2)) + '%)',
    'Excludes': str(len(population_data_exclude)) + '/' + str(len(total_timepoints)) + ' (' + str(round((len(population_data_exclude) / len(total_timepoints)) * 100, 2)) + '%)',
    'Date': date,
    'Commit': commit_hash,
    'ROCKETSHIP_commit': ROCKETSHIP_commit_hash,
    'Manufacturers': manufacturers,
    'Field_strengths': field_strengths,
    'Machines': machines,
    'Institutions': institutions,
    'pref_tr': pref_tr,
    'pref_fa': pref_fa,
    'pref_hematocrit': pref_hematocrit,
    'pref_SNR': pref_SNR,
    'pref_relaxivity': pref_relaxivity,
    'pref_t1blood': pref_t1blood,
    'pref_start_t': pref_start_t,
    'pref_end_t': pref_end_t,
    'pref_timeres': pref_timeres,
    'pref_model': DCE_model,
    'T1_wm_mean': round(T1_wm_mean, 4),
    'T1_wm_median': round(T1_wm_median, 4),
    'T1_wm_std': round(T1_wm_std, 4),
    'T1_wm_5th_percentile': round(T1_wm_5th_percentile, 4),
    'T1_wm_95th_percentile': round(T1_wm_95th_percentile, 4),
    'T1_gm_mean': round(T1_gm_mean, 4),
    'T1_gm_median': round(T1_gm_median, 4),
    'T1_gm_std': round(T1_gm_std, 4),
    'T1_gm_5th_percentile': round(T1_gm_5th_percentile, 4),
    'T1_gm_95th_percentile': round(T1_gm_95th_percentile, 4),
    'T1_blood_mean': round(T1_blood_mean, 4),
    'T1_blood_median': round(T1_blood_median, 4),
    'T1_blood_std': round(T1_blood_std, 4),
    'T1_blood_5th_percentile': round(T1_blood_5th_percentile, 4),
    'T1_blood_95th_percentile': round(T1_blood_95th_percentile, 4),
    'AIFitness_mean': round(AIFitness_mean, 4),
    'AIFitness_median': round(AIFitness_median, 4),
    'AIFitness_std': round(AIFitness_std, 4),
    'AIFitness_5th_percentile': round(AIFitness_5th_percentile, 4),
    'aif_mmol_mean': round(aif_mmol_mean, 4),
    'aif_mmol_median': round(aif_mmol_median, 4),
    'aif_mmol_std': round(aif_mmol_std, 4),
    'aif_mmol_5th_percentile': round(aif_mmol_5th_percentile, 4),
    'aif_mmol_95th_percentile': round(aif_mmol_95th_percentile, 4),
    'AIFitness_histogram' : "../../" + aifitness_histogram_path,
    'aif_mmol_histogram': "../../" + aif_mmol_histogram_path,
    'aif_pop_avg_AIF': "../../" + aif_pop_avg_path,
    'aif_curves': "../../" + aif_curves_path,
    'Ktrans_wm_mean': Ktrans_wm_mean,
    'Ktrans_wm_median': Ktrans_wm_median,
    'Ktrans_wm_std': Ktrans_wm_std,
    'Ktrans_gm_mean': Ktrans_gm_mean,
    'Ktrans_gm_median': Ktrans_gm_median,
    'Ktrans_gm_std': Ktrans_gm_std,
    'whole_hippo_Ktrans_mean': round(whole_hippo_Ktrans_mean, 4),
    'whole_hippo_Ktrans_median': round(whole_hippo_Ktrans_median, 4),
    'whole_hippo_Ktrans_std': round(whole_hippo_Ktrans_std, 4),
    'whole_phg_Ktrans_mean': round(whole_phg_Ktrans_mean, 4),
    'whole_phg_Ktrans_median': round(whole_phg_Ktrans_median, 4),
    'whole_phg_Ktrans_std': round(whole_phg_Ktrans_std, 4),
    'whole_putamen_Ktrans_mean': round(whole_putamen_Ktrans_mean, 4),
    'whole_putamen_Ktrans_median': round(whole_putamen_Ktrans_median, 4),
    'whole_putamen_Ktrans_std': round(whole_putamen_Ktrans_std, 4),
    'whole_pallidum_Ktrans_mean': round(whole_pallidum_Ktrans_mean, 4),
    'whole_pallidum_Ktrans_median': round(whole_pallidum_Ktrans_median, 4),
    'whole_pallidum_Ktrans_std': round(whole_pallidum_Ktrans_std, 4),
    'whole_thalamus_Ktrans_mean': round(whole_thalamus_Ktrans_mean, 4),
    'whole_thalamus_Ktrans_median': round(whole_thalamus_Ktrans_median, 4),
    'whole_thalamus_Ktrans_std': round(whole_thalamus_Ktrans_std, 4),
    'whole_caudate_Ktrans_mean': round(whole_caudate_Ktrans_mean, 4),
    'whole_caudate_Ktrans_median': round(whole_caudate_Ktrans_median, 4),
    'whole_caudate_Ktrans_std': round(whole_caudate_Ktrans_std, 4),
    'whole_amygdala_Ktrans_mean': round(whole_amygdala_Ktrans_mean, 4),
    'whole_amygdala_Ktrans_median': round(whole_amygdala_Ktrans_median, 4),
    'whole_amygdala_Ktrans_std': round(whole_amygdala_Ktrans_std, 4),
    'whole_entorhinal_cortex_Ktrans_mean': round(whole_entorhinal_cortex_Ktrans_mean, 4),
    'whole_entorhinal_cortex_Ktrans_median': round(whole_entorhinal_cortex_Ktrans_median, 4),
    'whole_entorhinal_cortex_Ktrans_std': round(whole_entorhinal_cortex_Ktrans_std, 4),
    'whole_fusiform_gyrus_cortex_Ktrans_mean': round(whole_fusiform_gyrus_cortex_Ktrans_mean, 4),
    'whole_fusiform_gyrus_cortex_Ktrans_median': round(whole_fusiform_gyrus_cortex_Ktrans_median, 4),
    'whole_fusiform_gyrus_cortex_Ktrans_std': round(whole_fusiform_gyrus_cortex_Ktrans_std, 4),
    'whole_fusiform_gyrus_WM_Ktrans_mean': round(whole_fusiform_gyrus_WM_Ktrans_mean, 4),
    'whole_fusiform_gyrus_WM_Ktrans_median': round(whole_fusiform_gyrus_WM_Ktrans_median, 4),
    'whole_fusiform_gyrus_WM_Ktrans_std': round(whole_fusiform_gyrus_WM_Ktrans_std, 4),
    'whole_insula_WM_Ktrans_mean': round(whole_insula_WM_Ktrans_mean, 4),
    'whole_insula_WM_Ktrans_median': round(whole_insula_WM_Ktrans_median, 4),
    'whole_insula_WM_Ktrans_std': round(whole_insula_WM_Ktrans_std, 4),
    'whole_superior_temporal_cortex_Ktrans_mean': round(whole_superior_temporal_cortex_Ktrans_mean, 4),
    'whole_superior_temporal_cortex_Ktrans_median': round(whole_superior_temporal_cortex_Ktrans_median, 4),
    'whole_superior_temporal_cortex_Ktrans_std': round(whole_superior_temporal_cortex_Ktrans_std, 4),
    'whole_inferior_temporal_cortex_Ktrans_mean': round(whole_inferior_temporal_cortex_Ktrans_mean, 4),
    'whole_inferior_temporal_cortex_Ktrans_median': round(whole_inferior_temporal_cortex_Ktrans_median, 4),
    'whole_inferior_temporal_cortex_Ktrans_std': round(whole_inferior_temporal_cortex_Ktrans_std, 4),
    'whole_posterior_cingulate_cortex_Ktrans_mean': round(whole_posterior_cingulate_cortex_Ktrans_mean, 4),
    'whole_posterior_cingulate_cortex_Ktrans_median': round(whole_posterior_cingulate_cortex_Ktrans_median, 4),
    'whole_posterior_cingulate_cortex_Ktrans_std': round(whole_posterior_cingulate_cortex_Ktrans_std, 4),
    'whole_medial_temporal_cortex_Ktrans_mean': round(whole_medial_temporal_cortex_Ktrans_mean, 4),
    'whole_medial_temporal_cortex_Ktrans_median': round(whole_medial_temporal_cortex_Ktrans_median, 4),
    'whole_medial_temporal_cortex_Ktrans_std': round(whole_medial_temporal_cortex_Ktrans_std, 4),
    'ktrans_wm_outliers': Ktrans_wm_outliers,
    'ktrans_gm_outliers': Ktrans_gm_outliers,
    'T1_blood_histogram': "../../" + T1_blood_histogram_path,
    'wm_histogram': "../../" + ktrans_wm_histogram_path,
    'gm_histogram': "../../" + ktrans_gm_histogram_path,
    'whole_hippo_outliers': whole_hippo_outliers,
    'whole_phg_outliers': whole_phg_outliers,
    'whole_putamen_outliers': whole_putamen_outliers,
    'whole_pallidum_outliers': whole_pallidum_outliers,
    'whole_thalamus_outliers': whole_thalamus_outliers,
    'whole_caudate_outliers': whole_caudate_outliers,
    'whole_amygdala_outliers': whole_amygdala_outliers,
    'whole_entorhinal_cortex_outliers': whole_entorhinal_cortex_outliers,
    'whole_fusiform_gyrus_cortex_outliers': whole_fusiform_gyrus_cortex_outliers,
    'whole_fusiform_gyrus_WM_outliers': whole_fusiform_gyrus_WM_outliers,
    'whole_insula_WM_outliers': whole_insula_WM_outliers,
    'whole_superior_temporal_cortex_outliers': whole_superior_temporal_cortex_outliers,
    'whole_inferior_temporal_cortex_outliers': whole_inferior_temporal_cortex_outliers,
    'whole_posterior_cingulate_cortex_outliers': whole_posterior_cingulate_cortex_outliers,
    'whole_medial_temporal_cortex_outliers': whole_medial_temporal_cortex_outliers,
    'Ktrans_whole_hippo_histogram': "../../" + Ktrans_whole_hippo_histogram_path,
    'Ktrans_whole_phg_histogram': "../../" + Ktrans_whole_phg_histogram_path,
    'Ktrans_whole_putamen_histogram': "../../" + Ktrans_whole_putamen_histogram_path,
    'Ktrans_whole_pallidum_histogram': "../../" + Ktrans_whole_pallidum_histogram_path,
    'Ktrans_whole_thalamus_histogram': "../../" + Ktrans_whole_thalamus_histogram_path,
    'Ktrans_whole_caudate_histogram': "../../" + Ktrans_whole_caudate_histogram_path,
    'Ktrans_whole_amygdala_histogram': "../../" + Ktrans_whole_amygdala_histogram_path,
    'Ktrans_whole_entorhinal_cortex_histogram': "../../" + Ktrans_whole_entorhinal_cortex_histogram_path,
    'Ktrans_whole_fusiform_gyrus_cortex_histogram': "../../" + Ktrans_whole_fusiform_gyrus_cortex_histogram_path,
    'Ktrans_whole_fusiform_gyrus_WM_histogram': "../../" + Ktrans_whole_fusiform_gyrus_WM_histogram_path,
    'Ktrans_whole_insula_WM_histogram': "../../" + Ktrans_whole_insula_WM_histogram_path,
    'Ktrans_whole_superior_temporal_cortex_histogram': "../../" + Ktrans_whole_superior_temporal_cortex_histogram_path,
    'Ktrans_whole_inferior_temporal_cortex_histogram': "../../" + Ktrans_whole_inferior_temporal_cortex_histogram_path,
    'Ktrans_whole_posterior_cingulate_cortex_histogram': "../../" + Ktrans_whole_posterior_cingulate_cortex_histogram_path,
    'Ktrans_whole_medial_temporal_cortex_histogram': "../../" + Ktrans_whole_medial_temporal_cortex_histogram_path
}

output = template.render(data)

data = {
    'Subjects' : subjects,
    # 'base_url': dceprep_dir,
    'Links': successful_links,
    'Failed_links': failed_links,
    'Cases': cases,
    'Failed_cases': failed_cases,
    'Flagged_cases': flagged_cases,
    'Combo': zip(successful_links, cases),
    'Failed_combo': zip(failed_links, failed_cases),
    'Motion_threshold': MOTION_THRESHOLD,
    'AIFitness_threshold': AIFITNESS_THRESHOLD,
    'Flagged_combo': zip(flagged_links, flagged_cases),
    'Subject_count': len(subjects),
    'Successes': str(len(population_data)) + '/' + str(len(total_timepoints)) + ' (' + str(round((len(population_data) / len(total_timepoints)) * 100, 2)) + '%)',
    'Excludes': str(len(population_data_exclude)) + '/' + str(len(total_timepoints)) + ' (' + str(round((len(population_data_exclude) / len(total_timepoints)) * 100, 2)) + '%)',
    'Date': date,
    'Commit': commit_hash,
    'ROCKETSHIP_commit': ROCKETSHIP_commit_hash,
    'Manufacturers': manufacturers_exclude,
    'Field_strengths': field_strengths_exclude,
    'Machines': machines,
    'Institutions': institutions_exclude,
    'pref_tr': pref_tr,
    'pref_fa': pref_fa,
    'pref_hematocrit': pref_hematocrit,
    'pref_SNR': pref_SNR,
    'pref_relaxivity': pref_relaxivity,
    'pref_t1blood': pref_t1blood,
    'pref_start_t': pref_start_t,
    'pref_end_t': pref_end_t,
    'pref_timeres': pref_timeres,
    'pref_model': DCE_model,
    'T1_wm_mean': round(T1_wm_mean_exclude, 4),
    'T1_wm_median': round(T1_wm_median_exclude, 4),
    'T1_wm_std': round(T1_wm_std_exclude, 4),
    'T1_wm_5th_percentile': round(T1_wm_5th_percentile_exclude, 4),
    'T1_wm_95th_percentile': round(T1_wm_95th_percentile_exclude, 4),
    'T1_gm_mean': round(T1_gm_mean_exclude, 4),
    'T1_gm_median': round(T1_gm_median_exclude, 4),
    'T1_gm_std': round(T1_gm_std_exclude, 4),
    'T1_gm_5th_percentile': round(T1_gm_5th_percentile_exclude, 4),
    'T1_gm_95th_percentile': round(T1_gm_95th_percentile_exclude, 4),
    'T1_blood_mean': round(T1_blood_mean_exclude, 4),
    'T1_blood_median': round(T1_blood_median_exclude, 4),
    'T1_blood_std': round(T1_blood_std_exclude, 4),
    'T1_blood_5th_percentile': round(T1_blood_5th_percentile_exclude, 4),
    'T1_blood_95th_percentile': round(T1_blood_95th_percentile_exclude, 4),
    'AIFitness_mean': round(AIFitness_exclude_mean, 4),
    'AIFitness_median': round(AIFitness_exclude_median, 4),
    'AIFitness_std': round(AIFitness_exclude_std, 4),
    'AIFitness_5th_percentile': round(AIFitness_exclude_5th_percentile, 4),
    'aif_mmol_mean': round(aif_mmol_mean_exclude, 4),
    'aif_mmol_median': round(aif_mmol_median_exclude, 4),
    'aif_mmol_std': round(aif_mmol_std_exclude, 4),
    'aif_mmol_5th_percentile': round(aif_mmol_5th_percentile_exclude, 4),
    'aif_mmol_95th_percentile': round(aif_mmol_95th_percentile_exclude, 4),
    'AIFitness_histogram' : "../../" + aifitness_histogram_exclude_path,
    'aif_mmol_histogram': "../../" + aif_mmol_histogram_exclude_path,
    'aif_pop_avg_AIF': "../../" + aif_pop_avg_path,
    'aif_curves': "../../" + aif_curves_path,
    'Ktrans_wm_mean': wm_mean_exclude,
    'Ktrans_wm_median': wm_median_exclude,
    'Ktrans_wm_std': wm_std_exclude,
    'Ktrans_gm_mean': gm_mean_exclude,
    'Ktrans_gm_median': gm_median_exclude,
    'Ktrans_gm_std': gm_std_exclude,
    'whole_hippo_Ktrans_mean': round(whole_hippo_Ktrans_mean_exclude, 4),
    'whole_hippo_Ktrans_median': round(whole_hippo_Ktrans_median_exclude, 4),
    'whole_hippo_Ktrans_std': round(whole_hippo_Ktrans_std_exclude, 4),
    'whole_phg_Ktrans_mean': round(whole_phg_Ktrans_mean_exclude, 4),
    'whole_phg_Ktrans_median': round(whole_phg_Ktrans_median_exclude, 4),
    'whole_phg_Ktrans_std': round(whole_phg_Ktrans_std_exclude, 4),
    'whole_putamen_Ktrans_mean': round(whole_putamen_Ktrans_mean_exclude, 4),
    'whole_putamen_Ktrans_median': round(whole_putamen_Ktrans_median_exclude, 4),
    'whole_putamen_Ktrans_std': round(whole_putamen_Ktrans_std_exclude, 4),
    'whole_pallidum_Ktrans_mean': round(whole_pallidum_Ktrans_mean_exclude, 4),
    'whole_pallidum_Ktrans_median': round(whole_pallidum_Ktrans_median_exclude, 4),
    'whole_pallidum_Ktrans_std': round(whole_pallidum_Ktrans_std_exclude, 4),
    'whole_thalamus_Ktrans_mean': round(whole_thalamus_Ktrans_mean_exclude, 4),
    'whole_thalamus_Ktrans_median': round(whole_thalamus_Ktrans_median_exclude, 4),
    'whole_thalamus_Ktrans_std': round(whole_thalamus_Ktrans_std_exclude, 4),
    'whole_caudate_Ktrans_mean': round(whole_caudate_Ktrans_mean_exclude, 4),
    'whole_caudate_Ktrans_median': round(whole_caudate_Ktrans_median_exclude, 4),
    'whole_caudate_Ktrans_std': round(whole_caudate_Ktrans_std_exclude, 4),
    'whole_amygdala_Ktrans_mean': round(whole_amygdala_Ktrans_mean_exclude, 4),
    'whole_amygdala_Ktrans_median': round(whole_amygdala_Ktrans_median_exclude, 4),
    'whole_amygdala_Ktrans_std': round(whole_amygdala_Ktrans_std_exclude, 4),
    'whole_entorhinal_cortex_Ktrans_mean': round(whole_entorhinal_cortex_Ktrans_mean_exclude, 4),
    'whole_entorhinal_cortex_Ktrans_median': round(whole_entorhinal_cortex_Ktrans_median_exclude, 4),
    'whole_entorhinal_cortex_Ktrans_std': round(whole_entorhinal_cortex_Ktrans_std_exclude, 4),
    'whole_fusiform_gyrus_cortex_Ktrans_mean': round(whole_fusiform_gyrus_cortex_Ktrans_mean_exclude, 4),
    'whole_fusiform_gyrus_cortex_Ktrans_median': round(whole_fusiform_gyrus_cortex_Ktrans_median_exclude, 4),
    'whole_fusiform_gyrus_cortex_Ktrans_std': round(whole_fusiform_gyrus_cortex_Ktrans_std_exclude, 4),
    'whole_fusiform_gyrus_WM_Ktrans_mean': round(whole_fusiform_gyrus_WM_Ktrans_mean_exclude, 4),
    'whole_fusiform_gyrus_WM_Ktrans_median': round(whole_fusiform_gyrus_WM_Ktrans_median_exclude, 4),
    'whole_fusiform_gyrus_WM_Ktrans_std': round(whole_fusiform_gyrus_WM_Ktrans_std_exclude, 4),
    'whole_insula_WM_Ktrans_mean': round(whole_insula_WM_Ktrans_mean_exclude, 4),
    'whole_insula_WM_Ktrans_median': round(whole_insula_WM_Ktrans_median_exclude, 4),
    'whole_insula_WM_Ktrans_std': round(whole_insula_WM_Ktrans_std_exclude, 4),
    'whole_superior_temporal_cortex_Ktrans_mean': round(whole_superior_temporal_cortex_Ktrans_mean_exclude, 4),
    'whole_superior_temporal_cortex_Ktrans_median': round(whole_superior_temporal_cortex_Ktrans_median_exclude, 4),
    'whole_superior_temporal_cortex_Ktrans_std': round(whole_superior_temporal_cortex_Ktrans_std_exclude, 4),
    'whole_inferior_temporal_cortex_Ktrans_mean': round(whole_inferior_temporal_cortex_Ktrans_mean_exclude, 4),
    'whole_inferior_temporal_cortex_Ktrans_median': round(whole_inferior_temporal_cortex_Ktrans_median_exclude, 4),
    'whole_inferior_temporal_cortex_Ktrans_std': round(whole_inferior_temporal_cortex_Ktrans_std_exclude, 4),
    'whole_posterior_cingulate_cortex_Ktrans_mean': round(whole_posterior_cingulate_cortex_Ktrans_mean_exclude, 4),
    'whole_posterior_cingulate_cortex_Ktrans_median': round(whole_posterior_cingulate_cortex_Ktrans_median_exclude, 4),
    'whole_posterior_cingulate_cortex_Ktrans_std': round(whole_posterior_cingulate_cortex_Ktrans_std_exclude, 4),
    'whole_medial_temporal_cortex_Ktrans_mean': round(whole_medial_temporal_cortex_Ktrans_mean_exclude, 4),
    'whole_medial_temporal_cortex_Ktrans_median': round(whole_medial_temporal_cortex_Ktrans_median_exclude, 4),
    'whole_medial_temporal_cortex_Ktrans_std': round(whole_medial_temporal_cortex_Ktrans_std_exclude, 4),
    'ktrans_wm_outliers': Ktrans_wm_outliers,
    'ktrans_gm_outliers': Ktrans_gm_outliers,
    'T1_blood_histogram': "../../" + T1_blood_histogram_exclude_path,
    'wm_histogram': "../../" + ktrans_wm_histogram_exclude_path,
    'gm_histogram': "../../" + ktrans_gm_histogram_exclude_path,
    'whole_hippo_outliers': whole_hippo_outliers,
    'whole_phg_outliers': whole_phg_outliers,
    'whole_putamen_outliers': whole_putamen_outliers,
    'whole_pallidum_outliers': whole_pallidum_outliers,
    'whole_thalamus_outliers': whole_thalamus_outliers,
    'whole_caudate_outliers': whole_caudate_outliers,
    'whole_amygdala_outliers': whole_amygdala_outliers,
    'whole_entorhinal_cortex_outliers': whole_entorhinal_cortex_outliers,
    'whole_fusiform_gyrus_cortex_outliers': whole_fusiform_gyrus_cortex_outliers,
    'whole_fusiform_gyrus_WM_outliers': whole_fusiform_gyrus_WM_outliers,
    'whole_insula_WM_outliers': whole_insula_WM_outliers,
    'whole_superior_temporal_cortex_outliers': whole_superior_temporal_cortex_outliers,
    'whole_inferior_temporal_cortex_outliers': whole_inferior_temporal_cortex_outliers,
    'whole_posterior_cingulate_cortex_outliers': whole_posterior_cingulate_cortex_outliers,
    'whole_medial_temporal_cortex_outliers': whole_medial_temporal_cortex_outliers,
    'Ktrans_whole_hippo_histogram': "../../" + whole_hippo_histogram_exclude_path,
    'Ktrans_whole_phg_histogram': "../../" + whole_phg_histogram_exclude_path,
    'Ktrans_whole_putamen_histogram': "../../" + whole_putamen_histogram_exclude_path,
    'Ktrans_whole_pallidum_histogram': "../../" + whole_pallidum_histogram_exclude_path,
    'Ktrans_whole_thalamus_histogram': "../../" + whole_thalamus_histogram_exclude_path,
    'Ktrans_whole_caudate_histogram': "../../" + whole_caudate_histogram_exclude_path,
    'Ktrans_whole_amygdala_histogram': "../../" + whole_amygdala_histogram_exclude_path,
    'Ktrans_whole_entorhinal_cortex_histogram': "../../" + whole_entorhinal_cortex_histogram_exclude_path,
    'Ktrans_whole_fusiform_gyrus_cortex_histogram': "../../" + whole_fusiform_gyrus_cortex_histogram_exclude_path,
    'Ktrans_whole_fusiform_gyrus_WM_histogram': "../../" + whole_fusiform_gyrus_WM_histogram_exclude_path,
    'Ktrans_whole_insula_WM_histogram': "../../" + whole_insula_WM_histogram_exclude_path,
    'Ktrans_whole_superior_temporal_cortex_histogram': "../../" + whole_superior_temporal_cortex_histogram_exclude_path,
    'Ktrans_whole_inferior_temporal_cortex_histogram': "../../" + whole_inferior_temporal_cortex_histogram_exclude_path,
    'Ktrans_whole_posterior_cingulate_cortex_histogram': "../../" + whole_posterior_cingulate_cortex_histogram_exclude_path,
    'Ktrans_whole_medial_temporal_cortex_histogram': "../../" + whole_medial_temporal_cortex_histogram_exclude_path
}

output_exclude = template.render(data)

# make reports directory if it doesn't exist
if not os.path.exists(dir + '/reports'):
    os.makedirs(dir + '/reports')

run_folder = output_dir[1:]
# make output_dir directory if it doesn't exist
if not os.path.exists(dir + '/reports/' + run_folder):
    os.makedirs(dir + '/reports/' + run_folder)

# write html to file
with open(dir + '/reports/' + run_folder + '/population_report' + output_dir + "_" + date_filename + '.html', 'w') as f:
    f.write(output)

with open(dir + '/reports/' + run_folder + '/population_report_exclude' + output_dir + "_" + date_filename + '.html', 'w') as f:
    f.write(output_exclude)

print('Report generated in ' + dir + '/reports/' + run_folder + '/population_report' + output_dir + "_" + date_filename + '.html')
print('Excluded report generated in ' + dir + '/reports/' + run_folder + '/population_report_exclude' + output_dir + "_" + date_filename + '.html')

if os.path.exists(os.path.join(dir, '../dce_available_3524_ac.xlsx')):
    # add apoe and cdr fields to population_data
    df = pd.read_excel(os.path.join(dir, '../dce_available_3524_ac.xlsx'), sheet_name="main")

    # get apoe and cdr values for each subject
    for subject in population_data.keys():
        # get subject's ID
        subject_id = subject.split("_")[0]
        subject_id = subject_id.split("-")[1]
        # get subject's timepoint
        timepoint = subject.split("_")[1]
        # get subject's apoe and cdr values
        if subject_id.startswith("4") or subject_id.startswith("3"):
            # insert underscore after 1st character
            subject_id = subject_id[:1] + "_" + subject_id[1:]
        try:
            if int(subject_id) in df['Subject_ID'].values:
                apoe = df.loc[df['Subject_ID'] == int(subject_id), 'APOE'].values[0]
                # cdr = df.loc[df['Subject_ID'] == int(subject_id), 'CDR'].values[0]
                # bmi = df.loc[df['Subject_ID'] == int(subject_id), 'BMI'].values[0]
            else:
                apoe = "N/A"
                cdr = "N/A"
                bmi = "N/A"
            # add to population_data
        except Exception as e:
            print(e)
            # print("Subject " + subject_id + " not found in dce_available_3524_ac.xlsx")
            apoe = "N/A"
            cdr = "N/A"
            bmi = "N/A"
        population_data[subject]["APOE"] = apoe
        # population_data[subject]["CDR"] = cdr
        # population_data[subject]["BMI"] = bmi

    for subject in population_data_exclude.keys():
        # get subject's ID
        subject_id = subject.split("_")[0]
        subject_id = subject_id.split("-")[1]
        # get subject's timepoint
        timepoint = subject.split("_")[1]
        # get subject's apoe and cdr values
        if subject_id.startswith("4") or subject_id.startswith("3"):
            # insert underscore after 1st character
            subject_id = subject_id[:1] + "_" + subject_id[1:]
        try:
            apoe = df.loc[df['Subject_ID'] == int(subject_id), 'APOE'].values[0]
            # cdr = df.loc[df['Subject_ID'] == int(subject_id), 'CDR'].values[0]
            # bmi = df.loc[df['Subject_ID'] == int(subject_id), 'BMI'].values[0]
            # add to population_data
        except Exception as e:
            print(e)
            print("Subject " + subject_id + " not found in dce_available_3524_ac.xlsx")
            apoe = "N/A"
            cdr = "N/A"
            bmi = "N/A"
        population_data_exclude[subject]["APOE"] = apoe
        # population_data_exclude[subject]["CDR"] = cdr
        # population_data_exclude[subject]["BMI"] = bmi

    # for subject in population_data_exclude_signa.keys():
    #     # get subject's ID
    #     subject_id = subject.split("_")[0]
    #     subject_id = subject_id.split("-")[1]
    #     # get subject's timepoint
    #     timepoint = subject.split("_")[1]
    #     # get subject's apoe and cdr values
    #     if subject_id.startswith("4") or subject_id.startswith("3"):
    #         # insert underscore after 1st character
    #         subject_id = subject_id[:1] + "_" + subject_id[1:]
    #     try:
    #         apoe = df.loc[df['Subject_ID'] == int(subject_id), 'APOE'].values[0]
    #         cdr = df.loc[df['Subject_ID'] == int(subject_id), 'CDR'].values[0]
    #         bmi = df.loc[df['Subject_ID'] == int(subject_id), 'BMI'].values[0]
    #         # add to population_data
    #     except Exception as e:
    #         print(e)
    #         print("Subject " + subject_id + " not found in dce_available_3524_ac.xlsx")
    #         apoe = "N/A"
    #         cdr = "N/A"
    #         bmi = "N/A"
    #     population_data_exclude_signa[subject]["APOE"] = apoe
    #     population_data_exclude_signa[subject]["CDR"] = cdr
    #     population_data_exclude_signa[subject]["BMI"] = bmi

    for subject in population_data_failed.keys():
        # get subject's ID
        subject_id = subject.split("_")[0]
        subject_id = subject_id.split("-")[1]
        # get subject's timepoint
        timepoint = subject.split("_")[1]
        # get subject's apoe and cdr values
        if subject_id.startswith("4") or subject_id.startswith("3"):
            # insert underscore after 1st character
            subject_id = subject_id[:1] + "_" + subject_id[1:]
        try:
            apoe = df.loc[df['Subject_ID'] == int(subject_id), 'APOE'].values[0]
            # cdr = df.loc[df['Subject_ID'] == int(subject_id), 'CDR'].values[0]
            # bmi = df.loc[df['Subject_ID'] == int(subject_id), 'BMI'].values[0]
            # add to population_data
        except Exception as e:
            print(e)
            print("Subject " + subject_id + " not found in dce_available_3524_ac.xlsx")
            apoe = "N/A"
            cdr = "N/A"
            bmi = "N/A"
        population_data_failed[subject]["APOE"] = apoe
        # population_data_failed[subject]["CDR"] = cdr
        # population_data_failed[subject]["BMI"] = bmi

    # read EXCLUDED sheet from dce_available_3524_ac.xlsx and move subjects to population_data_exclude
    df = pd.read_excel(os.path.join(dir, '../dce_available_3524_ac.xlsx'), sheet_name="EXCLUDED")
    # get subject ID and timepoint (first and second columns)
    subjects_excluded = df['Subject_ID']
    timepoints_excluded = df['Timepoint']
    # get exclusion reasons (third column)
    exclusion_reasons = df['REASON']
    dates_excluded = df['Study_Date']
    # if excluded subject is in population_data, move to population_data_exclude
    for subject, timepoint, exclusion_reason in zip(subjects_excluded, timepoints_excluded, exclusion_reasons):
        # skip if reason includes "aliasing"
        if "aliasing" in exclusion_reason.lower():
            continue
        if "no t1w" in exclusion_reason.lower():
            continue
        if "t1w only" in exclusion_reason.lower():
            continue
        if "no fas" in exclusion_reason.lower():
            continue
        # get subject's ID
        subject_id = subject
        # get subject's timepoint
        # if NaN, set to 1
        if pd.isnull(timepoint):
            timepoint = 1
        timepoint = int(timepoint)
        entry = f"{subject_id}_ses-0{timepoint}"
        if entry in population_data.keys():
            # move to population_data_exclude
            population_data_exclude[entry] = population_data.pop(entry)
            # add exclusion reason if not already there
            if "Reason" not in population_data_exclude[entry].keys():
                population_data_exclude[entry]["Reason"] = exclusion_reason
            else:
                population_data_exclude[entry]["Reason"] += ", " + exclusion_reason
            # add date
            # population_data_exclude[entry]["Date"] = dates_excluded[subjects_excluded == subject].values[0]
            # remove from population_data
            # del population_data[entry]
        elif entry not in population_data.keys() and entry not in population_data_failed.keys() and entry not in population_data_exclude.keys():# and entry not in population_data_exclude_signa.keys():
            # read whole row from dce_available_3524_ac.xlsx
            row = df.loc[df['Subject_ID'] == subject_id]
            population_data_exclude[entry] = {}
            population_data_exclude[entry]["Reason"] = exclusion_reason
            population_data_exclude[entry]["Timepoint"] = row['Timepoint'].values[0]
            population_data_exclude[entry]["APOE"] = row['APOE'].values[0]
            population_data_exclude[entry]["Sex"] = row['Sex'].values[0]
            population_data_exclude[entry]["Age"] = row['Age'].values[0]
            population_data_exclude[entry]["Date"] = row['Study_Date'].values[0]
            # population_data_exclude[entry]["CDR"] = row['CDR'].values[0]
            # population_data_exclude[entry]["BMI"] = row['BMI'].values[0]
            # Fill rest of fields with default values
            # fields = [
            #     "Machine", "Institution", "Coil", "TR", "Time_resolution", "TE", "Flip_angle", "n_reps",
            #     "Approximate SNR", "AIFitness", "aif_fitted_r2", "manual_aif_status", "max_disp", "T1_blood", "T1_wm_median", "T1_gm_median",
            #     "Ktrans_wm_median", "Ktrans_gm_median", "Ktrans_Hippo_median", "Ktrans_PhG_median", "Ktrans_Putamen_median", "Ktrans_Pallidum_median",
            #     "Ktrans_Thalamus_median", "Ktrans_Caudate_median", "Ktrans_Amygdala_median", "Ktrans_Entorhinal_cortex_median",
            #     "Ktrans_Fusiform_gyrus_cortex_median", "Ktrans_Fusiform_gyrus_WM_median", "Ktrans_Insula_WM_median",
            #     "Ktrans_Superior_temporal_cortex_median", "Ktrans_Inferior_temporal_cortex_median", "Ktrans_Posterior_cingulate_cortex_median", "Ktrans_Medial_temporal_cortex_median",
            #     "Vp_Hippo_median", "Vp_PhG_median", "Vp_Putamen_median", "Vp_Pallidum_median", "Vp_Thalamus_median",
            #     "Vp_Caudate_median", "Vp_Amygdala_median", "Vp_Entorhinal_cortex_median", "Vp_Fusiform_gyrus_cortex_median",
            #     "Vp_Fusiform_gyrus_WM_median", "Vp_Insula_WM_median", "Vp_Superior_temporal_cortex_median",
            #     "Vp_Inferior_temporal_cortex_median", "Vp_Posterior_cingulate_cortex_median", "Vp_Medial_temporal_cortex_median",
            #     "hippo_vol", "phg_vol", "putamen_vol", "pallidum_vol", "thalamus_vol", "caudate_vol", "amygdala_vol",
            #     "entorhinal_cortex_vol", "fusiform_gyrus_cortex_vol", "fusiform_gyrus_wm_vol", "insula_wm_vol",
            #     "superior_temporal_cortex_vol", "inferior_temporal_cortex_vol", "posterior_cingulate_cortex_vol", "medial_temporal_cortex_vol",
            #     "bankssts_thickness_avg", "bankssts_thickness_std", "caudalanteriorcingulate_thickness_avg", "caudalanteriorcingulate_thickness_std",
            #     "caudalmiddlefrontal_thickness_avg", "caudalmiddlefrontal_thickness_std", "cuneus_thickness_avg", "cuneus_thickness_std",
            #     "entorhinal_thickness_avg", "entorhinal_thickness_std", "fusiform_thickness_avg", "fusiform_thickness_std",
            #     "inferiorparietal_thickness_avg", "inferiorparietal_thickness_std", "inferiortemporal_thickness_avg", "inferiortemporal_thickness_std",
            #     "isthmuscingulate_thickness_avg", "isthmuscingulate_thickness_std", "lateraloccipital_thickness_avg", "lateraloccipital_thickness_std",
            #     "lateralorbitofrontal_thickness_avg", "lateralorbitofrontal_thickness_std", "lingual_thickness_avg", "lingual_thickness_std",
            #     "medialorbitofrontal_thickness_avg", "medialorbitofrontal_thickness_std", "middletemporal_thickness_avg", "middletemporal_thickness_std",
            #     "parahippocampal_thickness_avg", "parahippocampal_thickness_std", "paracentral_thickness_avg", "paracentral_thickness_std",
            #     "parsopercularis_thickness_avg", "parsopercularis_thickness_std", "parsorbitalis_thickness_avg", "parsorbitalis_thickness_std",
            #     "parstriangularis_thickness_avg", "parstriangularis_thickness_std", "pericalcarine_thickness_avg", "pericalcarine_thickness_std",
            #     "postcentral_thickness_avg", "postcentral_thickness_std", "posteriorcingulate_thickness_avg", "posteriorcingulate_thickness_std",
            #     "precentral_thickness_avg", "precentral_thickness_std", "precuneus_thickness_avg", "precuneus_thickness_std",
            #     "rostralanteriorcingulate_thickness_avg", "rostralanteriorcingulate_thickness_std", "rostralmiddlefrontal_thickness_avg",
            #     "rostralmiddlefrontal_thickness_std", "superiorfrontal_thickness_avg", "superiorfrontal_thickness_std",
            #     "superiorparietal_thickness_avg", "superiorparietal_thickness_std", "superiortemporal_thickness_avg", "superiortemporal_thickness_std",
            #     "supramarginal_thickness_avg", "supramarginal_thickness_std", "frontalpole_thickness_avg", "frontalpole_thickness_std",
            #     "temporalpole_thickness_avg", "temporalpole_thickness_std", "transversetemporal_thickness_avg", "transversetemporal_thickness_std",
            #     "insula_thickness_avg", "insula_thickness_std"
            # ]
            # for field in fields:
            #     if field not in population_data_exclude[entry]:
            #         population_data_exclude[entry][field] = -1

# make excel file
if not os.path.exists(os.path.join(dir, "spreadsheets", output_dir[1:])):
    os.makedirs(os.path.join(dir, "spreadsheets", output_dir[1:]))
writer = pd.ExcelWriter(
    os.path.join(dir, "spreadsheets", output_dir[1:], "dataset_ktrans" + output_dir + "_" + date_filename + ".xlsx"),
    date_format='YYYY/MM/DD',
    datetime_format='YYYY/MM/DD',
    engine='xlsxwriter'
)
# make dataframe
df_success = pd.DataFrame(population_data)
# df_exclude = pd.DataFrame(population_data_exclude)

order = ["Date", "APOE", "Sex", "Age", "Machine", "Institution", "Coil", "TR", "Time_resolution", "TE", "Flip_angle", "n_reps",
        "Approximate SNR", "AIFitness", "aif_fitted_r2", "manual_aif_status", "max_disp", "T1_blood", "T1_wm_median", "T1_gm_median",
        "Ktrans_wm_median", "Ktrans_gm_median", "Ktrans_Hippo_median", "Ktrans_PhG_median", "Ktrans_Putamen_median", "Ktrans_Pallidum_median",
        "Ktrans_Thalamus_median", "Ktrans_Caudate_median", "Ktrans_Amygdala_median", "Ktrans_Entorhinal_cortex_median",
        "Ktrans_Fusiform_gyrus_cortex_median", "Ktrans_Fusiform_gyrus_WM_median", "Ktrans_Insula_WM_median",
        "Ktrans_Superior_temporal_cortex_median", "Ktrans_Inferior_temporal_cortex_median", "Ktrans_Posterior_cingulate_cortex_median", "Ktrans_Medial_temporal_cortex_median",
        "Vp_Hippo_median", "Vp_PhG_median", "Vp_Putamen_median", "Vp_Pallidum_median", "Vp_Thalamus_median",
        "Vp_Caudate_median", "Vp_Amygdala_median", "Vp_Entorhinal_cortex_median", "Vp_Fusiform_gyrus_cortex_median",
        "Vp_Fusiform_gyrus_WM_median", "Vp_Insula_WM_median", "Vp_Superior_temporal_cortex_median",
        "Vp_Inferior_temporal_cortex_median", "Vp_Posterior_cingulate_cortex_median", "Vp_Medial_temporal_cortex_median",
        "hippo_vol", "phg_vol", "putamen_vol", "pallidum_vol", "thalamus_vol", "caudate_vol", "amygdala_vol",
        "entorhinal_cortex_vol", "fusiform_gyrus_cortex_vol", "fusiform_gyrus_wm_vol", "insula_wm_vol",
        "superior_temporal_cortex_vol", "inferior_temporal_cortex_vol", "posterior_cingulate_cortex_vol", "medial_temporal_cortex_vol",
        "bankssts_thickness_avg", "bankssts_thickness_std", "caudalanteriorcingulate_thickness_avg", "caudalanteriorcingulate_thickness_std",
        "caudalmiddlefrontal_thickness_avg", "caudalmiddlefrontal_thickness_std", "cuneus_thickness_avg", "cuneus_thickness_std",
        "entorhinal_thickness_avg", "entorhinal_thickness_std", "fusiform_thickness_avg", "fusiform_thickness_std",
        "inferiorparietal_thickness_avg", "inferiorparietal_thickness_std", "inferiortemporal_thickness_avg", "inferiortemporal_thickness_std",
        "isthmuscingulate_thickness_avg", "isthmuscingulate_thickness_std", "lateraloccipital_thickness_avg", "lateraloccipital_thickness_std",
        "lateralorbitofrontal_thickness_avg", "lateralorbitofrontal_thickness_std", "lingual_thickness_avg", "lingual_thickness_std",
        "medialorbitofrontal_thickness_avg", "medialorbitofrontal_thickness_std", "middletemporal_thickness_avg", "middletemporal_thickness_std",
        "parahippocampal_thickness_avg", "parahippocampal_thickness_std", "paracentral_thickness_avg", "paracentral_thickness_std",
        "parsopercularis_thickness_avg", "parsopercularis_thickness_std", "parsorbitalis_thickness_avg", "parsorbitalis_thickness_std",
        "parstriangularis_thickness_avg", "parstriangularis_thickness_std", "pericalcarine_thickness_avg", "pericalcarine_thickness_std",
        "postcentral_thickness_avg", "postcentral_thickness_std", "posteriorcingulate_thickness_avg", "posteriorcingulate_thickness_std",
        "precentral_thickness_avg", "precentral_thickness_std", "precuneus_thickness_avg", "precuneus_thickness_std",
        "rostralanteriorcingulate_thickness_avg", "rostralanteriorcingulate_thickness_std", "rostralmiddlefrontal_thickness_avg",
        "rostralmiddlefrontal_thickness_std", "superiorfrontal_thickness_avg", "superiorfrontal_thickness_std",
        "superiorparietal_thickness_avg", "superiorparietal_thickness_std", "superiortemporal_thickness_avg", "superiortemporal_thickness_std",
        "supramarginal_thickness_avg", "supramarginal_thickness_std", "frontalpole_thickness_avg", "frontalpole_thickness_std",
        "temporalpole_thickness_avg", "temporalpole_thickness_std", "transversetemporal_thickness_avg", "transversetemporal_thickness_std",
        "insula_thickness_avg", "insula_thickness_std"]

df_success = df_success.T
df_success = df_success[order]


order_exclude = order.copy()
order_exclude.insert(0, "Reason")

# name first column
df_success.index.name = "Subject_ID"

# write to excel
df_success.to_excel(writer, sheet_name='Success')
cell_format = writer.book.add_format()
cell_format.set_text_wrap()
cell_format.set_align('center')
cell_format.set_align('vcenter')
index_cell_format = writer.book.add_format()
index_cell_format.set_text_wrap()
index_cell_format.set_align('center')
index_cell_format.set_align('vcenter')
# unbold index
index_cell_format.set_bold(False)
if len(population_data_exclude) > 0:
    df_exclude = pd.DataFrame(population_data_exclude)
    df_exclude = df_exclude.T
    df_exclude = df_exclude[order_exclude]
    df_exclude.index.name = "Subject_ID"
    df_exclude.to_excel(writer, sheet_name='Pre-Exclude')
    for column in df_exclude.columns:
        max_length = df_exclude[column].map(str).map(len).max()
        max_length = max(max_length, len(column))
        if column == "Date":
            writer.sheets['Pre-Exclude'].set_column(df_exclude.columns.get_loc(column)+1, df_exclude.columns.get_loc(column)+1, 10, cell_format)
        else:
            writer.sheets['Pre-Exclude'].set_column(df_exclude.columns.get_loc(column)+1, df_exclude.columns.get_loc(column)+1, max_length+2, cell_format)

    writer.sheets['Pre-Exclude'].set_column(0, 0, 20, index_cell_format)
    writer.sheets['Pre-Exclude'].autofilter(0, 0, len(df_exclude), len(df_exclude.columns))

if len(population_data_failed) > 0:
    df_fail = pd.DataFrame(population_data_failed)
    df_fail = df_fail.T
    df_fail = df_fail[order_exclude]
    df_fail.index.name = "Subject_ID"
    df_fail.to_excel(writer, sheet_name='Fail')

if len(population_data_missing) > 0:
    df_missing = pd.DataFrame(population_data_missing)
    df_missing = df_missing.T
    df_missing.index.name = "Subject_ID"
    df_missing.to_excel(writer, sheet_name='Missing')

# if len(population_data_exclude_signa) > 0:
#     df_exclude_signa = pd.DataFrame(population_data_exclude_signa)
#     df_exclude_signa = df_exclude_signa.T
#     df_exclude_signa = df_exclude_signa[order_exclude]
#     df_exclude_signa.index.name = "Subject_ID"
#     df_exclude_signa.to_excel(writer, sheet_name='Crazy GE Data')

for column in df_success.columns:
    max_length = df_success[column].map(str).map(len).max()
    max_length = max(max_length, len(column))
    if column == "Date":
        writer.sheets['Success'].set_column(df_success.columns.get_loc(column)+1, df_success.columns.get_loc(column)+1, 10, cell_format)
    else:
        writer.sheets['Success'].set_column(df_success.columns.get_loc(column)+1, df_success.columns.get_loc(column)+1, max_length+2, cell_format)

writer.sheets['Success'].set_column(0, 0, 20, index_cell_format)
# autofilter
writer.sheets['Success'].autofilter(0, 0, len(df_success), len(df_success.columns))
# change date column data format to MM/DD/YYYY
writer.close()

# now backfill each subject's placement in the population
imgs = []
imgs_exclude = []
for subject_id in subjects:
# for subject_id, timepoint in zip(subjects, timepoints):
    # list _timepoint directories in subject directory
    for timepoint in subject_timepoints[subject_id]:
        if timepoint.startswith("ses-"):
            placement_wm_histogram_path = os.path.join(dceprep_dir, subject_id, timepoint, "figures/placement_wm_histogram.png")
            placement_gm_histogram_path = os.path.join(dceprep_dir, subject_id, timepoint, "figures/placement_gm_histogram.png")
            # get subject's Ktrans_wm_mean
            try:
                if f"{subject_id}_{timepoint}" in population_data.keys():
                    case_wm_median = population_data[subject_id + "_" + timepoint]["Ktrans_wm_median"]
                    case_gm_median = population_data[subject_id + "_" + timepoint]["Ktrans_gm_median"]
                elif f"{subject_id}_{timepoint}" in population_data_exclude.keys():
                    case_wm_median = population_data_exclude[subject_id + "_" + timepoint]["Ktrans_wm_median"]
                    case_gm_median = population_data_exclude[subject_id + "_" + timepoint]["Ktrans_gm_median"]
                # elif f"{subject_id}_{timepoint}" in population_data_exclude_signa.keys():
                #     case_wm_median = population_data_exclude_signa[subject_id + "_" + timepoint]["Ktrans_wm_median"]
                #     case_gm_median = population_data_exclude_signa[subject_id + "_" + timepoint]["Ktrans_gm_median"]
                elif f"{subject_id}_{timepoint}" in population_data_failed.keys():
                    case_wm_median = population_data_failed[subject_id + "_" + timepoint]["Ktrans_wm_median"]
                    case_gm_median = population_data_failed[subject_id + "_" + timepoint]["Ktrans_gm_median"]
                else:
                    case_wm_median = -1
                    case_gm_median = -1
            except Exception as e:
                print(f"Error getting {subject_id} {timepoint} wm or gm median.")
                print(e)
                continue

            if os.path.exists(placement_wm_histogram_path) and os.path.exists(placement_gm_histogram_path):
                # plot histograms
                plt.hist(wm_histogram, bins=30)
                plt.title("Ktrans White Matter Median")
                plt.xlabel("Ktrans (10^-3/min)")
                plt.axvline(x=case_wm_median, color='black')
                # put percentile text in top right corner
                plt.text(0.9, 0.95, "Percentile: " + str(round((len([x for x in wm_histogram if x < case_wm_median]) / len(wm_histogram)) * 100, 2)) + "%", horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
                plt.savefig(placement_wm_histogram_path, bbox_inches='tight')
                plt.close()

                plt.hist(gm_histogram, bins=30)
                plt.title("Ktrans Gray Matter Median")
                plt.xlabel("Ktrans (10^-3/min)")
                plt.axvline(x=case_gm_median, color='black')
                # put percentile text in top right corner
                plt.text(0.9, 0.95, "Percentile: " + str(round((len([x for x in gm_histogram if x < case_gm_median]) / len(gm_histogram)) * 100, 2)) + "%", horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
                plt.savefig(placement_gm_histogram_path, bbox_inches='tight')
                plt.close()
            
            # append to html file
            try:
                filename = os.path.join(dceprep_dir, subject_id, timepoint, f"reports/{subject_id}_{timepoint}_desc-casereport.html")
                if os.path.exists(filename):
                    with open(filename, "r") as f:
                        report_content = f.read()

                    # replace placeholder with histogram path
                    report_content = report_content.replace("placeholder_wm", "../../figures/placement_wm_histogram.png")
                    report_content = report_content.replace("placeholder_gm", "../../figures/placement_gm_histogram.png")
                    # write html to file
                    with open(filename, 'w') as f:
                        f.write(report_content)

                    report_path = os.path.join(dceprep_dir, subject_id, timepoint, f"reports/{subject_id}_{timepoint}_desc-report.png")

                    if f"{subject_id}_{timepoint}" in population_data.keys():
                        imgs.append(report_path)
                    elif f"{subject_id}_{timepoint}" in population_data_exclude.keys():
                        imgs_exclude.append(report_path)
            except Exception as e:
                print(f"Error appending {subject_id} {timepoint} placement histograms.")
                print(e)

# make scrollable report
# Function to add images to PDF
def add_image_to_pdf(pdf, image_path):
    pdf.drawImage(image_path, 50, 50, width=letter[0]-85, height=letter[1]-50)  # Adjust coordinates and dimensions as needed
    pdf.showPage()

# Create a PDF canvas
pdf_file = f"{dir}/reports/EZQCreport" + output_dir + "_" + date_filename + ".pdf"
pdf = canvas.Canvas(pdf_file, pagesize=letter)

# Add images to the PDF
for report in imgs:
    try:
        add_image_to_pdf(pdf, report)
    except Exception as e:
        print(f"Error adding {report} to PDF.")
        print(e)

# Save the PDF to dir/reports
pdf.save()

pdf_file = f"{dir}/reports/EZQCreport_exclude" + output_dir + "_" + date_filename + ".pdf"
pdf = canvas.Canvas(pdf_file, pagesize=letter)

# Add images to the PDF
for report in imgs_exclude:
    try:
        add_image_to_pdf(pdf, report)
    except Exception as e:
        print(f"Error adding {report} to PDF.")
        print(e)

pdf.save()
