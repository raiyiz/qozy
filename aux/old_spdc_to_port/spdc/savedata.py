# Code by Ilija Funk, last edited 13.02.2025, version 0.1
# This module contains functions to write data into txt files and save them in a year/month/day folder structure.
# Needs os, numpy, datetime.

import os
import numpy as np
from datetime import datetime

def generate_file_number(folder_path):
	for i in range(1,100):
		file_number = f'{i:02d}'
		if not os.path.exists(os.path.join(folder_path, file_number + '.txt')): #searches for files like "01.txt"
			return file_number
	return None # there are already 100 files

def generate_folder_path():
	now = datetime.now()
	folder_path = os.path.join('/home/sci/qkd/data',str(now.year),str(now.month).zfill(2),str(now.day).zfill(2),'')
	print(folder_path)
	os.makedirs(folder_path, exist_ok = True)
	return folder_path

def save_txt(data):
	folder_path = generate_folder_path()
	file_number = generate_file_number(folder_path)
	file_name = str(file_number) + '.txt'
	np.savetxt(folder_path + file_name, data, delimiter='\t', fmt='%f')