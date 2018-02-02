from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import epd_corpus
import unicodedata
import re


class Text:

    def __init__(self, praktijk_id, patient_id, levensverwachting, text):
        # Metadata
        self.praktijk_id = praktijk_id
        self.patient_id = patient_id
        self.levensverwachting = levensverwachting
        # Data
        self.text = ' '.join(text.lower().split())

    def drop_diacriticals(self):
        nfkd_form = unicodedata.normalize('NFKD', self.text)
        self.text = ''.join(c for c in nfkd_form if not unicodedata.combining(c))

    def as_tuple(self):
        return self.praktijk_id, self.patient_id, self.levensverwachting, self.text


class Brief(Text):

    def __init__(self, praktijk_id, patient_id, levensverwachting, text):
        super().__init__(praktijk_id, patient_id, levensverwachting, text)
        self.drop_diacriticals()
        self.drop_header()  # Geachte ...,
        self.drop_footer()  # Hoogachtend, ...

    def drop_header(self):
        for zoekterm in ['geachte']:
            pos = self.text.find(zoekterm)
            if pos >= 0:
                pos = self.text.find(',', pos)
                if pos >= 0:
                    self.text = self.text[pos + 1:]
                    break

    def drop_footer(self):
        for zoekterm in ['met vriendelijke', 'met collegiale', 'met hoogachting', 'hoogachtend', 'groet']:
            pos = self.text.find(zoekterm)
            if pos >= 0:
                self.text = self.text[:pos]
                break


class Notitie(Text):

    def __init__(self, praktijk_id, patient_id, levensverwachting, text):
        super().__init__(praktijk_id, patient_id, levensverwachting, text)
        self.drop_diacriticals()


class TextExtractor:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')        
        LOG.enter('development set')
        self.corpus = epd_corpus.read(epd_corpus.DataSet.DEVELOPMENT)
        self.extract_texts()
        self.write_texts('dev')
        LOG.leave()
        LOG.enter('validation set')
        self.corpus = epd_corpus.read(epd_corpus.DataSet.VALIDATION)
        self.extract_texts()
        self.write_texts('val')
        LOG.leave()        
        LOG.leave()

    def extract_texts(self):
        LOG.enter('extracting texts')
        # Brieven
        brieven = self.extract_brieven()
        LOG.message('{} characters in {} brieven'.format(sum(len(brief.text) for brief in brieven), len(brieven)))
        # Notities
        notities = self.extract_notities()
        LOG.message('{} characters in {} notities'.format(sum(len(notitie.text) for notitie in notities), len(notities)))
        #
        self.texts = brieven + notities
        LOG.leave()

    def extract_brieven(self):
        brieven = []
        for praktijk in self.corpus.praktijken:
            for patient in praktijk.patienten:
                for contact in patient.contacten:
                    levensverwachting = (patient.overlijdensdatum - contact.datum).days
                    for deelcontact in contact.deelcontacten:
                        for brief in deelcontact.brieven:
                            brieven.append(Brief(praktijk.ident, patient.ident, levensverwachting, brief.tekst))
        return brieven

    def extract_notities(self):
        notities = []
        for praktijk in self.corpus.praktijken:
            for patient in praktijk.patienten:
                for contact in patient.contacten:
                    levensverwachting = (patient.overlijdensdatum - contact.datum).days
                    for deelcontact in contact.deelcontacten:
                        for notitie in deelcontact.notities:
                            notities.append(Notitie(praktijk.ident, patient.ident, levensverwachting, notitie.tekst))
        return notities
        
    def write_texts(self, data_set):
        LOG.enter('writing texts')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_texts1.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TEXT'])
            for text in self.texts:
                target.writerow(text.as_tuple())
        LOG.message('{} texts'.format(len(self.texts)))
        LOG.leave()


if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    TextExtractor().run()
    LOG.leave()
