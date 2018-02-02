from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import epd_corpus


class PatientData:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        LOG.enter('development set')
        self.corpus = epd_corpus.read(epd_corpus.DataSet.DEVELOPMENT)
        self.get_data('dev')
        LOG.leave()
        LOG.enter('validation set')
        self.corpus = epd_corpus.read(epd_corpus.DataSet.VALIDATION)
        self.get_data('val')
        LOG.leave()
        LOG.leave()

    def get_data(self, data_set):
        LOG.enter('writing data')
        filename = CFG.PHASE1_DIR / 'Patients' / '{}_pat.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        count = 0
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEEFTIJD', 'GESLACHT'])
            for praktijk in self.corpus.praktijken:
                for patient in praktijk.patienten:
                    leeftijd = patient.leeftijd
                    target.writerow([praktijk.ident, patient.ident, leeftijd, patient.geslacht])
                    count += 1
        LOG.message('{} patiënten'.format(count))
        LOG.leave()


if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    PatientData().run()
    LOG.leave()
