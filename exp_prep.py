from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import getopt
import sys

class ExperimentPreparator:

    def help(self):
        print()
        print('Prepares experiments by creating subdirectories, each containing a param.txt file,')
        print('as defined by the contents of an experiment.csv file.')
        print()
        print('Syntax:')
        print()
        print('    python exp_prep.py [\x1B[4moption\x1B[0m...] \x1B[4mexperiment\x1B[0m...')
        print()
        print('where each \x1B[4mexperiment\x1B[0m is a directory in palliatie/Experiment containing an')
        print('experiment.csv file and a default param.txt file.')
        print()
        print('The following \x1B[4moptions\x1B[0m exist:')
        print()
        print('    -h, --help    Print this help text.')
        exit()

    def run(self):
        self.parse_cmdline()
        for experiment in self.experiments:
            self.prepare(experiment)

    def parse_cmdline(self):
        opts, self.experiments = getopt.getopt(sys.argv[1:], 'h', ['help'])
        for opt, val in opts:
            if opt in ('-h', '--help'):
                self.help()  # Does not return

    def prepare(self, experiment):
        experiment_dir = CFG.EXPERIMENT_DIR / experiment
        self.read_default_params(str(experiment_dir / 'default_param.txt'))
        with CSV.FileReader(experiment_dir / 'experiment.csv') as source:
            headers = list(map(str.strip, next(source)))
            assert headers[0] == 'SUBDIR'
            tweak_keys = headers[1:]
            for row in source:
                row = list(map(str.strip, row))
                subdir, tweak_values = row[0], row[1:]
                tweaks = dict(zip(tweak_keys, tweak_values))
                exp_params = self.tweak_params(tweaks)
                subexp_dir = experiment_dir / subdir
                print(subexp_dir)
                subexp_dir.mkdir()
                param_file = subexp_dir / 'param.txt'
                self.write_experiment_params(str(param_file), exp_params)

    # Gets the default parameters as a list of (key, value) pairs.
    # Blank lines and comments are dropped.
    def read_default_params(self, filename):
        with open(filename) as source:
            self.default_params = []
            for line in source:
                comment = line.find('#')
                if comment >= 0:
                    line = line[:comment].rstrip()
                if '=' in line:
                    param, value = map(str.strip, line.split('='))
                    self.default_params.append((param, value))

    def write_experiment_params(self, filename, params):
        with open(filename, 'w') as target:
            for key, value in params:
                target.write('{} = {}\n'.format(key, value))

    def tweak_params(self, tweaks):
        params = []
        for key, value in self.default_params:
            if key in tweaks:
                value = tweaks[key]
            params.append((key, value))
        return params

# Main program
if __name__ == '__main__':
    ExperimentPreparator().run()
