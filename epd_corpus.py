from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG

from enum import Enum
import datetime


class DataSet(Enum):
    DEVELOPMENT = 1
    VALIDATION = 2


def read(data_set):
    corpus = _CorpusReader().run(data_set)
    return corpus


# These domain classes are all data-only.
# Refer to Corpus (design).graphml for documentation.
class Corpus: pass
class Praktijk: pass
class Patient: pass
class Contact: pass
class Deelcontact: pass
class Medicatie: pass
class Meetwaarde: pass
class Brief: pass
class Notitie: pass


class _CorpusReader:

    def run(self, data_set):
        LOG.enter('reading corpus')
        LOG.message('from {}'.format(CFG.CORPUS_PER_PRAKTIJK_DIR))
        # Read the data
        corpus = Corpus()
        corpus.praktijken = []
        for ident in CFG.PRAKTIJK_IDS:
            LOG.message('praktijk {}'.format(ident))
            praktijk = _PraktijkReader().run(ident)
            corpus.praktijken.append(praktijk)
        # Filter the data
        for praktijk in corpus.praktijken:
            praktijk.patienten.sort(key=lambda patient: patient.overlijdensdatum)
            split = len(praktijk.patienten) * 9 // 10
            if data_set == DataSet.DEVELOPMENT:
                del praktijk.patienten[split:]
            else:
                del praktijk.patienten[:split]
        #
        LOG.leave()
        return corpus


