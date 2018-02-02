from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import re


class Rephraser:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        LOG.enter('development set')
        self.read_texts('dev')
        self.read_phrases()
        self.rephrase_texts()
        self.write_texts('dev')
        LOG.leave()
        LOG.enter('validation set')
        self.read_texts('val')
        self.read_phrases()
        self.rephrase_texts()
        self.write_texts('val')
        LOG.leave()        
        LOG.leave()

    def read_texts(self, data_set):
        LOG.enter('reading Frog input')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_texts3.csv'.format(data_set)
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TEXT']
            self.texts = [row for row in source]
        LOG.message('{} texts'.format(len(self.texts)))
        LOG.leave()

    def read_phrases(self):
        LOG.enter('reading phrases')
        filename = CFG.DATA_DIR / 'phrases.csv'
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PHRASE', 'EXPANSION']
            phrases = list(source)
        # Sort by descending phrase length, to prevent expansion of sub-phrases
        phrases.sort(key=lambda p_e: (-len(p_e[0]), p_e[0]))
        # Compile a regex for each replacement, to prevent expansion inside a word
        self.phrases = []
        for phrase, replacement in phrases:
            regex = re.compile('(?<![a-z]){}(?![a-z])'.format(phrase))
            self.phrases.append((regex, replacement))
        LOG.message('{} phrases'.format(len(self.phrases)))
        LOG.leave()

    def rephrase_texts(self):
        LOG.enter('Rephrasing texts')
        todo = len(self.texts)
        changes = 0
        for document in self.texts:
            todo -= 1
            print('{:6d}'.format(todo), end='\r')
            text = document[3]
            for phrase, replacement in self.phrases:
                text = phrase.sub(replacement, text)
            if text != document[3]:
                document[3] = text
                changes += 1
        LOG.message('{} texts rephrased'.format(changes))
        LOG.leave()            

    def write_texts(self, data_set):
        LOG.enter('writing texts')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_texts4.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TEXT'])
            for text in self.texts:
                target.writerow(text)
        LOG.message('{} texts'.format(len(self.texts)))
        LOG.leave()


if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    Rephraser().run()
    LOG.leave()
