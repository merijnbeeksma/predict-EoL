from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import re

class FrogPostprocessor:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        LOG.enter('development set')
        self.read_frog_output('dev')
        self.downcase()
        self.filter()
        self.write_lemmas('dev')
        LOG.leave()
        LOG.enter('validation set')
        self.read_frog_output('val')
        self.downcase()
        self.filter()
        self.write_lemmas('val')
        LOG.leave()
        LOG.leave()

    def read_frog_output(self, data_set):
        LOG.enter('reading Frog output')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_lemmas.csv'.format(data_set)
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PROGRESS', 'PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG']
            self.lemmas = [row for row in source]
        LOG.message('{} (lemma, postag) pairs'.format(len(self.lemmas)))
        LOG.leave()

    def downcase(self):
        LOG.message('Downcasing lemmas')
        lemmas = []
        for progress, praktijk_id, patient_id, levensverwachting, lemma, postag in self.lemmas:
            lemma = lemma.casefold()
            lemmas.append((praktijk_id, patient_id, levensverwachting, lemma, postag))
        self.lemmas = lemmas

    # Keep only lemmas that:
    #   *  consist entirely of letters and dashes;
    #   *  have at least one letter on both sides of every dash;
    #   *  contain at least two letters.
    def filter(self):
        LOG.enter('Filtering lemmas')
        regex = re.compile('[a-z]+(-[a-z]+)*')
        lemmas = []
        for row in self.lemmas:
            lemma = row[3]
            if len(lemma) > 1 and regex.fullmatch(lemma):
                lemmas.append(row)
        reject_count = len(self.lemmas) - len(lemmas)
        LOG.message('{} lemmas rejected'.format(reject_count))
        self.lemmas = lemmas
        LOG.leave()

    def write_lemmas(self, data_set):
        LOG.enter('Writing lemmas')
        filename = CFG.PHASE1_DIR / 'Keywords' / '{}_kwd.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG'])
            for row in self.lemmas:
                target.writerow(row)
        LOG.message('{} lemmas'.format(len(self.lemmas)))
        LOG.leave()

if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    FrogPostprocessor().run()
    LOG.leave()
