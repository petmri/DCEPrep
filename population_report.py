import h5py
import jinja2
import os
import matplotlib
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

# Load MRI population data dict with keys as subject IDs and values as gm and wm data
population_data = {}
# list directories in dir
subjects = os.listdir(dir)
# filter out non-directories
subjects = [subject for subject in subjects if os.path.isdir(os.path.join(dir, subject))]

count = 0
wm_outliers = []
gm_outliers = []
for subject_id in subjects:
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
            count += 1
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
                            print(subject_id + "_" + timepoint + " has a wm_median of " + str(wm_median) + "!")
                            wm_outliers.append(subject_id + "_" + timepoint)
                        if gm_median > 5:
                            print(subject_id + "_" + timepoint + " has a gm_median of " + str(gm_median) + "!")
                            gm_outliers.append(subject_id + "_" + timepoint)
            except Exception as e:
                print("Error reading " + filename)
                print(e)
                continue

            # read lines after "AIF mmol:"
            aif_mmol = []
            B_log = os.path.join(dir, subject_id, timepoint, output_dir, "B_dcefitted_R1info.log")
            with open(B_log, 'r') as f:
                for line in f:
                    if "AIF mmol:" in line:
                        aif_mmol = f.readlines()
                        # find index of line after last numbers ("MAT results saved to: \n")
                        lastline = aif_mmol.index("MAT results saved to: \n")
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

            entry = subject_id + "_" + timepoint
            population_data[entry] = {
                "aif_metric": aif_metric,
                "aif_mmol": aif_mmol,
                "T1_wm_median": T1_wm_median,
                # T1_wm_std: T1_wm_std,
                "T1_gm_median": T1_gm_median,
                # T1_gm_std: T1_gm_std,
                # "wm_mean": wm_mean,
                "wm_median": wm_median,
                # "wm_std": wm_std,
                # "gm_mean": gm_mean,
                "gm_median": gm_median,
                # "gm_std": gm_std
            }
AIFitness_values = [float(population_data[entry]["aif_metric"]) for entry in population_data]
AIFitness_mean = np.mean(AIFitness_values)
AIFitness_median = np.median(AIFitness_values)
AIFitness_std = np.std(AIFitness_values)
AIFitness_5th_percentile = np.percentile(AIFitness_values, 5)

aif_mmol_mean = np.mean([population_data[entry]["aif_mmol"] for entry in population_data])
aif_mmol_median = np.median([population_data[entry]["aif_mmol"] for entry in population_data])
aif_mmol_std = np.std([population_data[entry]["aif_mmol"] for entry in population_data])
aif_mmol_5th_percentile = np.percentile([population_data[entry]["aif_mmol"] for entry in population_data], 5)
aif_mmol_95th_percentile = np.percentile([population_data[entry]["aif_mmol"] for entry in population_data], 95)

T1_wm_mean = np.mean([population_data[entry]["T1_wm_median"] for entry in population_data])
T1_wm_median = np.median([population_data[entry]["T1_wm_median"] for entry in population_data])
T1_wm_std = np.std([population_data[entry]["T1_wm_median"] for entry in population_data])
T1_wm_5th_percentile = np.percentile([population_data[entry]["T1_wm_median"] for entry in population_data], 5)
T1_wm_95th_percentile = np.percentile([population_data[entry]["T1_wm_median"] for entry in population_data], 95)

T1_gm_mean = np.mean([population_data[entry]["T1_gm_median"] for entry in population_data])
T1_gm_median = np.median([population_data[entry]["T1_gm_median"] for entry in population_data])
T1_gm_std = np.std([population_data[entry]["T1_gm_median"] for entry in population_data])
T1_gm_5th_percentile = np.percentile([population_data[entry]["T1_gm_median"] for entry in population_data], 5)
T1_gm_95th_percentile = np.percentile([population_data[entry]["T1_gm_median"] for entry in population_data], 95)

wm_mean = np.mean([population_data[entry]["wm_median"] for entry in population_data])
wm_median = np.median([population_data[entry]["wm_median"] for entry in population_data])
wm_std = np.std([population_data[entry]["wm_median"] for entry in population_data])
gm_mean = np.mean([population_data[entry]["gm_median"] for entry in population_data])
gm_median = np.median([population_data[entry]["gm_median"] for entry in population_data])
gm_std = np.std([population_data[entry]["gm_median"] for entry in population_data])

# if no outliers, set to "None"
if len(wm_outliers) == 0:
    wm_outliers = "None"
if len(gm_outliers) == 0:
    gm_outliers = "None"

# make AIFitness histogram
plt.hist(AIFitness_values, bins=30)
plt.title("AIFitness Median")
plt.xlabel("AIFitness")
aifitness_histogram_path = os.path.join(dir, output_dir + "aifitness_histogram.png")
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
aif_mmol_histogram_path = os.path.join(dir, output_dir + "aif_mmol_histogram.png")
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
ktrans_wm_histogram_path = os.path.join(dir, output_dir + "wm_histogram.png")
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
ktrans_gm_histogram_path = os.path.join(dir, output_dir + "gm_histogram.png")
# save range of histogram for later use
gm_histogram_range = plt.xlim()
plt.savefig(ktrans_gm_histogram_path, bbox_inches='tight')
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

data = {
    'Subjects' : subjects,
    'Subject_count': len(subjects),
    'Cases': str(len(population_data)) + '/' + str(count) + ' (' + str(round((len(population_data) / count) * 100, 2)) + '% success)',
    'Date': date,
    'Commit': commit_hash,
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
    'ktrans_wm_outliers': wm_outliers,
    'ktrans_gm_outliers': gm_outliers,
    'wm_histogram': ktrans_wm_histogram_path,
    'gm_histogram': ktrans_gm_histogram_path
}

output = template.render(data)

# write html to file
with open(dir + '/population_report' + output_dir + '.html', 'w') as f:
    f.write(output)

print('Report generated in ' + dir + '/population_report.html')

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
