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


class FilterExperimentSummarizer:

    def run(self, directory):
        LOG.enter(self.__class__.__name__ + '.run()')
        for filter in PAR.FILTER_RESULTS:
            self.run_filter(directory, filter[0])

    def summarize(self, experiment, filter):
        LOG.enter('Experiment {}'.format(experiment))
        self.experiment_dir = CFG.EXPERIMENT_DIR / experiment
        self.get_subdirs()
        self.get_summary(filter)
        self.write_summary()
        LOG.leave()

    def get_subdirs(self):
        filename = self.experiment_dir / 'experiment.csv'
        LOG.message('Reading {}'.format(filename))
        with CSV.FileReader(filename) as source:
            headers = list(map(str.strip, next(source)))
            assert headers[0] == 'SUBDIR'
            self.subdirs = [row[0] for row in source]

    def get_summary(self, filter):
        self.summary = []
        for subdir in self.subdirs:
            summary_line = SummaryLine(subdir)
            filename = self.experiment_dir / subdir / 'report_filters.csv'
            LOG.message('Reading {}'.format(filename))
            with CSV.FileReader(filename) as source:
                for row in source:
                    if row and row[0] == filter:
                        summary_line.rms = row[3]
                        summary_line.mean = row[4]
                        summary_line.stdev = row[5]
            self.summary.append(summary_line)

    def write_summary(self, filter):
        filename = self.experiment_dir / 'summary_{}.csv'.format(filter)
        LOG.message('Writing {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['SUBDIR', 'RMS', 'MEAN', 'STDEV'])
            for s in self.summary:
                target.writerow([s.subdir, s.rms, s.mean, s.stdev])


# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    for experiment in sys.argv[1:]:
        FilterExperimentSummarizer().run(experiment)
    LOG.leave()
