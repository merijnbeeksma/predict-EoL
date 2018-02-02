import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from collections import Counter, defaultdict
import math
import scipy.stats


# Kullback-Leibler divergence.
# Unfortunately we cannot use scipy.stats.entropy here, because it doesn't handle
# p=0 cases correctly: keywords with zero occurrences in any month.
# Tested: whenever scipy.stats.entropy works, our kullback_leibler yields the same answer.
# https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.entropy.html
# https://en.wikipedia.org/wiki/Kullback%E2%80%93Leibler_divergence
def kullback_leibler(P, Q):
    assert len(P) == len(Q)
    sumP, sumQ = sum(P), sum(Q)
    divergence = 0.0
    for p, q in zip(P, Q):
        if p > 0.0 and q > 0.0:
            p, q = p / sumP, q / sumQ
            divergence += p * math.log(p / q)
    return divergence


def model_curve(x, a, b, c):
    return a * np.exp(-b * x) + c


# Represents one occurrence of a keyword in the corpus.
class KeywordEvent:

    def __init__(self, praktijk_id, patient_id, days_to_live, keyword, postag):
        self.ident = '{}_{}'.format(praktijk_id, patient_id)
        self.period = int(days_to_live) // PAR.PERIOD_LENGTH
        self.keyword = keyword
        self.postag = postag


# Represents a unique keyword.
class Keyword:

    def __init__(self, keyword, postag):
        self.keyword = keyword
        self.postag = postag
        self.absolute_counts = PAR.HISTORY_LENGTH * [0]
        self.relative_counts = PAR.HISTORY_LENGTH * [0.0]

    def total_absolute_count(self):
        return sum(self.absolute_counts)

    def total_relative_count(self):
        return sum(self.relative_counts)

    def calculate_relative_entropy(self):
        try:
            max_count = max(self.relative_counts)
            counts = np.array(self.relative_counts, np.double)
            bounds = (-2 * max_count, -2, 0), (2 * max_count, 2, np.inf)
            (a, b, c), pcov = curve_fit(f=model_curve, xdata=self.periods, ydata=counts, bounds=bounds)
            # FIX: Kullback-Leibler will fail if a+c<=0, which happens often enough
            # (500 out of 12000 keywords) to be a problem. Since -a/c is almost always
            # just above 1 in those cases, we salvage the situation by setting a=-c.
            if (a + c < 0.0): a = -c
            fit = model_curve(self.periods, a, b, c)
            # self.entropy = scipy.stats.entropy(counts, fit)
            self.relative_abc = a, b, c
            self.relative_entropy = kullback_leibler(counts, fit)
        except:
            self.relative_abc = None, None, None
            self.relative_entropy = None


