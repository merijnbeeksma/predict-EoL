from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG

from collections import namedtuple
import getopt
import sys


class SummaryLine:

    def __init__(self, subdir):
        self.subdir = subdir
        self.rms = None
        self.mean = None
        self.stdev = None
        self.train_loss = None
        self.test_loss = None
        self.epoch = None


class ExperimentSummarizer:

    def run(self, directory):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.summarize(directory)
        LOG.leave()

    def summarize(self, experiment):
        LOG.enter('Experiment {}'.format(experiment))
        self.experiment_dir = CFG.EXPERIMENT_DIR / experiment
        self.get_subdirs()
        self.get_summary()
        self.write_summary()
        LOG.leave()

    def get_subdirs(self):
        filename = self.experiment_dir / 'experiment.csv'
        LOG.message('Reading {}'.format(filename))
        with CSV.FileReader(filename) as source:
            headers = list(map(str.strip, next(source)))
            assert headers[0] == 'SUBDIR'
            self.subdirs = [row[0] for row in source]

    def get_summary(self):
        self.summary = []
        for subdir in self.subdirs:
            summary_line = SummaryLine(subdir)
            filename = self.experiment_dir / subdir / 'report.csv'
            LOG.message('Reading {}'.format(filename))
            with CSV.FileReader(filename) as source:
                for row in source:
                    if len(row) == 0: continue
                    if row[0] == 'total':
                        summary_line.rms = row[2]
                        summary_line.mean = row[3]
                        summary_line.stdev = row[4]
                    elif row[0] == 'TRAIN-LOSS':
                        summary_line.train_loss = row[1]
                    elif row[0] == 'TEST-LOSS':
                        summary_line.test_loss = row[1]
                    elif row[0] == 'EPOCH':
                        summary_line.epoch = row[1]
            self.summary.append(summary_line)

    def write_summary(self):
        filename = self.experiment_dir / 'summary.csv'
        LOG.message('Writing {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['SUBDIR', 'RMS', 'MEAN', 'STDEV', 'TRAIN-LOSS', 'TEST-LOSS', 'EPOCH'])
            for s in self.summary:
                target.writerow([s.subdir, s.rms, s.mean, s.stdev, s.train_loss, s.test_loss, s.epoch])


# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    for experiment in sys.argv[1:]:
        ExperimentSummarizer().run(experiment)
    LOG.leave()

