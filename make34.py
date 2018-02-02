from support import config as CFG
from support import logging as LOG
from support import parameters as PAR

from filter_kwd import KeywordFilter
from filter_evt import EventFilter
from get_histories import HistoryGenerator
from xsplit import Splitter
from model import TensorFlower
from report import Reporter
from filter_trajectories import IllnessTrajectoryFilter
from exp_summ import ExperimentSummarizer


import getopt
import os
import sys


class Phase3Maker:

    def run(self):
        self.parse_cmdline()
        LOG.enter(self.__class__.__name__ + '.run()')
        self.make_tree(CFG.EXPERIMENT_DIR) if self.make_all else self.make_dirs()
        LOG.leave()

    def parse_cmdline(self):
        self.make_all = False
        self.rebuild = False
        opts, self.directories = getopt.getopt(sys.argv[1:], 'arv:', ['all', 'rebuild', 'verbosity='])
        for opt, val in opts:
            if opt in ("-a", "--all"):
                self.make_all = True
            elif opt in ('-r', '--rebuild'):
                self.rebuild = True
            elif opt in ('-v', '--verbosity'):
                LOG.levels = int(val)

    # Make all experiments found recursively in the Experiments tree.
    def make_tree(self, directory):
        for path in directory.glob('**'):
            if path.is_dir() and (path / 'param.txt').is_file():
                self.make(path)
        ExperimentSummarizer().run(directory)

    # Make experiments in the directories specified on the command line.
    def make_dirs(self):
        for directory in self.directories:
            directory = CFG.EXPERIMENT_DIR / directory
            self.make_tree(directory)

    # Build the specified directory if necessary.
    def make(self, directory):
        must_build = self.must_build(directory)
        name = str(directory).split('/Experiment/')[1]
        LOG.enter(name)
        if must_build:
            LOG.enter('building')
            self.build(directory)
            LOG.leave()
        else:
            LOG.message('up to date')
        LOG.leave()

    # Do we need to build the specified directory?
    def must_build(self, directory):
        param = directory / 'param.txt'
        report = directory / 'report.csv'
        if not param.is_file(): return False    # Cannot build without a param.txt file
        if self.rebuild: return True            # Command-line option --rebuild present
        if not report.is_file(): return True    # Report is missing, so build it
        ptime = os.path.getmtime(str(param))
        rtime = os.path.getmtime(str(report))
        if ptime > rtime: return True           # Parameters changed since the last build
        return False                            # Everything seems to be up to date

    def build(self, directory):
        PAR.read(directory)
        KeywordFilter().run(directory)
        EventFilter().run(directory)
        HistoryGenerator().run(directory)
        if PAR.WORKFLOW == 'DEVELOPMENT':
            Splitter().run(directory)
        TensorFlower().run(directory)
        Reporter().run(directory)
        IllnessTrajectoryFilter().run(directory)

if __name__ == '__main__':
    LOG.enter(__file__)
    Phase3Maker().run()
    LOG.leave()
