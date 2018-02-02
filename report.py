from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import math
import statistics
import numpy as np

class TestResult():

    def __init__(self, data):
        self.data = data

    @property
    def size(self):
        return len(self.data)

    @property
    def rms(self):
        return math.sqrt(sum(x ** 2 for x in self.data) / len(self.data))

    @property
    def mean(self):
        return statistics.mean(self.data)

    @property
    def stdev(self):
        return statistics.stdev(self.data)


class Reporter:

    def __init__(self):
        self.results = {}    # fold => TestResult
        self.totals = None   # TestResult

    def run(self, directory):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.directory = directory
        self.read_results()  # from the result_*.csv files
        self.read_losses()   # from the loss_*.csv files
        if PAR.WORKFLOW == 'DEVELOPMENT':
            self.calc_totals()   # over all fold results
        # self.show_report()   # on the terminal
        self.write_report()  # to report.csv
        LOG.leave()

    def read_results(self):
        LOG.enter('reading results')
        LOG.message('from {}'.format(self.directory))
        if PAR.WORKFLOW == 'DEVELOPMENT':
            for fold in range(PAR.FOLDS):
                LOG.enter('fold {}'.format(fold))
                basename = 'result_{}.csv'.format(fold)
                LOG.message('from {}'.format(basename))
                path = str(self.directory / basename)
                with CSV.FileReader(path) as source:
                    assert next(source) == ['PRAKTIJK', 'PATIENT-ID', 'OUDERDOM', 'ARGMAX', 'PREDICTION']
                    data = [int(row[2]) - int(row[3]) for row in source]  # actual - predicted life expectancy
                self.results[fold] = TestResult(data)
                LOG.leave()
        elif PAR.WORKFLOW == 'VALIDATION':
            basename = 'result.csv'
            LOG.message('from {}'.format(basename))
            path = str(self.directory / basename)
            with CSV.FileReader(path) as source:
                assert next(source) == ['PRAKTIJK', 'PATIENT-ID', 'OUDERDOM', 'ARGMAX', 'PREDICTION']
                data = [int(row[2]) - int(row[3]) for row in source]  # actual - predicted life expectancy
            self.results = TestResult(data)
        LOG.leave()

    def read_losses(self):
        LOG.enter('reading losses')
        if PAR.WORKFLOW == 'DEVELOPMENT':
            fold_data = []
            for fold in range(PAR.FOLDS):
                LOG.enter('fold {}'.format(fold))
                basename = 'loss_{}.csv'.format(fold)
                LOG.message('from {}'.format(basename))
                path = str(self.directory / basename)
                with CSV.FileReader(path) as source:
                    assert next(source) == ['EPOCH', 'TRAIN', 'TEST']
                    data = [(float(train_loss), float(test_loss)) for epoch, train_loss, test_loss in source]
                    fold_data.append(data)
                LOG.leave()
            # Average over folds
            avg_data = []
            for epoch in range(PAR.EPOCHS):
                avg_train = sum(fold_data[fold][epoch][0] for fold in range(PAR.FOLDS)) / PAR.FOLDS
                avg_test = sum(fold_data[fold][epoch][1] for fold in range(PAR.FOLDS)) / PAR.FOLDS
                avg_data.append((epoch, avg_train, avg_test))
            # Get data where test_loss is minimal
            self.losses = min(avg_data, key=lambda t: t[2])
        elif PAR.WORKFLOW == 'VALIDATION':
            fold_data = []
            basename = 'loss.csv'
            LOG.message('from {}'.format(basename))
            path = str(self.directory / basename)
            with CSV.FileReader(path) as source:
                assert next(source) == ['EPOCH', 'TRAIN', 'TEST']
                data = [(epoch, float(train_loss), float(test_loss)) for epoch, train_loss, test_loss in source]
            # Get data where test_loss is minimal
            self.losses = min(data, key=lambda t: t[2])
        LOG.leave()

    def calc_totals(self):
        data = sum((result.data for result in self.results.values()), [])
        self.totals = TestResult(data)

    def show_report(self):
        print('  fold     windows     rms      mean      stdev')
        print('--------  --------  --------  --------  --------')
        for fold in range(PAR.FOLDS):
            result = self.results[fold]
            print('{0:5d}     {1.size:6d}     {1.rms:6.3f}    {1.mean:6.3f}    {1.stdev:6.3f}'.format(fold, result))
        if self.totals:
            print('--------  --------  --------  --------  --------')
            print('  total   {0.size:6d}     {0.rms:6.3f}    {0.mean:6.3f}    {0.stdev:6.3f}'.format(self.totals))

    def write_report(self):
        LOG.enter('writing report')
        path = str(self.directory / 'report.csv')
        LOG.message('to {}'.format(path))
        with CSV.FileWriter(path) as target:
            if PAR.WORKFLOW == 'DEVELOPMENT':
                headers = ['FOLD', 'WINDOWS', 'RMS', 'MEAN', 'STDEV']
                target.writerow(headers)
                for fold in range(PAR.FOLDS):
                    result = self.results[fold]
                    target.writerow([fold, result.size, result.rms, result.mean, result.stdev])
                target.writerow(['total', self.totals.size, self.totals.rms, self.totals.mean, self.totals.stdev])
                target.writerow([])
                target.writerow(['TRAIN-LOSS', self.losses[1]])
                target.writerow(['TEST-LOSS', self.losses[2]])
                target.writerow(['EPOCH', self.losses[0]])
            elif PAR.WORKFLOW == 'VALIDATION':
                headers = ['FOLD', 'WINDOWS', 'RMS', 'MEAN', 'STDEV']
                target.writerow(headers)
                result = self.results
                target.writerow(['total', result.size, result.rms, result.mean, result.stdev])
                target.writerow([])
                target.writerow(['TRAIN-LOSS', self.losses[1]])
                target.writerow(['TEST-LOSS', self.losses[2]])
                target.writerow(['EPOCH', self.losses[0]])
        LOG.leave()

# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    if PAR.WORKDLOW == 'DEVELOPMENT':
        Reporter().run(CFG.PHASE3_DIR)
    elif PAR.WORKDLOW == 'VALIDATION':
        Reporter().run(CFG.PHASE4_DIR)
    LOG.leave()
