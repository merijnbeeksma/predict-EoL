from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from math import sqrt
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date
import numpy


class HistoryGenerator:

    def run(self, output_dir):
        LOG.enter(self.__class__.__name__ + '.run()')
        # Development data
        self.run_patients(subcorpus='dev')
        if PAR.INCLUDE_KEYWORDS:
            self.run_keywords(output_dir, subcorpus='dev')
        self.run_events(output_dir, subcorpus='dev')
        self.write_histories(output_dir, filename='train.csv' if PAR.WORKFLOW == 'VALIDATION' else 'modeldata.csv')
        # Validation data
        if PAR.WORKFLOW == 'VALIDATION':
            self.run_patients(subcorpus='val')
            if PAR.INCLUDE_KEYWORDS:
                self.run_keywords(output_dir, subcorpus='val')
            self.run_events(output_dir, subcorpus='val')
            self.write_histories(output_dir, filename='test.csv')
        LOG.leave()
        
    def run_patients(self, subcorpus):
        LOG.enter('Patients')
        self.read_pat_data(subcorpus)
        self.create_pat_histories()
        LOG.leave()
        
    def run_keywords(self, output_dir, subcorpus):
        LOG.enter('Keywords')
        self.read_kwd_features(output_dir)
        self.read_kwd_data(subcorpus)
        self.create_kwd_histories()
        LOG.leave()
        
    def run_events(self, output_dir, subcorpus):
        LOG.enter('Events')
        self.read_icd_mapping()
        self.read_icpc_mapping()        
        self.evt_features = dict()  # tla => set of features
        self.evt_data = dict()  # tla => (praktijk, patient) => (days_to_live, event)
        self.evt_histories = dict()  # tla => histories
        for event_category in CFG.EVENT_CATEGORIES:
            if event_category.tla in PAR.EVENT_FILTER:
                LOG.enter(event_category.full_name)
                tla = event_category.tla
                self.read_evt_features(tla, output_dir)
                self.read_evt_data(tla, subcorpus)
                self.create_evt_histories(tla)
                LOG.leave()
        LOG.leave()
        
    def read_kwd_features(self, output_dir):
        filename = output_dir / 'kwd_features.csv'
        if PAR.KEYWORD_SELECTOR == 'WORD2VEC':
            LOG.enter('Reading word2vec model')
            LOG.message('From {}'.format(filename))
            self.kwd_vectors = dict()  # (keyword, postag) => vector
            with CSV.FileReader(filename) as source:
                assert next(source) == ['KEYWORD', 'POSTAG', 'VECTOR*']
                for row in source:
                    keyword = row[0]
                    postag = row[1]
                    vector = row[2:]
                    vector = numpy.array(vector, dtype='float64')
                    self.kwd_vectors[(keyword, postag)] = vector
            LOG.message('{} keywords'.format(len(self.kwd_vectors)))
            LOG.message('{} dimensions'.format(len(vector)))
            LOG.leave()
        else:
            LOG.enter('Reading keyword features')
            LOG.message('From {}'.format(filename))
            self.kwd_features = set()  # (keyword, postag) pairs
            with CSV.FileReader(filename) as source:
                assert next(source) == ['KEYWORD', 'POSTAG']
                for row in source:
                    keyword = row[0]
                    postag = row[1]
                    self.kwd_features.add((keyword, postag))
            LOG.message('{} keywords'.format(len(self.kwd_features)))
            LOG.leave()            
    
    def read_evt_features(self, tla, output_dir):
        LOG.enter('Reading event features')
        filename = output_dir / '{}_features.csv'.format(tla)
        LOG.message('From {}'.format(filename))
        features = set()
        with CSV.FileReader(filename) as source:
            assert next(source) == ['EVENT']
            for (event,) in source:
                event = '{}:{}'.format(tla, event)
                features.add(event)
        LOG.message('{} features'.format(len(features)))
        LOG.leave()
        self.evt_features[tla] = features
        
    def read_pat_data(self, subcorpus):
        LOG.enter('Reading patient data')
        filename = CFG.PHASE1_DIR / 'Patients' / '{}_pat.csv'.format(subcorpus)
        LOG.message('From {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEEFTIJD', 'GESLACHT']
            self.pat_data = {(praktijk_id, patient_id): (leeftijd, geslacht) for praktijk_id, patient_id, leeftijd, geslacht in source}
        LOG.leave()
        
    def read_kwd_data(self, subcorpus):
        filename = CFG.PHASE1_DIR / 'Keywords' / '{}_kwd.csv'.format(subcorpus)
        LOG.message('Reading {}'.format(filename))
        self.kwd_data = defaultdict(list)  # (praktijk, patient) => list of (days_to_live, lemma, postag) triples
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG']
            for praktijk_id, patient_id, days_to_live, lemma, postag in source:
                days_to_live = int(days_to_live)
                self.kwd_data[(praktijk_id, patient_id)].append((days_to_live, lemma, postag))
        
    def read_evt_data(self, tla, subcorpus):
        data = defaultdict(list)  # (praktijk, patient) => list of (days_to_live, event) pairs
        filename = CFG.PHASE1_DIR / 'Events' / '{}_{}.csv'.format(subcorpus, tla)
        LOG.message('Reading {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT']
            for praktijk_id, patient_id, days_to_live, event in source:
                days_to_live = int(days_to_live)
                data[(praktijk_id, patient_id)].append((days_to_live, event))
        self.evt_data[tla] = data
        LOG.message('{} events'.format(len(data)))
        
    def create_pat_histories(self):
        LOG.enter('Creating histories')
        self.pat_histories = defaultdict(lambda: [dict() for _ in range(PAR.HISTORY_LENGTH)])
        for (praktijk_id, patient_id), (age_of_death, geslacht) in self.pat_data.items():
            for period in range(PAR.HISTORY_LENGTH):
                vector = self.pat_histories[(praktijk_id, patient_id)][period]
                vector['age'] = (12 * float(age_of_death) - period) / 1440.0   # Max age for humans is 1440 months (120 years)
                vector['geslacht'] = -1 if geslacht == 'M' else +1 if geslacht == 'V' else 0
        LOG.message('{} patients'.format(len(self.pat_data)))
        LOG.leave()
        
    def create_kwd_histories(self):
        LOG.enter('Creating histories')
        if PAR.KEYWORD_SELECTOR == 'WORD2VEC':
            dimensions = PAR.KEYWORD_TOP
            self.kwd_histories = defaultdict(lambda: [numpy.zeros(dimensions) for _ in range(PAR.HISTORY_LENGTH)])
            # Count
            for (praktijk_id, patient_id), data in self.kwd_data.items():
                for (days_to_live, lemma, postag) in data:
                    if (lemma, postag) in self.kwd_vectors:
                        period = days_to_live // PAR.PERIOD_LENGTH
                        if 0 <= period < PAR.HISTORY_LENGTH:
                            #keyword_postag = '{}:{}'.format(lemma, postag)
                            vector = self.kwd_vectors[lemma, postag]            
                            self.kwd_histories[(praktijk_id, patient_id)][period] += vector
            # Scale
            for periods in self.kwd_histories.values():
                for vector in periods:
                    scale = max(max(vector), -min(vector))
                    if scale:
                        vector /= scale
        else:
            self.kwd_histories = defaultdict(lambda: [Counter() for _ in range(PAR.HISTORY_LENGTH)])
            # Count
            for (praktijk_id, patient_id), data in self.kwd_data.items():
                for (days_to_live, lemma, postag) in data:
                    if (lemma, postag) in self.kwd_features:
                        period = days_to_live // PAR.PERIOD_LENGTH
                        if 0 <= period < PAR.HISTORY_LENGTH:
                            keyword_postag = '{}:{}'.format(lemma, postag)
                            self.kwd_histories[(praktijk_id, patient_id)][period][keyword_postag] += 1
            # Scale
            for periods in self.kwd_histories.values():
                for counter in periods:
                    if counter:
                        max_freq = max(counter.values())
                        for keyword, freq in counter.items():
                            counter[keyword] /= max_freq
        LOG.leave()

    def create_evt_histories(self, tla):
        LOG.enter('Creating histories')
        data = self.evt_data[tla]
        features = self.evt_features[tla]
        histories = defaultdict(lambda: [Counter() for _ in range(PAR.HISTORY_LENGTH)])
        level = getattr(PAR, '{}_LEVEL'.format(tla.upper()))
        LOG.message('Aggregating to {} level'.format(level))
        # Count events per patient and per period
        for (praktijk, patient), evt_data in data.items():
            for (days_to_live, event) in evt_data:
                if tla == 'icd':
                    event = self.icd_mapping[event][level]
                if tla in {'ana', 'dia', 'int', 'rfe'}:
                    event = self.icpc_mapping[event][level]                
                event = '{}:{}'.format(tla, event)
                if event in features:
                    period = days_to_live // PAR.PERIOD_LENGTH
                    if 0 <= period < PAR.HISTORY_LENGTH:
                        histories[(praktijk, patient)][period][event] += 1
        # For each event category, each patient, and each period, scale the event counts to the range 0 ≤ count ≤ 1
        for periods in histories.values():
            for counter in periods:
                if counter:
                    max_freq = max(counter.values())
                    for event, freq in counter.items():
                        counter[event] /= max_freq
        self.evt_histories[tla] = histories
        LOG.leave()

    def write_histories(self, output_dir, filename):
        LOG.enter('Writing histories')
        filename = output_dir / filename
        LOG.message('To {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            headers = ['PRAKTIJK-ID', 'PATIENT-ID'] + ['P{0}'.format(period) for period in range(PAR.HISTORY_LENGTH)]
            target.writerow(headers)
            for (praktijk_id, patient_id) in self.pat_data:
                row = [praktijk_id, patient_id]
                for period in range(PAR.HISTORY_LENGTH):
                    features = []
                    # Patients
                    pat_features = self.pat_histories[(praktijk_id, patient_id)][period]
                    for feature, value in pat_features.items():
                        features.append((feature, value))
                    # Keywords
                    if PAR.INCLUDE_KEYWORDS:
                        if PAR.KEYWORD_SELECTOR == 'WORD2VEC':
                            vector = self.kwd_histories[(praktijk_id, patient_id)][period]
                            for dim, value in enumerate(vector):
                                feature = 'dim{}'.format(dim)
                                features.append((feature, value))
                        else:
                            kwd_features = self.kwd_histories[(praktijk_id, patient_id)][period]
                            for feature, value in kwd_features.items():
                                features.append((feature, value))
                    # Events
                    for tla, data in self.evt_histories.items():
                        evt_features = data[(praktijk_id, patient_id)][period]
                        for feature, value in evt_features.items():
                            features.append((feature, value))
                    # Write features
                    if len(features) == 2:  # Write nothing if only age and gender are present
                        features = ''
                    else:
                        features = ','.join('{}={}'.format(feature, value) for feature, value in features)
                    row.append(features)
                target.writerow(row)
            LOG.message('{} periods of {} days each'.format(PAR.HISTORY_LENGTH, PAR.PERIOD_LENGTH))
            LOG.message('{} histories'.format(len(self.pat_data)))
        LOG.leave()

    def read_icd_mapping(self):
        LOG.enter('Reading ICD mapping')
        filename = CFG.DATA_DIR / 'icd.csv'
        LOG.message('From {}'.format(filename))
        self.icd_mapping = dict()
        with CSV.FileReader(filename) as source:
            assert next(source) == ['CODE', 'SUB-CAT', 'MAIN-CAT']
            for code, sub_cat, main_cat in source:
                self.icd_mapping[code] = {'CODE': code, 'SUB-CAT': sub_cat, 'MAIN-CAT': main_cat}        
        LOG.leave()
    
    def read_icpc_mapping(self):
        LOG.enter('Reading ICPC mapping')
        filename = CFG.DATA_DIR / 'icpc.csv'
        LOG.message('From {}'.format(filename))
        self.icpc_mapping = dict()
        with CSV.FileReader(filename) as source:
            assert next(source) == ['CODE', 'SUB-CAT', 'MAIN-CAT', 'COLOR']
            for code, sub_cat, main_cat, color in source:
                self.icpc_mapping[code] = {'CODE': code, 'SUB-CAT': sub_cat, 'MAIN-CAT': main_cat, 'COLOR': color}        
        LOG.leave()
 

# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    if PAR.WORKFLOW == 'DEVELOPMENT':
        HistoryGenerator().run(CFG.PHASE3_DIR)
    elif PAR.WORKFLOW == 'VALIDATION':
        HistoryGenerator().run(CFG.PHASE4_DIR)
    LOG.leave()
