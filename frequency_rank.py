from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from collections import Counter, defaultdict


class FrequencyRanker:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.read_keywords()
        self.get_frequencies()
        self.write_csv()   # Table of frequencies
        self.write_arff()
        LOG.leave()

    def read_keywords(self):
        LOG.enter('reading keywords')
        filename = CFG.PHASE1_DIR / 'Keywords' / 'dev_kwd.csv'
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG']
            self.keywords = []
            for praktijk_id, patient_id, days_to_live, keyword, postag in source:
                self.keywords.append((keyword, postag))
        LOG.message('{} keywords read'.format(len(self.keywords)))
        LOG.leave()

    def get_frequencies(self):
        LOG.message('calculating frequencies')
        counts = Counter(self.keywords)
        total_count = sum(counts.values())
        counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)  # Sort by descending count
        self.frequencies = []
        rel_cum_freq = 0.0
        for keyword, count in counts:
            abs_freq = count
            rel_freq = count / total_count
            rel_cum_freq += rel_freq
            self.frequencies.append((keyword, abs_freq, rel_freq, rel_cum_freq))

    def write_csv(self):
        LOG.enter('writing table of frequencies')
        filename = CFG.PHASE2_DIR / 'Temp' / 'frequencies.csv'
        LOG.message('to {}'.format(filename))
        LOG.message('{} unique keywords'.format(len(self.frequencies)))
        with CSV.FileWriter(filename) as target:
            target.writerow(['KEYWORD', 'POSTAG', 'ABS-FREQ', 'REL_FREQ', 'REL_CUM_FREQ'])
            for (keyword, postag), abs_freq, rel_freq, rel_cum_freq in self.frequencies:
                target.writerow([keyword, postag, abs_freq, rel_freq, rel_cum_freq])
        LOG.leave()

    def write_arff(self):
        LOG.enter('writing ARFF file')
        filename = CFG.PHASE2_DIR / 'Keywords' / 'frequency_kwd.arff'
        LOG.message('to {}'.format(filename))
        with open(str(filename), 'w') as target:
            # Relation
            target.write('@relation Keywords\n\n')
            # Attributes
            for (keyword, postag), abs_freq, rel_freq, rel_cum_freq in self.frequencies:
                target.write("@attribute '{}:{}' numeric\n".format(keyword, postag))
            target.write("@attribute 'DaysToLive' numeric\n")
        LOG.leave()

# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    FrequencyRanker().run()
    LOG.leave()
