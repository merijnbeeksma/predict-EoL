# Captures common idiom for working with CSV files.
# Recurring details, such as text encoding and CSV delimiters,
# are also handled here.

import csv
import sys

csv.field_size_limit(sys.maxsize)

# Opens a text file for reading and places a CSV reader on it.
class FileReader():

    def __init__(self, filename):
        self.filename = str(filename)

    def __enter__(self):
        self.data_file = open(self.filename, 'r', encoding='utf-8-sig')
        self.csv_reader = csv.reader(self.data_file, delimiter=';')
        return self.csv_reader

    def __exit__(self, *args):
        self.data_file.close()


# Not a broken reader for CSV files, but a reader for broken CSV files.
#   Although CSV files are supposed to contain plain text, some of the
# CSV files in this project's corpus contain stray control codes, such
# as 0x00 and 0x0B, that crash an ordinary CSV reader.
#   This reader reads such a broken CSV file into memory, replaces the
# control codes with spaces, and places a CSV reader on the result.
#   Because of the extra memory requirement, use only when a regular
# FileReader won't work.
class BrokenFileReader():

    controls = bytes(n for n in range(32) if chr(n) not in '\n\r')
    table = bytes.maketrans(controls, len(controls) * b' ')

    def __init__(self, filename):
        self.filename = str(filename)

    def __enter__(self):
        with open(self.filename, 'rb') as data_file:
            self.data = data_file.read()
        self.data = self.data.translate(self.table)
        self.data = self.data.decode('utf-8-sig')
        self.data = self.data.splitlines()
        self.csv_reader = csv.reader(self.data, delimiter=';')
        return self.csv_reader

    def __exit__(self, *args):
        pass


# Opens a text file for writing and places a CSV writer on it.
class FileWriter():

    def __init__(self, filename, mode='w'):
        self.filename = str(filename)
        self.mode = mode

    def __enter__(self):
        self.data_file = open(self.filename, self.mode, encoding='utf-8')
        self.csv_writer = csv.writer(self.data_file, delimiter=';', lineterminator='\n')
        return self.csv_writer

    def __exit__(self, *args):
        self.data_file.close()
