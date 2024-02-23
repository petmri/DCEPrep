import jinja2
import os
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
import datetime
import subprocess
from sys import argv

dir = argv[1]
try:
    output_dir = argv[2]
except:
    output_dir = ""

try:
    ROCKETSHIP_dir = argv[3]
except IndexError:
    ROCKETSHIP_dir = argv[2]
    output_dir = ""

# Load MRI population data dict with keys as subject IDs and values as gm and wm data
population_data = {}
# list directories in dir
dir_list = os.listdir(dir)
# filter out non-directories
subjects = [subject for subject in dir_list if os.path.isdir(os.path.join(dir, subject)) and not subject.startswith("figures") and not subject.startswith("logs")]
subjects.sort()
# go into each subject directory and count number of successful_timepoints
# for subject_id in subjects:
#     # list _timepoint directories in subject directory
#     for timepoint in os.listdir(os.path.join(dir, subject_id)):
#         if timepoint.endswith("_timepoint"):
#             successful_timepoints.append(subject_id + '/' + timepoint)

KTRANS_MIN_THRESHOLD = 0.00001
wm_outliers = []
gm_outliers = []
# rPhG_L_outliers = []
# rPhG_R_outliers = []
# cPhG_L_outliers = []
# cPhG_R_outliers = []
# lateral_PPHC_L_outliers = []
# lateral_PPHC_R_outliers = []
# ECPhG_L_outliers = []
# ECPhG_R_outliers = []
# TIPhG_L_outliers = []
# TIPhG_R_outliers = []
# THPhG_L_outliers = []
# THPhG_R_outliers = []
# rHipp_L_outliers = []
# rHipp_R_outliers = []
# cHipp_L_outliers = []
# cHipp_R_outliers = []
whole_hippo_outliers = []
whole_phg_outliers = []
whole_putamen_outliers = []
whole_pallidum_outliers = []
whole_thalamus_outliers = []
whole_caudate_outliers = []
whole_amygdala_outliers = []
whole_entorhinal_cortex_outliers = []
whole_fusiform_gyrus_cortex_outliers = []
whole_fusiform_gyrus_WM_outliers = []
whole_insula_WM_outliers = []
whole_superior_temporal_cortex_outliers = []
# subject_list = ["4_11570", "4_65948", "4_67316", "4_68721", "4_84177"]
# subject_list = ["1102237", "1102187", "1102043", "1101938", "1101943", "1101819", "1102019", "1102091", "1102092"]
total_timepoints = []
successful_timepoints = []
aif_curves = []
for subject_id in subjects:
    # if subject_id in subject_list:
    # list _timepoint directories in subject directory
    for timepoint in os.listdir(os.path.join(dir, subject_id)):
        aif_metric = 0
        T1_wm_median = 0
        T1_wm_std = 0
        T1_gm_median = 0
        T1_gm_std = 0
        wm_mean = 0
        wm_median = 0
        wm_std = 0
        gm_mean = 0
        gm_median = 0
        gm_std = 0
        # print(subject_id + "_" + timepoint)
        if timepoint.endswith("_timepoint"):
            total_timepoints.append(subject_id + '/' + timepoint + "/" + output_dir)
            # read AIF curve by applying aif.nii to dce.nii
            try:
                dce = os.path.join(dir, subject_id, timepoint, output_dir, "DCE_mc_bfc_norm.nii.gz")
                aif = os.path.join(dir, subject_id, timepoint, output_dir, "aif.nii")
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
                if any(intensities[10:30] < 2):
                    print(subject_id, timepoint, "has an intensity < 2")
                # line up curve peaks
                max_index = np.argmax(intensities)
                intensities = np.roll(intensities, -max_index+2)
                aif_curves.append(intensities[0:40])
            except Exception as e:
                print("Error reading DCE or AIF for", subject_id, timepoint)
                print(e)
                continue

            # read wm and gm data from html file
            filename = os.path.join(dir, subject_id, timepoint, output_dir, "case_report.html")
            try:
                with open(filename, "r") as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if "T1 wm median:" in line:
                            T1_wm_median = float(line.split(":")[-1].strip()[:-5])
                            # T1_wm_std = lines[i + 1].split(':')[-1].strip()[:-4]
                        if "T1 gm median:" in line:
                            T1_gm_median = float(line.split(":")[-1].strip()[:-5])
                            # T1_gm_std = lines[i + 1].split(':')[-1].strip()[:-4]
                        if "Blood T1: " in line:
                            T1_blood = float(line.split(":")[-1].strip()[:-6])
                        if "Median wm Ktrans" in line:
                            # wm_mean = float(lines[i].split(':')[1][:-6])
                            wm_median = float(lines[i].split()[-1][:-6])
                            # wm_std = float(lines[i + 1].split(':')[-1][:-6])
                        if "Median gm Ktrans" in line:
                            # gm_mean = float(lines[i].split(':')[1][:-6])
                            gm_median = float(lines[i].split()[-1][:-6])
                            # gm_std = float(lines[i + 1].split(':')[-1][:-6])
                        # read aif metric from html file
                        if "AIFitness" in line:
                            aif_metric = line.split(":")[-1].strip()[:-4]
                            # population_aif_metric.append(round(float(aif_metric), 4))
                            if float(aif_metric) > 130:
                                print(subject_id + "_" + timepoint + " has an aif_metric of " + str(aif_metric) + "!")
                        if wm_median > 5:
                            if subject_id + "_" + timepoint not in wm_outliers:
                                print(subject_id + "_" + timepoint + " has a wm_median of " + str(wm_median) + "!")
                                wm_outliers.append(subject_id + "_" + timepoint)
                        if gm_median > 5:
                            if subject_id + "_" + timepoint not in gm_outliers:
                                print(subject_id + "_" + timepoint + " has a gm_median of " + str(gm_median) + "!")
                                gm_outliers.append(subject_id + "_" + timepoint)
            except Exception as e:
                print("Error reading " + filename)
                print(e)
                T1_wm_median = -1
                T1_gm_median = -1
                T1_blood = -1
                wm_median = -1
                gm_median = -1
                aif_metric = -1
                # continue

            # read lines after "AIF mmol:"
            aif_mmol = []
            B_log = os.path.join(dir, subject_id, timepoint, output_dir, "B_dcefitted_R1info.log")
            try:
                with open(B_log, 'r') as f:
                    for line in f:
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
                            break
            except Exception as e:
                print("Error reading " + B_log)
                print(e)
                aif_mmol = -1
            # get manufacturer, field strength, and machine from json
            json_file = os.path.join(dir, subject_id, timepoint, output_dir, "DCE.json")
            try:
                with open(json_file, 'r') as f:
                    for line in f:
                        if "\"Manufacturer\":" in line:
                            manufacturer = line.split(":")[-1].strip()[1:-2]
                        if "MagneticFieldStrength" in line:
                            field_strength = line.split(":")[-1].strip()[0] + "T"
                        if "ManufacturersModelName" in line:
                            machine = line.split(":")[-1].strip()[1:-2]
                        if "InstitutionName" in line:
                            institution = line.split(":")[-1].strip()[1:-2]
            except Exception as e:
                print("Error reading " + json_file)
                print(e)
                manufacturer = "json error"
                field_strength = "json error"
                machine = "json error"
                institution = "json error"

            # get MNI region stats
            # read ktrans map
            # ktrans_map = os.path.join(dir, subject_id, timepoint, output_dir, "Ktrans_MNI.nii.gz")
            # ktrans_map = nib.load(ktrans_map)
            # ktrans_map = ktrans_map.get_fdata()
            try:
                ktrans_map = os.path.join(dir, subject_id, timepoint, output_dir, "dce_patlak_fit_Ktrans.nii")
                ktrans_map = nib.load(ktrans_map)
                ktrans_map = ktrans_map.get_fdata()
            except:
                print("Error reading " + ktrans_map)
                continue
            # try:
            #     ktrans_map_hippo = os.path.join(dir, subject_id, timepoint, output_dir, "Ktrans_aseg.nii.gz")
            #     ktrans_map_hippo = nib.load(ktrans_map_hippo)
            #     ktrans_map_hippo = ktrans_map_hippo.get_fdata()
            #     ktrans_map = ktrans_map_hippo
            #     # get mean of each z-slice and select slice with highest mean
            #     ktrans_map = np.mean(ktrans_map, axis=(0, 1))
            #     ktrans_map = np.argmax(ktrans_map)
            #     # select z-slice with highest mean
            #     ktrans_map_hippo = ktrans_map_hippo[:,:,ktrans_map]
            # except:
            #     print("Error reading " + ktrans_map_hippo)
            #     continue
            # ktrans_map = ktrans_map[:,110,:]
            # rPhG_L = 109
            # rPhG_R = 110
            # cPhG_L = 111
            # cPhG_R = 112
            # lateral_PPHC_L = 113
            # lateral_PPHC_R = 114
            # ECPhG_L = 115
            # ECPhG_R = 116
            # TIPhG_L = 117
            # TIPhG_R = 118
            # THPhG_L = 119
            # THPhG_R = 120
            # rHipp_L = 215
            # rHipp_R = 216
            # cHipp_L = 217
            # cHipp_R = 218
            # Numbers are locations of regions in freesurfer wmparc.mgz
            L_HIPPO = 17
            R_HIPPO = 53
            L_PHG = 1016
            R_PHG = 2016
            L_PUTAMEN = 12
            R_PUTAMEN = 51
            L_PALLIDUM = 13
            R_PALLIDUM = 52
            L_THALAMUS = 10
            R_THALAMUS = 49
            L_CAUDATE = 11
            R_CAUDATE = 50
            L_AMYGDALA = 18
            R_AMYGDALA = 54
            L_ENTORHINAL_CORTEX = 1006
            R_ENTORHINAL_CORTEX = 2006
            L_FUSIFORM_GYRUS_CORTEX = 1007
            R_FUSIFORM_GYRUS_CORTEX = 2007
            L_FUSIFORM_GYRUS_WM = 3007
            R_FUSIFORM_GYRUS_WM = 4007
            L_INSULA_WM = 3035
            R_INSULA_WM = 4035
            L_SUPERIOR_TEMPORAL_CORTEX = 1030
            R_SUPERIOR_TEMPORAL_CORTEX = 2030
            # atlas file is where this script is located
            # atlas = os.path.join(os.path.dirname(os.path.realpath(__file__)), "BN_Atlas_246_1mm.nii.gz")
            # atlas = nib.load(atlas)
            # atlas = atlas.get_fdata()
            # atlas = ktrans_map_hippo
            # atlas = atlas[:,110,:]
            try:
                wmparc = os.path.join(dir, subject_id, timepoint, output_dir, "wmparc_dyn.nii.gz")
                wmparc = nib.load(wmparc)
                wmparc = wmparc.get_fdata()
            except Exception as e:
                print("Error reading " + wmparc)
                print(e)
                continue
            HIPPO_INDICES = np.where((wmparc == L_HIPPO) | (wmparc == R_HIPPO) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            PHG_INDICES = np.where((wmparc == L_PHG) | (wmparc == R_PHG) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            PUTAMEN_INDICES = np.where((wmparc == L_PUTAMEN) | (wmparc == R_PUTAMEN) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            PALLIDUM_INDICES = np.where((wmparc == L_PALLIDUM) | (wmparc == R_PALLIDUM) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            THALAMUS_INDICES = np.where((wmparc == L_THALAMUS) | (wmparc == R_THALAMUS) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            CAUDATE_INDICES = np.where((wmparc == L_CAUDATE) | (wmparc == R_CAUDATE) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            AMYGDALA_INDICES = np.where((wmparc == L_AMYGDALA) | (wmparc == R_AMYGDALA) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            ENTORHINAL_CORTEX_INDICES = np.where((wmparc == L_ENTORHINAL_CORTEX) | (wmparc == R_ENTORHINAL_CORTEX) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            FUSIFORM_GYRUS_CORTEX_INDICES = np.where((wmparc == L_FUSIFORM_GYRUS_CORTEX) | (wmparc == R_FUSIFORM_GYRUS_CORTEX) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            FUSIFORM_GYRUS_WM_INDICES = np.where((wmparc == L_FUSIFORM_GYRUS_WM) | (wmparc == R_FUSIFORM_GYRUS_WM) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            INSULA_WM_INDICES = np.where((wmparc == L_INSULA_WM) | (wmparc == R_INSULA_WM) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            SUPERIOR_TEMPORAL_CORTEX_INDICES = np.where((wmparc == L_SUPERIOR_TEMPORAL_CORTEX) | (wmparc == R_SUPERIOR_TEMPORAL_CORTEX) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # get indices of hippocampi on z-slice 110
            # MNI_hippo_seg = os.path.join(os.path.dirname(os.path.realpath(__file__)), "MNI_hippo_seg.nii.gz")
            # MNI_hippo_seg = nib.load(MNI_hippo_seg)
            # MNI_hippo_seg = MNI_hippo_seg.get_fdata()
            # rPhG_L_indices = np.where((atlas == rPhG_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # rPhG_R_indices = np.where((atlas == rPhG_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # cPhG_L_indices = np.where((atlas == cPhG_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # cPhG_R_indices = np.where((atlas == cPhG_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # whole_hippo = np.where((atlas == rHipp_L) | (atlas == rHipp_R) | (atlas == cHipp_L) | (atlas == cHipp_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # lateral_PPHC_L_indices = np.where((atlas == lateral_PPHC_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # lateral_PPHC_R_indices = np.where((atlas == lateral_PPHC_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # ECPhG_L_indices = np.where((atlas == ECPhG_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # ECPhG_R_indices = np.where((atlas == ECPhG_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # TIPhG_L_indices = np.where((atlas == TIPhG_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # TIPhG_R_indices = np.where((atlas == TIPhG_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # THPhG_L_indices = np.where((atlas == THPhG_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # THPhG_R_indices = np.where((atlas == THPhG_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # rHipp_L_indices = np.where((atlas == rHipp_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # rHipp_R_indices = np.where((atlas == rHipp_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # cHipp_L_indices = np.where((atlas == cHipp_L) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # cHipp_R_indices = np.where((atlas == cHipp_R) & (ktrans_map > KTRANS_MIN_THRESHOLD))
            # get ktrans values at hippocampi
            # ktrans_rPhG_L = ktrans_map[rPhG_L_indices]*1000
            # ktrans_rPhG_R = ktrans_map[rPhG_R_indices]*1000
            # ktrans_cPhG_L = ktrans_map[cPhG_L_indices]*1000
            # ktrans_cPhG_R = ktrans_map[cPhG_R_indices]*1000
            # ktrans_lateral_PPHC_L = ktrans_map[lateral_PPHC_L_indices]*1000
            # ktrans_lateral_PPHC_R = ktrans_map[lateral_PPHC_R_indices]*1000
            # ktrans_ECPhG_L = ktrans_map[ECPhG_L_indices]*1000
            # ktrans_ECPhG_R = ktrans_map[ECPhG_R_indices]*1000
            # ktrans_TIPhG_L = ktrans_map[TIPhG_L_indices]*1000
            # ktrans_TIPhG_R = ktrans_map[TIPhG_R_indices]*1000
            # ktrans_THPhG_L = ktrans_map[THPhG_L_indices]*1000
            # ktrans_THPhG_R = ktrans_map[THPhG_R_indices]*1000
            # ktrans_rHipp_L = ktrans_map[rHipp_L_indices]*1000
            # ktrans_rHipp_R = ktrans_map[rHipp_R_indices]*1000
            # ktrans_cHipp_L = ktrans_map[cHipp_L_indices]*1000
            # ktrans_cHipp_R = ktrans_map[cHipp_R_indices]*1000
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
            # ktrans_whole_hippo = ktrans_map[whole_hippo]*1000
            # get median ktrans values
            # ktrans_rPhG_L_median = np.median(ktrans_rPhG_L)
            # ktrans_rPhG_R_median = np.median(ktrans_rPhG_R)
            # ktrans_cPhG_L_median = np.median(ktrans_cPhG_L)
            # ktrans_cPhG_R_median = np.median(ktrans_cPhG_R)
            # ktrans_lateral_PPHC_L_median = np.median(ktrans_lateral_PPHC_L)
            # ktrans_lateral_PPHC_R_median = np.median(ktrans_lateral_PPHC_R)
            # ktrans_ECPhG_L_median = np.median(ktrans_ECPhG_L)
            # ktrans_ECPhG_R_median = np.median(ktrans_ECPhG_R)
            # ktrans_TIPhG_L_median = np.median(ktrans_TIPhG_L)
            # ktrans_TIPhG_R_median = np.median(ktrans_TIPhG_R)
            # ktrans_THPhG_L_median = np.median(ktrans_THPhG_L)
            # ktrans_THPhG_R_median = np.median(ktrans_THPhG_R)
            # ktrans_rHipp_L_median = np.median(ktrans_rHipp_L)
            # ktrans_rHipp_R_median = np.median(ktrans_rHipp_R)
            # ktrans_cHipp_L_median = np.median(ktrans_cHipp_L)
            # ktrans_cHipp_R_median = np.median(ktrans_cHipp_R)
            Ktrans_Hippo_median = np.median(Ktrans_Hippo)
            Ktrans_PhG_median = np.median(Ktrans_PhG)
            Ktrans_Putamen_median = np.median(Ktrans_Putamen)
            Ktrans_Pallidum_median = np.median(Ktrans_Pallidum)
            Ktrans_Thalamus_median = np.median(Ktrans_Thalamus)
            Ktrans_Caudate_median = np.median(Ktrans_Caudate)
            Ktrans_Amygdala_median = np.median(Ktrans_Amygdala)
            Ktrans_Entorhinal_cortex_median = np.median(Ktrans_Entorhinal_cortex)
            Ktrans_Fusiform_gyrus_cortex_median = np.median(Ktrans_Fusiform_gyrus_cortex)
            Ktrans_Fusiform_gyrus_WM_median = np.median(Ktrans_Fusiform_gyrus_WM)
            Ktrans_Insula_WM_median = np.median(Ktrans_Insula_WM)
            Ktrans_Superior_temporal_cortex_median = np.median(Ktrans_Superior_temporal_cortex)
            
            # check for outliers
            # if ktrans_rPhG_L_median > 5:
            #     if subject_id + "_" + timepoint not in rPhG_L_outliers:
            #         rPhG_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_rPhG_R_median > 5:
            #     if subject_id + "_" + timepoint not in rPhG_R_outliers:
            #         rPhG_R_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_cPhG_L_median > 5:
            #     if subject_id + "_" + timepoint not in cPhG_L_outliers:
            #         cPhG_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_cPhG_R_median > 5:
            #     if subject_id + "_" + timepoint not in cPhG_R_outliers:
            #         cPhG_R_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_lateral_PPHC_L_median > 5:
            #     if subject_id + "_" + timepoint not in lateral_PPHC_L_outliers:
            #         lateral_PPHC_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_lateral_PPHC_R_median > 5:
            #     if subject_id + "_" + timepoint not in lateral_PPHC_R_outliers:
            #         lateral_PPHC_R_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_ECPhG_L_median > 5:
            #     if subject_id + "_" + timepoint not in ECPhG_L_outliers:
            #         ECPhG_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_ECPhG_R_median > 5:
            #     if subject_id + "_" + timepoint not in ECPhG_R_outliers:
            #         ECPhG_R_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_TIPhG_L_median > 5:
            #     if subject_id + "_" + timepoint not in TIPhG_L_outliers:
            #         TIPhG_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_TIPhG_R_median > 5:
            #     if subject_id + "_" + timepoint not in TIPhG_R_outliers:
            #         TIPhG_R_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_THPhG_L_median > 5:
            #     if subject_id + "_" + timepoint not in THPhG_L_outliers:
            #         THPhG_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_THPhG_R_median > 5:
            #     if subject_id + "_" + timepoint not in THPhG_R_outliers:
            #         THPhG_R_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_rHipp_L_median > 5:
            #     if subject_id + "_" + timepoint not in rHipp_L_outliers:
            #         rHipp_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_rHipp_R_median > 5:
            #     if subject_id + "_" + timepoint not in rHipp_R_outliers:
            #         rHipp_R_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_cHipp_L_median > 5:
            #     if subject_id + "_" + timepoint not in cHipp_L_outliers:
            #         cHipp_L_outliers.append(subject_id + "_" + timepoint)
            # if ktrans_cHipp_R_median > 5:
            #     if subject_id + "_" + timepoint not in cHipp_R_outliers:
            #         cHipp_R_outliers.append(subject_id + "_" + timepoint)
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
            # get mean ktrans values
            # ktrans_rPhG_L_mean = np.mean(ktrans_rPhG_L)
            # ktrans_rPhG_R_mean = np.mean(ktrans_rPhG_R)
            # ktrans_cPhG_L_mean = np.mean(ktrans_cPhG_L)
            # ktrans_cPhG_R_mean = np.mean(ktrans_cPhG_R)
            # ktrans_lateral_PPHC_L_mean = np.mean(ktrans_lateral_PPHC_L)
            # ktrans_lateral_PPHC_R_mean = np.mean(ktrans_lateral_PPHC_R)
            # ktrans_ECPhG_L_mean = np.mean(ktrans_ECPhG_L)
            # ktrans_ECPhG_R_mean = np.mean(ktrans_ECPhG_R)
            # ktrans_TIPhG_L_mean = np.mean(ktrans_TIPhG_L)
            # ktrans_TIPhG_R_mean = np.mean(ktrans_TIPhG_R)
            # ktrans_THPhG_L_mean = np.mean(ktrans_THPhG_L)
            # ktrans_THPhG_R_mean = np.mean(ktrans_THPhG_R)
            # ktrans_rHipp_L_mean = np.mean(ktrans_rHipp_L)
            # ktrans_rHipp_R_mean = np.mean(ktrans_rHipp_R)
            # ktrans_cHipp_L_mean = np.mean(ktrans_cHipp_L)
            # ktrans_cHipp_R_mean = np.mean(ktrans_cHipp_R)
            # Ktrans_Hippo_mean = np.mean(Ktrans_Hippo)
            # Ktrans_PhG_mean = np.mean(Ktrans_PhG)
            # Ktrans_Putamen_mean = np.mean(Ktrans_Putamen)
            # Ktrans_Pallidum_mean = np.mean(Ktrans_Pallidum)
            # Ktrans_Thalamus_mean = np.mean(Ktrans_Thalamus)
            # Ktrans_Caudate_mean = np.mean(Ktrans_Caudate)
            # Ktrans_Amygdala_mean = np.mean(Ktrans_Amygdala)
            # Ktrans_Entorhinal_cortex_mean = np.mean(Ktrans_Entorhinal_cortex)
            # Ktrans_Fusiform_gyrus_cortex_mean = np.mean(Ktrans_Fusiform_gyrus_cortex)
            # Ktrans_Fusiform_gyrus_WM_mean = np.mean(Ktrans_Fusiform_gyrus_WM)
            # Ktrans_Insula_WM_mean = np.mean(Ktrans_Insula_WM)
            # Ktrans_Superior_temporal_cortex_mean = np.mean(Ktrans_Superior_temporal_cortex)

            # get std ktrans values
            # ktrans_rPhG_L_std = np.std(ktrans_rPhG_L)
            # ktrans_rPhG_R_std = np.std(ktrans_rPhG_R)
            # ktrans_cPhG_L_std = np.std(ktrans_cPhG_L)
            # ktrans_cPhG_R_std = np.std(ktrans_cPhG_R)
            # ktrans_lateral_PPHC_L_std = np.std(ktrans_lateral_PPHC_L)
            # ktrans_lateral_PPHC_R_std = np.std(ktrans_lateral_PPHC_R)
            # ktrans_ECPhG_L_std = np.std(ktrans_ECPhG_L)
            # ktrans_ECPhG_R_std = np.std(ktrans_ECPhG_R)
            # ktrans_TIPhG_L_std = np.std(ktrans_TIPhG_L)
            # ktrans_TIPhG_R_std = np.std(ktrans_TIPhG_R)
            # ktrans_THPhG_L_std = np.std(ktrans_THPhG_L)
            # ktrans_THPhG_R_std = np.std(ktrans_THPhG_R)
            # ktrans_rHipp_L_std = np.std(ktrans_rHipp_L)
            # ktrans_rHipp_R_std = np.std(ktrans_rHipp_R)
            # ktrans_cHipp_L_std = np.std(ktrans_cHipp_L)
            # ktrans_cHipp_R_std = np.std(ktrans_cHipp_R)
            # Ktrans_Hippo_std = np.std(Ktrans_Hippo)
            # Ktrans_PhG_std = np.std(Ktrans_PhG)
            # Ktrans_Putamen_std = np.std(Ktrans_Putamen)
            # Ktrans_Pallidum_std = np.std(Ktrans_Pallidum)
            # Ktrans_Thalamus_std = np.std(Ktrans_Thalamus)
            # Ktrans_Caudate_std = np.std(Ktrans_Caudate)
            # Ktrans_Amygdala_std = np.std(Ktrans_Amygdala)
            # Ktrans_Entorhinal_cortex_std = np.std(Ktrans_Entorhinal_cortex)
            # Ktrans_Fusiform_gyrus_cortex_std = np.std(Ktrans_Fusiform_gyrus_cortex)
            # Ktrans_Fusiform_gyrus_WM_std = np.std(Ktrans_Fusiform_gyrus_WM)
            # Ktrans_Insula_WM_std = np.std(Ktrans_Insula_WM)
            # Ktrans_Superior_temporal_cortex_std = np.std(Ktrans_Superior_temporal_cortex)
            
            successful_timepoints.append(subject_id + '/' + timepoint + "/" + output_dir)
            entry = subject_id + "_" + timepoint
            population_data[entry] = {
                "aif_metric": aif_metric,
                "aif_mmol": aif_mmol,
                "T1_wm_median": T1_wm_median,
                # T1_wm_std: T1_wm_std,
                "T1_gm_median": T1_gm_median,
                # T1_gm_std: T1_gm_std,
                "T1_blood": T1_blood,
                # "wm_mean": wm_mean,
                "wm_median": wm_median,
                # "wm_std": wm_std,
                # "gm_mean": gm_mean,
                "gm_median": gm_median,
                # "gm_std": gm_std
                "manufacturer": manufacturer,
                "field_strength": field_strength,
                "machine": machine,
                "institution": institution,
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
            }

try:
    AIFitness_values = [float(population_data[entry]["aif_metric"]) for entry in population_data]
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
    wm_mean = np.mean([population_data[entry]["wm_median"] for entry in population_data])
    wm_median = np.median([population_data[entry]["wm_median"] for entry in population_data])
    wm_std = np.std([population_data[entry]["wm_median"] for entry in population_data])
    gm_mean = np.mean([population_data[entry]["gm_median"] for entry in population_data])
    gm_median = np.median([population_data[entry]["gm_median"] for entry in population_data])
    gm_std = np.std([population_data[entry]["gm_median"] for entry in population_data])
except Exception as e:
    print(e)
    wm_mean = -1
    wm_median = -1
    wm_std = -1
    gm_mean = -1
    gm_median = -1
    gm_std = -1

# rPhG_L_mean = np.mean([population_data[entry]["ktrans_rPhG_L_median"] for entry in population_data])
# rPhG_L_median = np.median([population_data[entry]["ktrans_rPhG_L_median"] for entry in population_data])
# rPhG_L_std = np.std([population_data[entry]["ktrans_rPhG_L_median"] for entry in population_data])
# rPhG_R_mean = np.mean([population_data[entry]["ktrans_rPhG_R_median"] for entry in population_data])
# rPhG_R_median = np.median([population_data[entry]["ktrans_rPhG_R_median"] for entry in population_data])
# rPhG_R_std = np.std([population_data[entry]["ktrans_rPhG_R_median"] for entry in population_data])
# cPhG_L_mean = np.mean([population_data[entry]["ktrans_cPhG_L_median"] for entry in population_data])
# cPhG_L_median = np.median([population_data[entry]["ktrans_cPhG_L_median"] for entry in population_data])
# cPhG_L_std = np.std([population_data[entry]["ktrans_cPhG_L_median"] for entry in population_data])
# cPhG_R_mean = np.mean([population_data[entry]["ktrans_cPhG_R_median"] for entry in population_data])
# cPhG_R_median = np.median([population_data[entry]["ktrans_cPhG_R_median"] for entry in population_data])
# cPhG_R_std = np.std([population_data[entry]["ktrans_cPhG_R_median"] for entry in population_data])
# lateral_PPHC_L_mean = np.mean([population_data[entry]["ktrans_lateral_PPHC_L_median"] for entry in population_data])
# lateral_PPHC_L_median = np.median([population_data[entry]["ktrans_lateral_PPHC_L_median"] for entry in population_data])
# lateral_PPHC_L_std = np.std([population_data[entry]["ktrans_lateral_PPHC_L_median"] for entry in population_data])
# lateral_PPHC_R_mean = np.mean([population_data[entry]["ktrans_lateral_PPHC_R_median"] for entry in population_data])
# lateral_PPHC_R_median = np.median([population_data[entry]["ktrans_lateral_PPHC_R_median"] for entry in population_data])
# lateral_PPHC_R_std = np.std([population_data[entry]["ktrans_lateral_PPHC_R_median"] for entry in population_data])
# ECPhG_L_mean = np.mean([population_data[entry]["ktrans_ECPhG_L_median"] for entry in population_data])
# ECPhG_L_median = np.median([population_data[entry]["ktrans_ECPhG_L_median"] for entry in population_data])
# ECPhG_L_std = np.std([population_data[entry]["ktrans_ECPhG_L_median"] for entry in population_data])
# ECPhG_R_mean = np.mean([population_data[entry]["ktrans_ECPhG_R_median"] for entry in population_data])
# ECPhG_R_median = np.median([population_data[entry]["ktrans_ECPhG_R_median"] for entry in population_data])
# ECPhG_R_std = np.std([population_data[entry]["ktrans_ECPhG_R_median"] for entry in population_data])
# TIPhG_L_mean = np.mean([population_data[entry]["ktrans_TIPhG_L_median"] for entry in population_data])
# TIPhG_L_median = np.median([population_data[entry]["ktrans_TIPhG_L_median"] for entry in population_data])
# TIPhG_L_std = np.std([population_data[entry]["ktrans_TIPhG_L_median"] for entry in population_data])
# TIPhG_R_mean = np.mean([population_data[entry]["ktrans_TIPhG_R_median"] for entry in population_data])
# TIPhG_R_median = np.median([population_data[entry]["ktrans_TIPhG_R_median"] for entry in population_data])
# TIPhG_R_std = np.std([population_data[entry]["ktrans_TIPhG_R_median"] for entry in population_data])
# THPhG_L_mean = np.mean([population_data[entry]["ktrans_THPhG_L_median"] for entry in population_data])
# THPhG_L_median = np.median([population_data[entry]["ktrans_THPhG_L_median"] for entry in population_data])
# THPhG_L_std = np.std([population_data[entry]["ktrans_THPhG_L_median"] for entry in population_data])
# THPhG_R_mean = np.mean([population_data[entry]["ktrans_THPhG_R_median"] for entry in population_data])
# THPhG_R_median = np.median([population_data[entry]["ktrans_THPhG_R_median"] for entry in population_data])
# THPhG_R_std = np.std([population_data[entry]["ktrans_THPhG_R_median"] for entry in population_data])
# rHipp_L_mean = np.mean([population_data[entry]["ktrans_rHipp_L_median"] for entry in population_data])
# rHipp_L_median = np.median([population_data[entry]["ktrans_rHipp_L_median"] for entry in population_data])
# rHipp_L_std = np.std([population_data[entry]["ktrans_rHipp_L_median"] for entry in population_data])
# rHipp_R_mean = np.mean([population_data[entry]["ktrans_rHipp_R_median"] for entry in population_data])
# rHipp_R_median = np.median([population_data[entry]["ktrans_rHipp_R_median"] for entry in population_data])
# rHipp_R_std = np.std([population_data[entry]["ktrans_rHipp_R_median"] for entry in population_data])
# cHipp_L_mean = np.mean([population_data[entry]["ktrans_cHipp_L_median"] for entry in population_data])
# cHipp_L_median = np.median([population_data[entry]["ktrans_cHipp_L_median"] for entry in population_data])
# cHipp_L_std = np.std([population_data[entry]["ktrans_cHipp_L_median"] for entry in population_data])
# cHipp_R_mean = np.mean([population_data[entry]["ktrans_cHipp_R_median"] for entry in population_data])
# cHipp_R_median = np.median([population_data[entry]["ktrans_cHipp_R_median"] for entry in population_data])
# cHipp_R_std = np.std([population_data[entry]["ktrans_cHipp_R_median"] for entry in population_data])
whole_hippo_mean = np.mean([population_data[entry]["Ktrans_Hippo_median"] for entry in population_data])
whole_hippo_median = np.median([population_data[entry]["Ktrans_Hippo_median"] for entry in population_data])
whole_hippo_std = np.std([population_data[entry]["Ktrans_Hippo_median"] for entry in population_data])

whole_phg_mean = np.mean([population_data[entry]["Ktrans_PhG_median"] for entry in population_data])
whole_phg_median = np.median([population_data[entry]["Ktrans_PhG_median"] for entry in population_data])
whole_phg_std = np.std([population_data[entry]["Ktrans_PhG_median"] for entry in population_data])

whole_putamen_mean = np.mean([population_data[entry]["Ktrans_Putamen_median"] for entry in population_data])
whole_putamen_median = np.median([population_data[entry]["Ktrans_Putamen_median"] for entry in population_data])
whole_putamen_std = np.std([population_data[entry]["Ktrans_Putamen_median"] for entry in population_data])

whole_pallidum_mean = np.mean([population_data[entry]["Ktrans_Pallidum_median"] for entry in population_data])
whole_pallidum_median = np.median([population_data[entry]["Ktrans_Pallidum_median"] for entry in population_data])
whole_pallidum_std = np.std([population_data[entry]["Ktrans_Pallidum_median"] for entry in population_data])

whole_thalamus_mean = np.mean([population_data[entry]["Ktrans_Thalamus_median"] for entry in population_data])
whole_thalamus_median = np.median([population_data[entry]["Ktrans_Thalamus_median"] for entry in population_data])
whole_thalamus_std = np.std([population_data[entry]["Ktrans_Thalamus_median"] for entry in population_data])

whole_caudate_mean = np.mean([population_data[entry]["Ktrans_Caudate_median"] for entry in population_data])
whole_caudate_median = np.median([population_data[entry]["Ktrans_Caudate_median"] for entry in population_data])
whole_caudate_std = np.std([population_data[entry]["Ktrans_Caudate_median"] for entry in population_data])

whole_amygdala_mean = np.mean([population_data[entry]["Ktrans_Amygdala_median"] for entry in population_data])
whole_amygdala_median = np.median([population_data[entry]["Ktrans_Amygdala_median"] for entry in population_data])
whole_amygdala_std = np.std([population_data[entry]["Ktrans_Amygdala_median"] for entry in population_data])

whole_entorhinal_cortex_mean = np.mean([population_data[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data])
whole_entorhinal_cortex_median = np.median([population_data[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data])
whole_entorhinal_cortex_std = np.std([population_data[entry]["Ktrans_Entorhinal_cortex_median"] for entry in population_data])

whole_fusiform_gyrus_cortex_mean = np.mean([population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data])
whole_fusiform_gyrus_cortex_median = np.median([population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data])
whole_fusiform_gyrus_cortex_std = np.std([population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"] for entry in population_data])

whole_fusiform_gyrus_WM_mean = np.mean([population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data])
whole_fusiform_gyrus_WM_median = np.median([population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data])
whole_fusiform_gyrus_WM_std = np.std([population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"] for entry in population_data])

whole_insula_WM_mean = np.mean([population_data[entry]["Ktrans_Insula_WM_median"] for entry in population_data])
whole_insula_WM_median = np.median([population_data[entry]["Ktrans_Insula_WM_median"] for entry in population_data])
whole_insula_WM_std = np.std([population_data[entry]["Ktrans_Insula_WM_median"] for entry in population_data])

whole_superior_temporal_cortex_mean = np.mean([population_data[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data])
whole_superior_temporal_cortex_median = np.median([population_data[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data])
whole_superior_temporal_cortex_std = np.std([population_data[entry]["Ktrans_Superior_temporal_cortex_median"] for entry in population_data])

# if no outliers, set to "None"
if len(wm_outliers) == 0:
    wm_outliers = "None"
if len(gm_outliers) == 0:
    gm_outliers = "None"

# make figures directory if it doesn't exist
if not os.path.exists(os.path.join(dir, "figures/")):
    os.makedirs(os.path.join(dir, "figures/"))

# make T1 blood histogram
T1_blood_histogram = []
for entry in population_data.keys():
    T1_blood_histogram.append(population_data[entry]["T1_blood"])

# plot histogram
plt.hist(T1_blood_histogram, bins=30)
plt.title("T1 Blood")
plt.xlabel("T1 Blood")
T1_blood_histogram_path = os.path.join(dir, "figures/", output_dir + "T1_blood_histogram.png")
plt.savefig(T1_blood_histogram_path, bbox_inches='tight')
plt.close()

# make AIFitness histogram
plt.hist(AIFitness_values, bins=30)
plt.title("AIFitness Median")
plt.xlabel("AIFitness")
aifitness_histogram_path = os.path.join(dir, "figures/", output_dir + "aifitness_histogram.png")
plt.savefig(aifitness_histogram_path, bbox_inches='tight')
plt.close()

# make aif_mmol histogram
aif_mmol_histogram = []
for entry in population_data.keys():
    aif_mmol_histogram.append(population_data[entry]["aif_mmol"])

# plot histogram
plt.hist(aif_mmol_histogram, bins=30)
plt.title("AIF mmol (mean of last 1/3)")
plt.xlabel("AIF mmol")
aif_mmol_histogram_path = os.path.join(dir, "figures/", output_dir + "aif_mmol_histogram.png")
plt.savefig(aif_mmol_histogram_path, bbox_inches='tight')
plt.close()

# make ktrans histograms from each timepoint mean
wm_histogram = []
for entry in population_data.keys():
    wm_histogram.append(population_data[entry]["wm_median"])

# plot histogram
plt.hist(wm_histogram, bins=50, range=(0, 5))
plt.title("White Matter Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
ktrans_wm_histogram_path = os.path.join(dir, "figures/", output_dir + "wm_histogram.png")
plt.savefig(ktrans_wm_histogram_path, bbox_inches='tight')
plt.close()

# now get gm mean histogram
gm_histogram = []
for entry in population_data.keys():
    gm_histogram.append(population_data[entry]["gm_median"])

# plot histogram
plt.hist(gm_histogram, bins=50, range=(0, 5))
plt.title("Gray Matter Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
ktrans_gm_histogram_path = os.path.join(dir, "figures/", output_dir + "gm_histogram.png")
# save range of histogram for later use
gm_histogram_range = plt.xlim()
plt.savefig(ktrans_gm_histogram_path, bbox_inches='tight')
plt.close()

avg_curve = np.asarray(aif_curves)
avg_curve = np.mean(avg_curve, axis=0)
# for aif in aif_curves:
#     plt.plot(aif, linewidth=0.5, color='grey', alpha=0.5)
plt.plot(avg_curve, linewidth=1, color='black')
# plot stdev per timepoint
plt.fill_between(np.arange(0, len(avg_curve)), avg_curve - np.std(aif_curves, axis=0), avg_curve + np.std(aif_curves, axis=0), alpha=0.3)
plt.xlabel('Time (s)')
plt.ylabel('Normalized Intensity')
plt.title('AIF Curves')
aif_avg_curve_path = os.path.join(dir, "figures/", output_dir + "aif_avg_curve.png")
plt.savefig(aif_avg_curve_path, bbox_inches='tight', dpi=300)  # Increase dpi for higher resolution
plt.close()

# time for hippocampus histograms
# rPhG_L_histogram = []
# for entry in population_data.keys():
#     rPhG_L_histogram.append(population_data[entry]["ktrans_rPhG_L_median"])

# rPhG_R_histogram = []
# for entry in population_data.keys():
#     rPhG_R_histogram.append(population_data[entry]["ktrans_rPhG_R_median"])

# cPhG_L_histogram = []
# for entry in population_data.keys():
#     cPhG_L_histogram.append(population_data[entry]["ktrans_cPhG_L_median"])

# cPhG_R_histogram = []
# for entry in population_data.keys():
#     cPhG_R_histogram.append(population_data[entry]["ktrans_cPhG_R_median"])

# lateral_PPHC_L_histogram = []
# for entry in population_data.keys():
#     lateral_PPHC_L_histogram.append(population_data[entry]["ktrans_lateral_PPHC_L_median"])

# lateral_PPHC_R_histogram = []
# for entry in population_data.keys():
#     lateral_PPHC_R_histogram.append(population_data[entry]["ktrans_lateral_PPHC_R_median"])

# ECPhG_L_histogram = []
# for entry in population_data.keys():
#     ECPhG_L_histogram.append(population_data[entry]["ktrans_ECPhG_L_median"])

# ECPhG_R_histogram = []
# for entry in population_data.keys():
#     ECPhG_R_histogram.append(population_data[entry]["ktrans_ECPhG_R_median"])

# TIPhG_L_histogram = []
# for entry in population_data.keys():
#     TIPhG_L_histogram.append(population_data[entry]["ktrans_TIPhG_L_median"])

# TIPhG_R_histogram = []
# for entry in population_data.keys():
#     TIPhG_R_histogram.append(population_data[entry]["ktrans_TIPhG_R_median"])

# THPhG_L_histogram = []
# for entry in population_data.keys():
#     THPhG_L_histogram.append(population_data[entry]["ktrans_THPhG_L_median"])

# THPhG_R_histogram = []
# for entry in population_data.keys():
#     THPhG_R_histogram.append(population_data[entry]["ktrans_THPhG_R_median"])

# rHipp_L_histogram = []
# for entry in population_data.keys():
#     rHipp_L_histogram.append(population_data[entry]["ktrans_rHipp_L_median"])
    
# rHipp_R_histogram = []
# for entry in population_data.keys():
#     rHipp_R_histogram.append(population_data[entry]["ktrans_rHipp_R_median"])

# cHipp_L_histogram = []
# for entry in population_data.keys():
#     cHipp_L_histogram.append(population_data[entry]["ktrans_cHipp_L_median"])

# cHipp_R_histogram = []
# for entry in population_data.keys():
#     cHipp_R_histogram.append(population_data[entry]["ktrans_cHipp_R_median"])

whole_hippo_histogram = []
for entry in population_data.keys():
    whole_hippo_histogram.append(population_data[entry]["Ktrans_Hippo_median"])

whole_phg_histogram = []
for entry in population_data.keys():
    whole_phg_histogram.append(population_data[entry]["Ktrans_PhG_median"])

whole_putamen_histogram = []
for entry in population_data.keys():
    whole_putamen_histogram.append(population_data[entry]["Ktrans_Putamen_median"])

whole_pallidum_histogram = []
for entry in population_data.keys():
    whole_pallidum_histogram.append(population_data[entry]["Ktrans_Pallidum_median"])

whole_thalamus_histogram = []
for entry in population_data.keys():
    whole_thalamus_histogram.append(population_data[entry]["Ktrans_Thalamus_median"])

whole_caudate_histogram = []
for entry in population_data.keys():
    whole_caudate_histogram.append(population_data[entry]["Ktrans_Caudate_median"])

whole_amygdala_histogram = []
for entry in population_data.keys():
    whole_amygdala_histogram.append(population_data[entry]["Ktrans_Amygdala_median"])

whole_entorhinal_cortex_histogram = []
for entry in population_data.keys():
    whole_entorhinal_cortex_histogram.append(population_data[entry]["Ktrans_Entorhinal_cortex_median"])

whole_fusiform_gyrus_cortex_histogram = []
for entry in population_data.keys():
    whole_fusiform_gyrus_cortex_histogram.append(population_data[entry]["Ktrans_Fusiform_gyrus_cortex_median"])

whole_fusiform_gyrus_WM_histogram = []
for entry in population_data.keys():
    whole_fusiform_gyrus_WM_histogram.append(population_data[entry]["Ktrans_Fusiform_gyrus_WM_median"])

whole_insula_WM_histogram = []
for entry in population_data.keys():
    whole_insula_WM_histogram.append(population_data[entry]["Ktrans_Insula_WM_median"])

whole_superior_temporal_cortex_histogram = []
for entry in population_data.keys():
    whole_superior_temporal_cortex_histogram.append(population_data[entry]["Ktrans_Superior_temporal_cortex_median"])

# make figures directory
# figures_dir = os.path.join(dir, "figures")
# if not os.path.exists(figures_dir):
#     os.makedirs(figures_dir)

# plot hippocampustograms
# plt.hist(rPhG_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Rostral Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# rPhG_L_histogram_path = os.path.join(dir, "figures/", output_dir + "rPhG_L_histogram.png")
# plt.savefig(rPhG_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(rPhG_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Rostral Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# rPhG_R_histogram_path = os.path.join(dir, "figures/", output_dir + "rPhG_R_histogram.png")
# plt.savefig(rPhG_R_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(cPhG_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Caudal Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# cPhG_L_histogram_path = os.path.join(dir, "figures/", output_dir + "cPhG_L_histogram.png")
# plt.savefig(cPhG_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(cPhG_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Caudal Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# cPhG_R_histogram_path = os.path.join(dir, "figures/", output_dir + "cPhG_R_histogram.png")
# plt.savefig(cPhG_R_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(lateral_PPHC_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Lateral Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# lateral_PPHC_L_histogram_path = os.path.join(dir, "figures/", output_dir + "lateral_PPHC_L_histogram.png")
# plt.savefig(lateral_PPHC_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(lateral_PPHC_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Lateral Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# lateral_PPHC_R_histogram_path = os.path.join(dir, "figures/", output_dir + "lateral_PPHC_R_histogram.png")
# plt.savefig(lateral_PPHC_R_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(ECPhG_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Entorhinal Cortex and Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# ECPhG_L_histogram_path = os.path.join(dir, "figures/", output_dir + "ECPhG_L_histogram.png")
# plt.savefig(ECPhG_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(ECPhG_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Entorhinal Cortex and Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# ECPhG_R_histogram_path = os.path.join(dir, "figures/", output_dir + "ECPhG_R_histogram.png")
# plt.savefig(ECPhG_R_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(TIPhG_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Temporal Inferior Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# TIPhG_L_histogram_path = os.path.join(dir, "figures/", output_dir + "TIPhG_L_histogram.png")
# plt.savefig(TIPhG_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(TIPhG_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Temporal Inferior Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# TIPhG_R_histogram_path = os.path.join(dir, "figures/", output_dir + "TIPhG_R_histogram.png")
# plt.savefig(TIPhG_R_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(THPhG_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Temporal Inferior Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# THPhG_L_histogram_path = os.path.join(dir, "figures/", output_dir + "THPhG_L_histogram.png")
# plt.savefig(THPhG_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(THPhG_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Temporal Inferior Parahippocampal Gyrus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# THPhG_R_histogram_path = os.path.join(dir, "figures/", output_dir + "THPhG_R_histogram.png")
# plt.savefig(THPhG_R_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(rHipp_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Rostral Hippocampus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# rHipp_L_histogram_path = os.path.join(dir, "figures/", output_dir + "rHipp_L_histogram.png")
# plt.savefig(rHipp_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(rHipp_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Rostral Hippocampus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# rHipp_R_histogram_path = os.path.join(dir, "figures/", output_dir + "rHipp_R_histogram.png")
# plt.savefig(rHipp_R_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(cHipp_L_histogram, bins=50, range=(0, 5))
# plt.title("Left Caudal Hippocampus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# cHipp_L_histogram_path = os.path.join(dir, "figures/", output_dir + "cHipp_L_histogram.png")
# plt.savefig(cHipp_L_histogram_path, bbox_inches='tight')
# plt.close()

# plt.hist(cHipp_R_histogram, bins=50, range=(0, 5))
# plt.title("Right Caudal Hippocampus Median Ktrans")
# plt.xlabel("Ktrans (10^-3/min)")
# cHipp_R_histogram_path = os.path.join(dir, "figures/", output_dir + "cHipp_R_histogram.png")
# plt.savefig(cHipp_R_histogram_path, bbox_inches='tight')
# plt.close()

plt.hist(whole_hippo_histogram, bins=50, range=(0, 5))
plt.title("Whole Hippocampus Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_hippo_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_hippo_histogram.png")
plt.savefig(whole_hippo_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_phg_histogram, bins=50, range=(0, 5))
plt.title("Whole Parahippocampal Gyrus Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_phg_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_phg_histogram.png")
plt.savefig(whole_phg_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_putamen_histogram, bins=50, range=(0, 5))
plt.title("Whole Putamen Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_putamen_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_putamen_histogram.png")
plt.savefig(whole_putamen_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_pallidum_histogram, bins=50, range=(0, 5))
plt.title("Whole Pallidum Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_pallidum_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_pallidum_histogram.png")
plt.savefig(whole_pallidum_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_thalamus_histogram, bins=50, range=(0, 5))
plt.title("Whole Thalamus Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_thalamus_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_thalamus_histogram.png")
plt.savefig(whole_thalamus_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_caudate_histogram, bins=50, range=(0, 5))
plt.title("Whole Caudate Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_caudate_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_caudate_histogram.png")
plt.savefig(whole_caudate_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_amygdala_histogram, bins=50, range=(0, 5))
plt.title("Whole Amygdala Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_amygdala_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_amygdala_histogram.png")
plt.savefig(whole_amygdala_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_entorhinal_cortex_histogram, bins=50, range=(0, 5))
plt.title("Whole Entorhinal Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_entorhinal_cortex_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_entorhinal_cortex_histogram.png")
plt.savefig(whole_entorhinal_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_fusiform_gyrus_cortex_histogram, bins=50, range=(0, 5))
plt.title("Whole Fusiform Gyrus Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_fusiform_gyrus_cortex_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_fusiform_gyrus_cortex_histogram.png")
plt.savefig(whole_fusiform_gyrus_cortex_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_fusiform_gyrus_WM_histogram, bins=50, range=(0, 5))
plt.title("Whole Fusiform Gyrus WM Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_fusiform_gyrus_WM_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_fusiform_gyrus_WM_histogram.png")
plt.savefig(whole_fusiform_gyrus_WM_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_insula_WM_histogram, bins=50, range=(0, 5))
plt.title("Whole Insula WM Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_insula_WM_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_insula_WM_histogram.png")
plt.savefig(whole_insula_WM_histogram_path, bbox_inches='tight')
plt.close()

plt.hist(whole_superior_temporal_cortex_histogram, bins=50, range=(0, 5))
plt.title("Whole Superior Temporal Cortex Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
whole_superior_temporal_cortex_histogram_path = os.path.join(dir, "figures/", output_dir + "whole_superior_temporal_cortex_histogram.png")
plt.savefig(whole_superior_temporal_cortex_histogram_path, bbox_inches='tight')
plt.close()

# round to 4 decimal places
wm_mean = round(wm_mean, 4)
wm_median = round(wm_median, 4)
wm_std = round(wm_std, 4)
gm_mean = round(gm_mean, 4)
gm_median = round(gm_median, 4)
gm_std = round(gm_std, 4)

# make population report
# df = pd.DataFrame(population_data)
# df.to_csv("population_report.csv")

# use jinja2 to generate html
env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(os.path.realpath(__file__))))
template = env.get_template('population_template.html')

# get date
date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# get commit hash
try:
    commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(os.path.realpath(__file__))).decode('ascii').strip()
except Exception as e:
    print("Git didn't work correctly. Trying a different way of getting latest dev branch commit hash...")
    command = ['cat', '.git/refs/heads/dev']

    commit_hash = subprocess.check_output(command, cwd=os.path.dirname(os.path.realpath(__file__))).decode('ascii').strip()

# make dict of manufacturer, field strength, machine, and institution
manufacturers = {}
field_strengths = {}
machines = {}
institutions = {}
for entry in population_data.keys():
    manufacturer = population_data[entry]["manufacturer"]
    field_strength = population_data[entry]["field_strength"]
    machine = population_data[entry]["machine"]
    institution = population_data[entry]["institution"]
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

successful_timepoints = list(set(successful_timepoints))
successful_timepoints.sort()
# num_timepoints = len(successful_timepoints)
# remove output_dir from successful_timepoints
cases = [timepoint.replace(output_dir, "") for timepoint in successful_timepoints]
# get failed cases from total_timepoints not in successful_timepoints
failed_cases = [timepoint.replace(output_dir, "") for timepoint in total_timepoints if timepoint not in successful_timepoints]
# get links for each failed case's directory
failed_links = [os.path.join(dir, case) + str(output_dir) for case in failed_cases]

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
        elif "relaxivity =" in line:
            pref_relaxivity = line.split("= ")[1].strip()
        elif "blood_t1 =" in line:
            pref_t1blood = line.split("= ")[1].strip()
        elif "start_t =" in line:
            pref_start_t = line.split("= ")[1].strip()
        elif "end_t =" in line:
            pref_end_t = line.split("= ")[1].strip()
        elif "time_resolution =" in line:
            pref_timeres = line.split("= ")[1].strip()

data = {
    'Subjects' : subjects,
    'base_url': dir,
    'Links': successful_timepoints,
    'Failed_links': failed_links,
    'Cases': cases,
    'Failed_cases': failed_cases,
    'Combo': zip(successful_timepoints, cases),
    'Failed_combo': zip(failed_links, failed_cases),
    'Subject_count': len(subjects),
    'Successes': str(len(population_data)) + '/' + str(len(total_timepoints)) + ' (' + str(round((len(population_data) / len(total_timepoints)) * 100, 2)) + '%)',
    'Date': date,
    'Commit': commit_hash,
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
    'AIFitness_histogram' : aifitness_histogram_path,
    'aif_mmol_histogram': aif_mmol_histogram_path,
    'wm_mean': wm_mean,
    'wm_median': wm_median,
    'wm_std': wm_std,
    'gm_mean': gm_mean,
    'gm_median': gm_median,
    'gm_std': gm_std,
    # 'rPhG_L_mean': round(rPhG_L_mean, 4),
    # 'rPhG_L_median': round(rPhG_L_median, 4),
    # 'rPhG_L_std': round(rPhG_L_std, 4),
    # 'rPhG_R_mean': round(rPhG_R_mean, 4),
    # 'rPhG_R_median': round(rPhG_R_median, 4),
    # 'rPhG_R_std': round(rPhG_R_std, 4),
    # 'cPhG_L_mean': round(cPhG_L_mean, 4),
    # 'cPhG_L_median': round(cPhG_L_median, 4),
    # 'cPhG_L_std': round(cPhG_L_std, 4),
    # 'cPhG_R_mean': round(cPhG_R_mean, 4),
    # 'cPhG_R_median': round(cPhG_R_median, 4),
    # 'cPhG_R_std': round(cPhG_R_std, 4),
    # 'lateral_PPHC_L_mean': round(lateral_PPHC_L_mean, 4),
    # 'lateral_PPHC_L_median': round(lateral_PPHC_L_median, 4),
    # 'lateral_PPHC_L_std': round(lateral_PPHC_L_std, 4),
    # 'lateral_PPHC_R_mean': round(lateral_PPHC_R_mean, 4),
    # 'lateral_PPHC_R_median': round(lateral_PPHC_R_median, 4),
    # 'lateral_PPHC_R_std': round(lateral_PPHC_R_std, 4),
    # 'ECPhG_L_mean': round(ECPhG_L_mean, 4),
    # 'ECPhG_L_median': round(ECPhG_L_median, 4),
    # 'ECPhG_L_std': round(ECPhG_L_std, 4),
    # 'ECPhG_R_mean': round(ECPhG_R_mean, 4),
    # 'ECPhG_R_median': round(ECPhG_R_median, 4),
    # 'ECPhG_R_std': round(ECPhG_R_std, 4),
    # 'TIPhG_L_mean': round(TIPhG_L_mean, 4),
    # 'TIPhG_L_median': round(TIPhG_L_median, 4),
    # 'TIPhG_L_std': round(TIPhG_L_std, 4),
    # 'TIPhG_R_mean': round(TIPhG_R_mean, 4),
    # 'TIPhG_R_median': round(TIPhG_R_median, 4),
    # 'TIPhG_R_std': round(TIPhG_R_std, 4),
    # 'THPhG_L_mean': round(THPhG_L_mean, 4),
    # 'THPhG_L_median': round(THPhG_L_median, 4),
    # 'THPhG_L_std': round(THPhG_L_std, 4),
    # 'THPhG_R_mean': round(THPhG_R_mean, 4),
    # 'THPhG_R_median': round(THPhG_R_median, 4),
    # 'THPhG_R_std': round(THPhG_R_std, 4),
    # 'rHipp_L_mean': round(rHipp_L_mean, 4),
    # 'rHipp_L_median': round(rHipp_L_median, 4),
    # 'rHipp_L_std': round(rHipp_L_std, 4),
    # 'rHipp_R_mean': round(rHipp_R_mean, 4),
    # 'rHipp_R_median': round(rHipp_R_median, 4),
    # 'rHipp_R_std': round(rHipp_R_std, 4),
    # 'cHipp_L_mean': round(cHipp_L_mean, 4),
    # 'cHipp_L_median': round(cHipp_L_median, 4),
    # 'cHipp_L_std': round(cHipp_L_std, 4),
    # 'cHipp_R_mean': round(cHipp_R_mean, 4),
    # 'cHipp_R_median': round(cHipp_R_median, 4),
    # 'cHipp_R_std': round(cHipp_R_std, 4),
    'whole_hippo_mean': round(whole_hippo_mean, 4),
    'whole_hippo_median': round(whole_hippo_median, 4),
    'whole_hippo_std': round(whole_hippo_std, 4),
    'whole_phg_mean': round(whole_phg_mean, 4),
    'whole_phg_median': round(whole_phg_median, 4),
    'whole_phg_std': round(whole_phg_std, 4),
    'whole_putamen_mean': round(whole_putamen_mean, 4),
    'whole_putamen_median': round(whole_putamen_median, 4),
    'whole_putamen_std': round(whole_putamen_std, 4),
    'whole_pallidum_mean': round(whole_pallidum_mean, 4),
    'whole_pallidum_median': round(whole_pallidum_median, 4),
    'whole_pallidum_std': round(whole_pallidum_std, 4),
    'whole_thalamus_mean': round(whole_thalamus_mean, 4),
    'whole_thalamus_median': round(whole_thalamus_median, 4),
    'whole_thalamus_std': round(whole_thalamus_std, 4),
    'whole_caudate_mean': round(whole_caudate_mean, 4),
    'whole_caudate_median': round(whole_caudate_median, 4),
    'whole_caudate_std': round(whole_caudate_std, 4),
    'whole_amygdala_mean': round(whole_amygdala_mean, 4),
    'whole_amygdala_median': round(whole_amygdala_median, 4),
    'whole_amygdala_std': round(whole_amygdala_std, 4),
    'whole_entorhinal_cortex_mean': round(whole_entorhinal_cortex_mean, 4),
    'whole_entorhinal_cortex_median': round(whole_entorhinal_cortex_median, 4),
    'whole_entorhinal_cortex_std': round(whole_entorhinal_cortex_std, 4),
    'whole_fusiform_gyrus_cortex_mean': round(whole_fusiform_gyrus_cortex_mean, 4),
    'whole_fusiform_gyrus_cortex_median': round(whole_fusiform_gyrus_cortex_median, 4),
    'whole_fusiform_gyrus_cortex_std': round(whole_fusiform_gyrus_cortex_std, 4),
    'whole_fusiform_gyrus_WM_mean': round(whole_fusiform_gyrus_WM_mean, 4),
    'whole_fusiform_gyrus_WM_median': round(whole_fusiform_gyrus_WM_median, 4),
    'whole_fusiform_gyrus_WM_std': round(whole_fusiform_gyrus_WM_std, 4),
    'whole_insula_WM_mean': round(whole_insula_WM_mean, 4),
    'whole_insula_WM_median': round(whole_insula_WM_median, 4),
    'whole_insula_WM_std': round(whole_insula_WM_std, 4),
    'whole_superior_temporal_cortex_mean': round(whole_superior_temporal_cortex_mean, 4),
    'whole_superior_temporal_cortex_median': round(whole_superior_temporal_cortex_median, 4),
    'whole_superior_temporal_cortex_std': round(whole_superior_temporal_cortex_std, 4),
    'ktrans_wm_outliers': wm_outliers,
    'ktrans_gm_outliers': gm_outliers,
    'T1_blood_histogram': T1_blood_histogram_path,
    'wm_histogram': ktrans_wm_histogram_path,
    'gm_histogram': ktrans_gm_histogram_path,
    # 'rPhG_L_outliers': rPhG_L_outliers,
    # 'rPhG_R_outliers': rPhG_R_outliers,
    # 'cPhG_L_outliers': cPhG_L_outliers,
    # 'cPhG_R_outliers': cPhG_R_outliers,
    # 'lateral_PPHC_L_outliers': lateral_PPHC_L_outliers,
    # 'lateral_PPHC_R_outliers': lateral_PPHC_R_outliers,
    # 'ECPhG_L_outliers': ECPhG_L_outliers,
    # 'ECPhG_R_outliers': ECPhG_R_outliers,
    # 'TIPhG_L_outliers': TIPhG_L_outliers,
    # 'TIPhG_R_outliers': TIPhG_R_outliers,
    # 'THPhG_L_outliers': THPhG_L_outliers,
    # 'THPhG_R_outliers': THPhG_R_outliers,
    # 'rHipp_L_outliers': rHipp_L_outliers,
    # 'rHipp_R_outliers': rHipp_R_outliers,
    # 'cHipp_L_outliers': cHipp_L_outliers,
    # 'cHipp_R_outliers': cHipp_R_outliers,
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
    # 'rPhG_L_histogram': rPhG_L_histogram_path,
    # 'rPhG_R_histogram': rPhG_R_histogram_path,
    # 'cPhG_L_histogram': cPhG_L_histogram_path,
    # 'cPhG_R_histogram': cPhG_R_histogram_path,
    # 'lateral_PPHC_L_histogram': lateral_PPHC_L_histogram_path,
    # 'lateral_PPHC_R_histogram': lateral_PPHC_R_histogram_path,
    # 'ECPhG_L_histogram': ECPhG_L_histogram_path,
    # 'ECPhG_R_histogram': ECPhG_R_histogram_path,
    # 'TIPhG_L_histogram': TIPhG_L_histogram_path,
    # 'TIPhG_R_histogram': TIPhG_R_histogram_path,
    # 'THPhG_L_histogram': THPhG_L_histogram_path,
    # 'THPhG_R_histogram': THPhG_R_histogram_path,
    # 'rHipp_L_histogram': rHipp_L_histogram_path,
    # 'rHipp_R_histogram': rHipp_R_histogram_path,
    # 'cHipp_L_histogram': cHipp_L_histogram_path,
    # 'cHipp_R_histogram': cHipp_R_histogram_path,
    'whole_hippo_histogram': whole_hippo_histogram_path,
    'whole_phg_histogram': whole_phg_histogram_path,
    'whole_putamen_histogram': whole_putamen_histogram_path,
    'whole_pallidum_histogram': whole_pallidum_histogram_path,
    'whole_thalamus_histogram': whole_thalamus_histogram_path,
    'whole_caudate_histogram': whole_caudate_histogram_path,
    'whole_amygdala_histogram': whole_amygdala_histogram_path,
    'whole_entorhinal_cortex_histogram': whole_entorhinal_cortex_histogram_path,
    'whole_fusiform_gyrus_cortex_histogram': whole_fusiform_gyrus_cortex_histogram_path,
    'whole_fusiform_gyrus_WM_histogram': whole_fusiform_gyrus_WM_histogram_path,
    'whole_insula_WM_histogram': whole_insula_WM_histogram_path,
    'whole_superior_temporal_cortex_histogram': whole_superior_temporal_cortex_histogram_path
}

output = template.render(data)

# write html to file
with open(dir + '/population_report' + output_dir + '.html', 'w') as f:
    f.write(output)

print('Report generated in ' + dir + '/population_report.html')

# add apoe and cdr fields to population_data
# get apoe and cdr values from /media/network_mriphysics/USC-PPG/GIGA_DATA/Ararat_CBF_cases_better_format.xlsx
# read in excel file, second sheet "Sheet2"
df = pd.read_excel('/media/network_mriphysics/USC-PPG/GIGA_DATA/Ararat_CBF_cases_better_format.xlsx', sheet_name="Sheet2")

# get apoe and cdr values for each subject
for subject in population_data.keys():
    # get subject's ID
    subject_id = subject.split("_")[0]
    # get subject's timepoint
    timepoint = subject.split("_")[1]
    # get subject's apoe and cdr values
    try:
        apoe = df.loc[df['ID'] == int(subject_id), 'apoebin'].values[0]
        cdr = df.loc[df['ID'] == int(subject_id), 'CDR'].values[0]
        # add to population_data
        population_data[subject]["apoebin"] = apoe
        population_data[subject]["CDR"] = cdr
    except Exception as e:
        print(e)
        print("Subject " + subject_id + " not found in Ararat_CBF_cases_better_format.xlsx")

# make excel file
# make dataframe
df = pd.DataFrame(population_data)
order = ["apoebin", "CDR", "aif_metric", "wm_median", "gm_median", "Ktrans_Hippo_median", "Ktrans_PhG_median", "Ktrans_Putamen_median", "Ktrans_Pallidum_median",
         "Ktrans_Thalamus_median", "Ktrans_Caudate_median", "Ktrans_Amygdala_median", "Ktrans_Entorhinal_cortex_median",
         "Ktrans_Fusiform_gyrus_cortex_median", "Ktrans_Fusiform_gyrus_WM_median", "Ktrans_Insula_WM_median",
         "Ktrans_Superior_temporal_cortex_median"]

df = df.T
df = df[order]
# write to excel
df.to_excel(os.path.join(dir, "dataset_ktrans" + output_dir + ".xlsx"))

# now backfill each subject's placement in the population
for subject_id in subjects:
    # list _timepoint directories in subject directory
    for timepoint in os.listdir(os.path.join(dir, subject_id)):
        if timepoint.endswith("_timepoint"):
            placement_wm_histogram_path = os.path.join(dir, subject_id, timepoint, output_dir, "figures/placement_wm_histogram.png")
            placement_gm_histogram_path = os.path.join(dir, subject_id, timepoint, output_dir, "figures/placement_gm_histogram.png")

            # get subject's wm_mean
            try:
                case_wm_median = population_data[subject_id + "_" + timepoint]["wm_median"]
                case_gm_median = population_data[subject_id + "_" + timepoint]["gm_median"]
            except Exception as e:
                print(e)
                continue

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
            filename = os.path.join(dir, subject_id, timepoint, output_dir, "case_report.html")
            print(filename)
            with open(filename, "r") as f:
                report_content = f.read()

            # replace placeholder with histogram path
            report_content = report_content.replace("placeholder_wm", placement_wm_histogram_path)
            report_content = report_content.replace("placeholder_gm", placement_gm_histogram_path)
            # write html to file
            with open(filename, 'w') as f:
                f.write(report_content)