class _PraktijkReader:

    def run(self, ident):
        self.ident = ident
        # Indexes
        self.patient_index = {}      # patient_ident => Patient
        self.contact_index = {}      # contact_ident => Contact
        self.deelcontact_index = {}  # deelcontact_ident => Deelcontact
        # The Praktijk object to return
        self.praktijk = Praktijk()
        self.praktijk.ident = ident
        self.praktijk.patienten = []
        # Read all the praktijk's corpus files
        self.lees_overledenen(self.make_path('Overledenen'))
        self.lees_contacten(self.make_path('Contacten'))
        self.lees_deelcontacten(self.make_path('Deelcontacten'))
        self.lees_medicaties(self.make_path('Medicatie'))
        self.lees_meetwaarden(self.make_path('Meetwaarden'))
        self.lees_brieven(self.make_path('Brieven'))
        self.lees_notities(self.make_path('Notities deelcontacten'))
        return self.praktijk

    def lees_overledenen(self, path):
        with CSV.FileReader(path) as source:
            headers = next(source)
            assert headers == ['PatNr', 'Gesl', 'Datum overlijden', 'Leeftijd bij overlijden', 'StartDatum', 'Aantal dagen']
            for record in source:
                if record[1]:
                    patient = Patient()
                    patient.ident = int(record[0])
                    patient.contacten = []
                    patient.geslacht = record[1]
                    patient.overlijdensdatum = self.parse_datum(record[2])
                    patient.leeftijd = int(record[3])
                    self.praktijk.patienten.append(patient)
                    self.patient_index[patient.ident] = patient

    def lees_contacten(self, path):
        with CSV.FileReader(path) as source:
            headers = next(source)
            assert headers == ['PatNr', 'Datum', 'ContId', 'EncType', 'Label', 'Id', 'Gebruikerstype']
            for record in source:
                if record[1]:
                    contact = Contact()
                    contact.ident = int(record[2])
                    contact.deelcontacten = []
                    contact.datum = self.parse_datum(record[1])  # field: Datum
                    contact.consult = record[4]
                    patient_ident = int(record[0])
                    patient = self.patient_index[patient_ident]
                    patient.contacten.append(contact)
                    self.contact_index[contact.ident] = contact

    def lees_deelcontacten(self, path):
        with CSV.FileReader(path) as source:
            headers = next(source)
            assert headers == ['PatNr', 'Contid', 'DiaId', 'RFE 1-7', 'RFE 2-6', 'Anamnese', 'Int. interv.', 'Diagnose', 'ICD10', 'Label diagnose', 'Res. interv.', 'EpiId']
            for record in source:
                if record[1]:
                    deelcontact = Deelcontact()
                    deelcontact.ident = int(record[2])
                    deelcontact.medicaties = []
                    deelcontact.meetwaarden = []
                    deelcontact.brieven = []
                    deelcontact.notities = []
                    deelcontact.anamnese = record[5]
                    deelcontact.diagnose = record[7]
                    deelcontact.icd10 = record[8]
                    deelcontact.int_interv = record[6]
                    deelcontact.res_interv = record[10]
                    deelcontact.rfe17 = record[3]
                    deelcontact.rfe26 = record[4]
                    contact_ident = int(record[1])
                    contact = self.contact_index[contact_ident]
                    contact.deelcontacten.append(deelcontact)
                    self.deelcontact_index[deelcontact.ident] = deelcontact

    def lees_medicaties(self, path):
        with CSV.FileReader(path) as source:
            headers = next(source)
            assert headers == ['PatNr', 'Datum van', 'DiaId', 'Tot', 'Middel', 'Hpknr', 'Prknr', 'Gpknr', 'ATC', 'Aantal', 'S', 'Chron', 'StopDatum']
            for record in source:
                if record[1]:
                    deelcontact_ident = int(record[2])
                    if deelcontact_ident in self.deelcontact_index:  # TODO
                        deelcontact = self.deelcontact_index[deelcontact_ident]
                        medicatie = Medicatie()
                        medicatie.middel = record[4]
                        deelcontact.medicaties.append(medicatie)

    def lees_meetwaarden(self, path):
        with CSV.FileReader(path) as source:
            headers = next(source)
            assert headers == ['PatNr', 'DiaId', 'Labcodeid', 'Label', 'Datum uitslag', 'Uitslag', 'Afwijkend']
            for record in source:
                if record[1]:
                    deelcontact_ident = int(record[1])
                    if deelcontact_ident in self.deelcontact_index:  # TODO
                        deelcontact = self.deelcontact_index[deelcontact_ident]
                        meetwaarde = Meetwaarde()
                        meetwaarde.labcode = record[2]
                        meetwaarde.afwijkend = record[6] == 'J'
                        deelcontact.meetwaarden.append(meetwaarde)

    def lees_brieven(self, path):
        with CSV.BrokenFileReader(path) as source:
            headers = next(source)
            assert headers == ['PatNr', 'DiaId', 'Type', 'Hulpverlener', 'PdfId', 'HiddenRichText']
            for record in source:
                if len(record) == len(headers) and record[5]:  # TODO
                    deelcontact_ident = int(record[1])
                    if deelcontact_ident in self.deelcontact_index:  # TODO
                        deelcontact = self.deelcontact_index[deelcontact_ident]
                        brief = Brief()
                        brief.tekst = record[5]
                        deelcontact.brieven.append(brief)

    def lees_notities(self, path):
        with CSV.FileReader(path) as source:
            headers = next(source)
            assert headers == ['PatNr', 'DiaId', 'Type', 'HiddenMemo']
            for record in source:
                if len(record) == len(headers) and record[1]:  # TODO
                    deelcontact_ident = int(record[1])
                    if deelcontact_ident in self.deelcontact_index: # TODO
                        deelcontact = self.deelcontact_index[deelcontact_ident]
                        notitie = Notitie()
                        notitie.tekst = record[3]
                        deelcontact.notities.append(notitie)

    def make_path(self, basename):
        path = CFG.CORPUS_PER_PRAKTIJK_DIR / self.ident / '{0}_{1}.csv'.format(self.ident, basename)
        return str(path)

    @staticmethod
    def parse_datum(tekst):
        if tekst:
            dag, maand, jaar = map(int, tekst.split('-'))
            datum = datetime.date(jaar, maand, dag)
            return datum
