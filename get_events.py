from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import epd_corpus
import unicodedata
import re


class EventExtractor:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        LOG.enter('development set')
        self.corpus = epd_corpus.read(epd_corpus.DataSet.DEVELOPMENT)
        self.get_events('dev')
        LOG.leave()
        LOG.enter('validation set')
        self.corpus = epd_corpus.read(epd_corpus.DataSet.VALIDATION)
        self.get_events('val')
        LOG.leave()
        LOG.leave()

    def get_events(self, data_set):
        LOG.enter('writing events')
        LOG.message('to {}'.format(CFG.PHASE1_DIR))
        for event_category in CFG.EVENT_CATEGORIES:
            LOG.enter(event_category.full_name)
            name = 'get_{}_events'.format(event_category.tla)
            method = getattr(self, name)
            method(data_set)
            LOG.leave()
        LOG.leave()

    # Anamnese
    def get_ana_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_ana.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        for deelcontact in contact.deelcontacten:
                            if deelcontact.anamnese:
                                for anamnese in deelcontact.anamnese.split(','):
                                    code = anamnese.split(':')[0]
                                    if code.startswith(' '): continue
                                    if len(code) == 3 and 'A' <= code[0] <= 'Z' and '0' <= code[1] <= '9' and '0' <= code[2] <= '9':
                                        target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                        num_events += 1
        LOG.message('{} events'.format(num_events))

    # Consult
    def get_con_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_con.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        code = contact.consult.replace("'", '').replace(',', '')
                        target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                        num_events += 1
        LOG.message('{} events'.format(num_events))

    # Diagnose
    def get_dia_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_dia.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        for deelcontact in contact.deelcontacten:
                                code = deelcontact.diagnose
                                if len(code) == 3 and 'A' <= code[0] <= 'Z' and '0' <= code[1] <= '9' and '0' <= code[2] <= '9':
                                    target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                    num_events += 1
        LOG.message('{} events'.format(num_events))

    # ICD10
    def get_icd_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_icd.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        for deelcontact in contact.deelcontacten:
                            if deelcontact.icd10:
                                code = deelcontact.icd10.split('.')[0]
                                if len(code) == 3 and 'A' <= code[0] <= 'Z' and '0' <= code[1] <= '9' and '0' <= code[2] <= '9':
                                    target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                    num_events += 1
        LOG.message('{} events'.format(num_events))

    # Interventie
    def get_int_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_int.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        for deelcontact in contact.deelcontacten:
                            if deelcontact.int_interv:
                                for interventie in deelcontact.int_interv.split(','):
                                    code = interventie.split(':')[0]
                                    if code.startswith(' '): continue
                                    if len(code) == 3 and 'A' <= code[0] <= 'Z' and '0' <= code[1] <= '9' and '0' <= code[2] <= '9':
                                        target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                        num_events += 1
                            if deelcontact.res_interv:
                                for interventie in deelcontact.res_interv.split(','):
                                    code = interventie.split(':')[0]
                                    if code.startswith(' '): continue
                                    if len(code) == 3 and 'A' <= code[0] <= 'Z' and '0' <= code[1] <= '9' and '0' <= code[2] <= '9':
                                        target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                        num_events += 1
        LOG.message('{} events'.format(num_events))

    # Medicatie
    def get_med_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_med.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        for deelcontact in contact.deelcontacten:
                            for medicatie in deelcontact.medicaties:
                                code = medicatie.middel.strip()
                                if ' ' in code:
                                    code = code.split(maxsplit=1)[0]
                                if code:
                                    target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                    num_events += 1
        LOG.message('{} events'.format(num_events))

    # Meetwaarde
    def get_mtw_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_mtw.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        for deelcontact in contact.deelcontacten:
                            for meetwaarde in deelcontact.meetwaarden:
                                if meetwaarde.afwijkend:
                                    code = meetwaarde.labcode
                                    target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                    num_events += 1
        LOG.message('{} events'.format(num_events))

    # RFE
    def get_rfe_events(self, data_set):
        filename = CFG.PHASE1_DIR / 'Events' / '{}_rfe.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        num_events = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    for contact in patient.contacten:
                        dagen_te_leven = (patient.overlijdensdatum - contact.datum).days
                        for deelcontact in contact.deelcontacten:
                            if deelcontact.rfe17:
                                for rfe in deelcontact.rfe17.split(','):
                                    code = rfe.split(':')[0]
                                    if code.startswith(' '): continue
                                    if len(code) == 3 and 'A' <= code[0] <= 'Z' and '0' <= code[1] <= '9' and '0' <= code[2] <= '9':
                                        target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                        num_events += 1
                            if deelcontact.rfe26:
                                for rfe in deelcontact.rfe26.split(','):
                                    code = rfe.split(':')[0]
                                    if code.startswith(' '): continue
                                    if len(code) == 3 and 'A' <= code[0] <= 'Z' and '0' <= code[1] <= '9' and '0' <= code[2] <= '9':
                                        target.writerow([praktijk.ident, patient.ident, dagen_te_leven, code])
                                        num_events += 1
        LOG.message('{} events'.format(num_events))


if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    EventExtractor().run()
    LOG.leave()
