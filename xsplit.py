from support import config as CFG
from support import logging as LOG
from support import parameters as PAR

import os
import random


FOLDS = 10  # Always use 10-fold cross validation


class Splitter:

    def run(self, directory):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.clean_up(directory)
        self.read_data(directory)
        self.randomize()
        for fold in range(FOLDS):
            LOG.enter('fold {}'.format(fold))
            self.write_train(directory, fold)
            self.write_test(directory, fold)
            LOG.leave()
        LOG.leave()

    # Remove old output files.
    def clean_up(self, directory):
        LOG.enter('cleaning up old files')
        LOG.message('in {}'.format(directory))
        for file in directory.glob('train_*.csv'):
            LOG.message('removing {}'.format(file))
            os.remove(str(file))
        for file in directory.glob('test_*.csv'):
            LOG.message('removing {}'.format(file))
            os.remove(str(file))
        LOG.leave()

    def read_data(self, directory):
        LOG.enter('reading histories')
        path = str(directory / 'modeldata.csv')
        LOG.message('from {}'.format(path))
        with open(path, encoding='utf-8') as source:
            self.headers = next(source)
            self.data = [line for line in source]
        LOG.leave()

    def randomize(self):
        # Specify a seed if repeatable randomness is wanted.
        random.seed(1234)  # Any integer
        random.shuffle(self.data)

    # Write the training data for a given fold.
    # If fold is 7, all lines are copied except line 7, 17, 27...
    def write_train(self, directory, fold):
        path = os.path.abspath(str(directory / 'train_{}.csv'.format(fold)))
        LOG.message(str(path))
        with open(path, 'w', encoding='utf-8') as target:
            target.write(self.headers)
            for line_number, line in enumerate(self.data):
                if line_number % FOLDS != fold:
                    target.write(line)

    # Write the test data for a given fold.
    # If fold is 7, the lines numbered 7, 17, 27... are copied.
    def write_test(self, directory, fold):
        path = os.path.abspath(str(directory / 'test_{}.csv'.format(fold)))
        LOG.message(str(path))
        with open(path, 'w', encoding='utf-8') as target:
            target.write(self.headers)
            for line_number, line in enumerate(self.data):
                if line_number % FOLDS == fold:
                    target.write(line)


# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    Splitter().run(CFG.PHASE3_DIR)
    LOG.leave()
