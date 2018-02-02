from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from collections import Counter, defaultdict


class ArffGenerator:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.get_icd_mapping()
        self.get_icpc_mapping()
        for event_category in CFG.EVENT_CATEGORIES:
            LOG.enter(event_category.full_name)
            level_param = event_category.tla.upper() + '_LEVELS'
            levels = getattr(PAR, level_param)
            for level in levels:
                LOG.enter('Aggregation level {}'.format(level))
                self.read_events(event_category, level)
                self.get_frequencies()
                for selector in PAR.EVENT_SELECTORS:
                    LOG.enter('Selector {}'.format(selector))
                    self.select_attributes(selector)
                    self.write_arff(selector, level, event_category)
                    LOG.leave()
                LOG.leave()
            LOG.leave()
        LOG.leave()

    def get_icd_mapping(self):
        LOG.enter('Reading ICD mapping')
        filename = CFG.DATA_DIR / 'icd.csv'
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['CODE', 'SUB-CAT', 'MAIN-CAT']
            self.icd_mapping = {}
            for code, subcat, maincat in source:
                self.icd_mapping[code] = {'CODE': code, 'SUB-CAT': subcat, 'MAIN-CAT': maincat}
        LOG.leave()

    def get_icpc_mapping(self):
        LOG.enter('Reading ICPC mapping')
        filename = CFG.DATA_DIR / 'icpc.csv'
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['CODE', 'SUB-CAT', 'MAIN-CAT', 'COLOR']
            self.icpc_mapping = {}
            for code, subcat, maincat, color in source:
                self.icpc_mapping[code] = {'CODE': code, 'SUB-CAT': subcat, 'MAIN-CAT': maincat, 'COLOR': color}
        LOG.leave()

    def read_events(self, event_category, level):
        filename = CFG.PHASE1_DIR / 'Events' / 'dev_{}.csv'.format(event_category.tla)
        LOG.message('Reading {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT']
            self.events = []
            for praktijk_id, patient_id, days_to_live, event in source:
                days_to_live = int(days_to_live)
                if event_category.tla == 'icd':
                    event = self.icd_mapping[event][level]
                elif event_category.tla in {'ana', 'dia', 'int', 'rfe'}:
                    event = self.icpc_mapping[event][level]
                self.events.append((praktijk_id, patient_id, days_to_live, event))
        LOG.message('{} events'.format(len(self.events)))

    def get_frequencies(self):
        LOG.message('calculating frequencies')
        counts = Counter()
        for praktijk_id, patient_id, days_to_live, event in self.events:
            counts[event] += 1
        total_count = sum(counts.values())
        counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)  # Sort by descending count
        self.frequencies = []
        rel_cum_freq = 0.0
        for event, count in counts:
            abs_freq = count
            rel_freq = 100.0 * count / total_count  # percent
            rel_cum_freq += rel_freq
            self.frequencies.append((event, abs_freq, rel_freq, rel_cum_freq))

    def select_attributes(self, selector):
        for event, abs_freq, rel_freq, rel_cum_freq in self.frequencies:
            if selector == 'ABS_FREQ':
                self.attributes = [event for event, abs_freq, _, _ in self.frequencies if abs_freq >= PAR.ABS_FREQ_CUTOFF]
            elif selector == 'REL_FREQ':
                self.attributes = [event for event, _, rel_freq, _ in self.frequencies if rel_freq >= PAR.REL_FREQ_CUTOFF]
            elif selector == 'REL_CUM_FREQ':
                self.attributes = [event for event, _, _, rel_cum_freq in self.frequencies if rel_cum_freq <= PAR.REL_CUM_FREQ_CUTOFF]
        LOG.message('{} unique events (attributes)'.format(len(self.attributes)))

    def write_arff(self, selector, level, event_category):
        LOG.enter('writing ARFF file')
        filename = CFG.PHASE2_DIR / 'Events' / '{}_{}_{}.arff'.format(selector, level, event_category.tla) # Does not write to temp
        LOG.message('to {}'.format(filename))
        self.target = open(str(filename), 'w')
        self.write_relation(event_category)
        self.write_attributes()
        if level == 'CODE':
            self.get_patients()  # Events per patient (ARFF rows)
            self.get_index()     # Column number per attribute (ARFF columns)
        self.target.close()
        LOG.leave()

    def write_relation(self, event_category):
        self.target.write('@relation {}\n\n'.format(event_category.full_name))

    def write_attributes(self):
        for index, attribute in enumerate(sorted(self.attributes)):
            self.target.write("@attribute '{}' numeric  % {}\n".format(attribute, index))
        self.target.write("@attribute 'DaysToLive' numeric  % {}\n".format(len(self.attributes)))

    def get_patients(self):
        self.patients = defaultdict(list)
        for praktijk_id, patient_id, days_to_live, event in self.events:
            self.patients[(praktijk_id, patient_id)].append((days_to_live, event))
        LOG.message('{} patients'.format(len(self.patients)))

    def get_index(self):
        self.index = {attribute: index for index, attribute in enumerate(self.attributes)}

# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    ArffGenerator().run()
    LOG.leave()
