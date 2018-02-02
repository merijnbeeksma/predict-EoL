from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from frog import Frog, FrogOptions
import os

class FrogRunner2:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.instantiate_frog()
        # Handle a possible restart of this program
        LOG.leave()
        LOG.enter('development set')
        progress = self.get_progress('dev')
        if progress:
            self.restart(progress, 'dev')
        else:
            self.new_run('dev')
        LOG.leave()
        LOG.enter('validation set')
        progress = self.get_progress('val')
        if progress:
            self.restart(progress, 'val')
        else:
            self.new_run('val')
        LOG.leave()      

    def instantiate_frog(self):
        LOG.enter('instantiating Frog')
        config = '/usr/share/frog/nld/frog.cfg'  # TODO: op Merijn's computer
        LOG.message('configuration from {}'.format(config))
        self.frog = Frog(FrogOptions(parser=False, mwu=False), config)
        LOG.leave()

    # Frog has a nasty tendency to hang. This program must then be killed and
    # restarted from the point where the previous run failed. The PROGRESS
    # column in lemmas.csv, which corresponds to the line number in texts4.csv,
    # provides the necessary information.
    def get_progress(self, data_set):
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_lemmas.csv'.format(data_set)
        if filename.exists():
            with CSV.FileReader(filename) as source:
                assert next(source) == ['PROGRESS', 'PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG']
                for row in source:
                    progress = row[0]
            progress = int(progress)
        else:
            progress = 0
        return progress

    def new_run(self, data_set):
        LOG.message('Starting a new run')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_texts4.csv'.format(data_set)
        LOG.message('Reading from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TEXT']
            filename = CFG.PHASE1_DIR / 'Temp' / '{}_lemmas.csv'.format(data_set)
            LOG.message('Writing to {}'.format(filename))
            with CSV.FileWriter(filename, mode='x') as target:
                target.writerow(['PROGRESS', 'PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG'])
                self.run_frog(source, target, progress=0)

    def restart(self, progress, data_set):
        LOG.message('Restarting from line {}'.format(progress + 1))
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_texts4.csv'.format(data_set)
        LOG.message('Reading from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TEXT']
            # Skip to the restart point
            for _ in range(progress):
                next(source)
            filename = CFG.PHASE1_DIR / 'Temp' / '{}_lemmas.csv'.format(data_set)
            LOG.message('Appending to {}'.format(filename))
            with CSV.FileWriter(filename, mode='a') as target:
                self.run_frog(source, target, progress)

    def run_frog(self, source, target, progress):
        for praktijk_id, patient_id, levensverwachting, text in source:
            progress += 1
            print('  Progress: {}'.format(progress), end='\r')
            output = self.frog.process_raw(text)
            lines = output.split('\n')
            for line in lines:
                items = line.split('\t')
                if len(items) < 5: continue
                token = items[1]
                lemma = items[2]
                postag = items[4]
                postag = postag[:postag.find('(')]
                target.writerow([progress, praktijk_id, patient_id, levensverwachting, lemma, postag])

if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    FrogRunner2().run()
    LOG.leave()
