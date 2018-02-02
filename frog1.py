from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from frog import Frog, FrogOptions

class FrogRunner1:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.instantiate_frog()
        LOG.enter('development set')
        self.read_input('dev')
        self.run_frog()
        self.write_output('dev')
        LOG.leave()
        LOG.enter('validation set')
        self.read_input('val')
        self.run_frog()
        self.write_output('val')
        LOG.leave()      
        LOG.leave()

    def instantiate_frog(self):
        LOG.enter('instantiating Frog')
        config = '/usr/share/frog/nld/frog.cfg'  # TODO: op Merijn's computer
        LOG.message('configuration from {}'.format(config))
        self.frog = Frog(FrogOptions(parser=False, mwu=False), config)
        LOG.leave()

    def read_input(self, data_set):
        LOG.enter('reading Frog input')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_texts1.csv'.format(data_set)
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TEXT']
            self.input = [row for row in source]
        LOG.message('{} texts'.format(len(self.input)))
        LOG.leave()

    def run_frog(self):
        LOG.enter('running Frog')
        self.output = []
        count = 0
        for praktijk_id, patient_id, levensverwachting, text in self.input:
            count += 1
            print(count, end='\r')
            output = self.frog.process_raw(text)
            lines = output.split('\n')
            for line in lines:
                items = line.split('\t')
                if len(items) < 5: continue
                token = items[1]
                postag = items[4]
                postag = postag[:postag.find('(')]
                self.output.append([praktijk_id, patient_id, levensverwachting, token, postag])
        LOG.leave()

    def write_output(self, data_set):
        LOG.enter('writing output')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_tokens.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TOKEN', 'POSTAG'])
            for row in self.output:
                target.writerow(row)
        LOG.message('{} (token, postag) pairs'.format(len(self.output)))
        LOG.leave()

if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    FrogRunner1().run()
    LOG.leave()
