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
# Load MRI population data dict with keys as subject IDs and values as gm and wm data
population_data = {}
# list directories in dir
subjects = os.listdir(dir)
# filter out non-directories
subjects = [subject for subject in subjects if os.path.isdir(os.path.join(dir, subject))]

count = 0
for subject_id in subjects:
    # list _timepoint directories in subject directory
    for timepoint in os.listdir(os.path.join(dir, subject_id)):
        wm_mean = 0
        wm_median = 0
        wm_std = 0
        gm_mean = 0
        gm_median = 0
        gm_std = 0
        if timepoint.endswith("_timepoint"):
            count += 1
            # print(timepoint)
            # read wm and gm data from html file
            filename = os.path.join(dir, subject_id, timepoint, "case_report.html")
            # print(filename)
            # try:
            try:
                with open(filename, "r") as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if "Median wm Ktrans" in line:
                            # wm_mean = float(lines[i].split(':')[1][:-6])
                            wm_median = float(lines[i].split()[-1][:-6])
                            wm_std = float(lines[i + 1].split(':')[-1][:-6])
                        if "Median gm Ktrans" in line:
                            # gm_mean = float(lines[i].split(':')[1][:-6])
                            gm_median = float(lines[i].split()[-1][:-6])
                            gm_std = float(lines[i + 1].split(':')[-1][:-6])
            except Exception as e:
                print(e)
                continue
            entry = subject_id + "_" + timepoint
            # print(wm_mean, wm_std, gm_mean, gm_std)
            population_data[entry] = {
                # "wm_mean": wm_mean,
                "wm_median": wm_median,
                "wm_std": wm_std,
                # "gm_mean": gm_mean,
                "gm_median": gm_median,
                "gm_std": gm_std
            }
            # except:
            #     continue
# print(population_data[1101743_runner_1st_timepoint])
# print(population_data[subject_id]["wm_mean"])
# print(population_data[subject_id]["wm_std"])
# print(population_data[subject_id]["gm_mean"])
# print(population_data[subject_id]["gm_std"])
# get population mean and std
# print(population_data.keys())
# print(population_data)
# for entry in population_data.keys():
#     print(entry)
#     print(population_data[entry]["wm_median"])
#     print(population_data[entry]["wm_std"])
#     print(population_data[entry]["gm_median"])
#     print(population_data[entry]["gm_std"])
wm_mean = np.mean([population_data[entry]["wm_median"] for entry in population_data])
wm_median = np.median([population_data[entry]["wm_median"] for entry in population_data])
wm_std = np.std([population_data[entry]["wm_median"] for entry in population_data])
gm_mean = np.mean([population_data[entry]["gm_median"] for entry in population_data])
gm_median = np.median([population_data[entry]["gm_median"] for entry in population_data])
gm_std = np.std([population_data[entry]["gm_median"] for entry in population_data])

# make histogram from each timepoint mean
wm_histogram = []
for entry in population_data.keys():
    wm_histogram.append(population_data[entry]["wm_median"])

# plot histogram
plt.hist(wm_histogram, bins=20)
plt.title("White Matter Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
# plt.show()
wm_histogram_path = os.path.join(dir, "wm_histogram.png")
plt.savefig(wm_histogram_path, bbox_inches='tight')
plt.close()

# now get gm mean histogram
gm_histogram = []
for entry in population_data.keys():
    gm_histogram.append(population_data[entry]["gm_median"])

# plot histogram
plt.hist(gm_histogram, bins=20)
plt.title("Gray Matter Median Ktrans")
plt.xlabel("Ktrans (10^-3/min)")
# plt.show()
gm_histogram_path = os.path.join(dir, "gm_histogram.png")
plt.savefig(gm_histogram_path, bbox_inches='tight')
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
    'wm_mean': wm_mean,
    'wm_median': wm_median,
    'wm_std': wm_std,
    'gm_mean': gm_mean,
    'gm_median': gm_median,
    'gm_std': gm_std,
    'wm_histogram': wm_histogram_path,
    'gm_histogram': gm_histogram_path
}

output = template.render(data)

# write html to file
with open(dir + '/population_report.html', 'w') as f:
    f.write(output)

print('Report generated in ' + dir + '/population_report.html')

# now backfill each subject's placement in the population
for subject_id in subjects:
    # list _timepoint directories in subject directory
    for timepoint in os.listdir(os.path.join(dir, subject_id)):
        if timepoint.endswith("_timepoint"):
            print(timepoint)
            placement_wm_histogram_path = os.path.join(dir, subject_id, timepoint, "figures/placement_wm_histogram.png")
            placement_gm_histogram_path = os.path.join(dir, subject_id, timepoint, "figures/placement_gm_histogram.png")

            # get subject's wm_mean
            try:
                case_wm_median = population_data[subject_id + "_" + timepoint]["wm_median"]
                case_gm_median = population_data[subject_id + "_" + timepoint]["gm_median"]
            except Exception as e:
                print(e)
                continue

            # plot histograms
            plt.hist(wm_histogram, bins=20)
            plt.title("Ktrans White Matter Median")
            plt.xlabel("Ktrans (10^-3/min)")
            plt.axvline(x=case_wm_median, color='black')
            # put percentile text in top right corner
            plt.text(0.9, 0.95, "Percentile: " + str(round((len([x for x in wm_histogram if x < case_wm_median]) / len(wm_histogram)) * 100, 2)) + "%", horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
            plt.savefig(placement_wm_histogram_path, bbox_inches='tight')
            plt.close()

            plt.hist(gm_histogram, bins=20)
            plt.title("Ktrans Gray Matter Median")
            plt.xlabel("Ktrans (10^-3/min)")
            plt.axvline(x=case_gm_median, color='black')
            # put percentile text in top right corner
            plt.text(0.9, 0.95, "Percentile: " + str(round((len([x for x in gm_histogram if x < case_gm_median]) / len(gm_histogram)) * 100, 2)) + "%", horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
            plt.savefig(placement_gm_histogram_path, bbox_inches='tight')
            plt.close()

            # append to html file
            filename = os.path.join(dir, subject_id, timepoint, "case_report.html")
            print(filename)
            with open(filename, "r") as f:
                report_content = f.read()

            report_content = report_content.replace("placeholder_wm", placement_wm_histogram_path)
            report_content = report_content.replace("placeholder_gm", placement_gm_histogram_path)
            # write html to file
            with open(filename, 'w') as f:
                f.write(report_content)
