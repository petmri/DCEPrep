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

for subject_id in subjects:
    # list _timepoint directories in subject directory
    for timepoint in os.listdir(os.path.join(dir, subject_id)):
        if timepoint.endswith("_timepoint"):
            # print(timepoint)
            # read wm and gm data from html file
            filename = os.path.join(dir, subject_id, timepoint, "case_report.html")
            # print(filename)
            # try:
            with open(filename, "r") as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    # wm_mean = 0
                    # wm_median = 0
                    # wm_std = 0
                    # gm_mean = 0
                    # gm_median = 0
                    # gm_std = 0
                    if "Mean Ktrans (wm)" in line:
                        wm_mean = float(lines[i].split(':')[1][:-7])
                        # wm_median = float(lines[i + 2].split()[1])
                        wm_std = float(lines[i + 1].split(':')[1][:-7])
                    if "Mean Ktrans (gm)" in line:
                        gm_mean = float(lines[i].split(':')[1][:-7])
                        # gm_median = float(lines[i + 2].split()[1])
                        gm_std = float(lines[i + 1].split(':')[1][:-7])
            entry = subject_id + "_" + timepoint
            print(wm_mean, wm_std, gm_mean, gm_std)
            population_data[entry] = {
                "wm_mean": wm_mean,
                # "wm_median": wm_median,
                "wm_std": wm_std,
                "gm_mean": gm_mean,
                # "gm_median": gm_median,
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
    # print(population_data[entry]["wm_mean"])
    # print(population_data[entry]["wm_std"])
    # print(population_data[entry]["gm_mean"])
    # print(population_data[entry]["gm_std"])
wm_mean = np.mean([population_data[entry]["wm_mean"] for entry in population_data])
wm_std = np.mean([population_data[entry]["wm_std"] for entry in population_data])
gm_mean = np.mean([population_data[entry]["gm_mean"] for entry in population_data])
gm_std = np.mean([population_data[entry]["gm_std"] for entry in population_data])
# convert to 10^-3
wm_mean = wm_mean * 1000
wm_std = wm_std * 1000
gm_mean = gm_mean * 1000
gm_std = gm_std * 1000
print(wm_mean)
print(wm_std)
print(gm_mean)
print(gm_std)

# make histogram from each timepoint mean
histogram = []
for entry in population_data.keys():
    histogram.append(population_data[entry]["wm_mean"])

# plot histogram
plt.hist(histogram, bins=10)
# plt.show()
wm_histogram_path = os.path.join(dir, "wm_histogram.png")
plt.savefig(wm_histogram_path, bbox_inches='tight')
plt.close()

# now get gm mean histogram
histogram = []
for entry in population_data.keys():
    histogram.append(population_data[entry]["gm_mean"])

# plot histogram
plt.hist(histogram, bins=10)
# plt.show()
gm_histogram_path = os.path.join(dir, "gm_histogram.png")
plt.savefig(gm_histogram_path, bbox_inches='tight')


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
    'Date': date,
    'Commit': commit_hash,
    'wm_mean': wm_mean,
    'wm_std': wm_std,
    'gm_mean': gm_mean,
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
            placement_histogram_path = os.path.join(dir, subject_id, timepoint, "placement_histogram.png")
            # append to html file
            filename = os.path.join(dir, subject_id, timepoint, "case_report.html")
            print(filename)
            with open(filename, "w") as f:
                report_content = f.read()

            report_content = report_content.replace("{{ placement }}", placement_histogram_path)
