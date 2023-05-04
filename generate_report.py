import datetime
import os
import sys
import time
from jinja2 import Template, FileSystemLoader, Environment

dir = sys.argv[1]
print(dir)

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('template.html')

data = {
    'title': 'My Image Report',
    'heading': 'Welcome to my image report!',
    'body': 'This is the body of my report.',
    'image_path1': 'C:\\Users\\thero\\Pictures\\Noggin.png',
    'image_alt1': 'My image1',
    'image_path2': 'C:\\Users\\thero\\Pictures\\Capture.png',
    'image_alt2': 'My image2'
}

output = template.render(data)

with open('output.html', 'w') as f:
    f.write(output)

print('Report generated!')