class EntropyRanker:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        Keyword.periods = np.linspace(0, PAR.HISTORY_LENGTH - 1, PAR.HISTORY_LENGTH)
        self.read_events()                # Read all words from the corpus
        self.filter_by_period()           # Retain only words inside the history
        self.count_keywords()             # Count how often each words appears (vertical totals)
        self.count_patients()             # Count for how many patients each word appears (horizontal totals)
        self.filter_by_frequency()        # Remove infrequent words
        self.calculate_relative_counts()  # Adjust for frequencies generally increasing in time
        self.calculate_entropies()        # Do curve fitting and calculate the entropy
        self.write_keywords()             # Write keywords with curve fit params and entropy
        self.filter_keywords()            # Discard keywords where entropy calculation failed
        self.rank_keywords()              # Sort by increasing entropy
        self.write_arff_file()            # Write ARFF file
        LOG.leave()

    def read_events(self):
        LOG.enter('Reading keyword events')
        filename = CFG.PHASE1_DIR / 'Keywords' / 'dev_kwd.csv'
        LOG.message('From {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG']
            self.events = [KeywordEvent(*row) for row in source]
        LOG.message('{} keyword events'.format(len(self.events)))
        LOG.leave()

    def filter_by_period(self):
        LOG.enter('Filtering keyword events by period number')
        filtered_events = [event for event in self.events if 0 <= event.period < PAR.HISTORY_LENGTH]
        remove_count = len(self.events) - len(filtered_events)
        self.events = filtered_events
        LOG.message('Removed {} keyword events with a negative period number'.format(remove_count))
        LOG.message('{} keyword events remaining'.format(len(self.events)))
        LOG.leave()

    # For every keyword and period, count how often that keyword appears in
    # that period over all patients. These counts are the "absolute frequencies".
    # Next get the total number of keyword events in every period (vertical totals).
    # Then get the "relative frequencies" by dividing the absolute frequency
    # of a keyword in a period by the total number of keyword events in that
    # period. This compensates for the fact that keyword events are not evenly
    # distributed over all periods.
    def count_keywords(self):
        LOG.enter('Counting keyword events per period')
        self.keywords = dict()  # (keyword, postag) => Keyword
        # Absolute frequencies
        for event in self.events:
            keyword = self.keywords.get((event.keyword, event.postag))
            if keyword is None:
                keyword = Keyword(event.keyword, event.postag)
                self.keywords[(event.keyword, event.postag)] = keyword
            keyword.absolute_counts[event.period] += 1
        LOG.message('{} unique keywords'.format(len(self.keywords)))
        LOG.leave()

    def calculate_relative_counts(self):
        LOG.message('Calculating relative event counts')
        # Get the total number of keyword events in every period (vertical totals).
        total_counts = PAR.HISTORY_LENGTH * [0]
        for keyword in self.keywords:
            for period in range(PAR.HISTORY_LENGTH):
                total_counts[period] += keyword.absolute_counts[period]
        # Divide absolute counts by totals to get relative counts.
        for keyword in self.keywords:
            for period in range(PAR.HISTORY_LENGTH):
                if total_counts[period]:  # Avoid division by zero
                    keyword.relative_counts[period] = keyword.absolute_counts[period] / total_counts[period]

    def count_patients(self):
        LOG.message('Counting patients per keyword')
        patients = defaultdict(set)
        for event in self.events:
            patients[(event.keyword, event.postag)].add(event.ident)
        for (keyword, postag), idents in patients.items():
            self.keywords[(keyword, postag)].patients = len(idents)

    # Filter keywords based on total number of events.
    def filter_by_frequency(self):
        MIN_EVENTS = 10  # TODO: move to param.txt?
        LOG.enter('Filtering keywords by event count')
        filtered_keywords = [keyword for keyword in self.keywords.values() if keyword.total_absolute_count() >= MIN_EVENTS]
        removed = len(self.keywords) - len(filtered_keywords)
        self.keywords = filtered_keywords
        LOG.message('Removed {} keywords appearing fewer than {} times'.format(removed, MIN_EVENTS))
        LOG.message('{} unique keywords remaining'.format(len(self.keywords)))
        LOG.leave()

    # def curve_plot(self):
    #     periods = np.linspace(0, 60, 61)
    #     for keyword in self.keywords:
    #         try:
    #             counts = np.array(keyword.counts, np.double)
    #             (a, b, c), pcov = curve_fit(model_curve, periods, counts)
    #             fit = model_curve(periods, a, b, c)
    #             plt.plot(periods, counts, 'b-', label=keyword.keyword)
    #             plt.plot(periods, fit, 'r-', label='fit')
    #             plt.xlabel('period')
    #             plt.ylabel('occurrences')
    #             plt.legend()
    #             plt.show()
    #         except:
    #             pass

    def calculate_entropies(self, ):
        LOG.enter('Calculating keyword entropies')
        progress = len(self.keywords)
        for keyword in self.keywords:
            if progress % 100 == 0:
                print('  Progress: {} '.format(progress), end='\r')
            progress -= 1
            keyword.calculate_relative_entropy()
        LOG.leave()

    def write_keywords(self):
        LOG.enter('Writing keyword entropies')
        filename = CFG.PHASE2_DIR / 'Temp' / 'entropies.csv'
        LOG.message('To {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['KEYWORD', 'POSTAG', 'A', 'B', 'C', 'ENTROPY', 'REL_FREQ', 'PATIENTS'])
            for keyword in self.keywords:
                target.writerow([keyword.keyword, keyword.postag] + list(keyword.relative_abc) + [keyword.relative_entropy, keyword.total_relative_count(), keyword.patients])
        LOG.leave()

    def filter_keywords(self):
        LOG.enter('Filtering keywords')
        keywords = [keyword for keyword in self.keywords if keyword.relative_entropy]
        discard_count = len(self.keywords) - len(keywords)
        self.keywords = keywords
        LOG.message('Discarded {} keywords without entropy.'.format(discard_count))
        LOG.leave()

    def rank_keywords(self):
        LOG.message('Ranking keywords')
        self.keywords.sort(key=lambda keyword: keyword.relative_entropy)

    def write_arff_file(self):
        LOG.enter('Writing selected keywords')
        filename = CFG.PHASE2_DIR / 'Keywords' /'entropy_kwd.arff'
        LOG.message('To {}'.format(filename))
        with open(str(filename), 'w') as target:
            # Relation
            target.write('@relation Keywords\n\n')
            # Attributes
            for keyword in self.keywords:
                target.write("@attribute '{}:{}' numeric\n".format(keyword.keyword, keyword.postag))
            target.write("@attribute 'DaysToLive' numeric\n")
        LOG.leave()


# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    EntropyRanker().run()
    LOG.leave()
