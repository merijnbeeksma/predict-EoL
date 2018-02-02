from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from collections import Counter

class WordfreqOptimizer:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.read_opentaal()
        self.downcase()
        self.sort()
        self.write_output()
        LOG.leave()

    def read_opentaal(self):
        LOG.enter('reading OpenTaal word frequencies')
        filename = CFG.DATA_DIR / 'word_frequencies.csv'
        LOG.message('from {}'.format(filename))
        self.opentaal = []
        with CSV.FileReader(filename) as source:
            for word, freq in source:
                freq = int(freq)
                self.opentaal.append((word, freq))
        unique_words = len(self.opentaal)
        corpus_size = sum(freq for word, freq in self.opentaal)
        LOG.message('{} unique words, {} tokens'.format(unique_words, corpus_size))
        LOG.leave()

    # Downcase all words, merging the frequencies of words that are identical
    # except for casing.
    def downcase(self):
        LOG.enter('downcasing words')
        self.wordfreq = Counter()
        count = 0
        for word, freq in self.opentaal:
            lc_word = word.casefold()
            if word != lc_word:
                count += 1
            self.wordfreq[lc_word] += freq
        LOG.message('{} words downcased'.format(count))
        LOG.leave()

    # Sort by descending frequency then by ascending word. This makes it easy
    # to perform queries such as:
    #  *  take the top-100000 most frequent words;
    #  *  take all words with frequency 100 or more.
    def sort(self):
        def order(word_freq):
            word, freq = word_freq
            return (-freq, word)
        LOG.enter('sorting words')
        self.wordfreq = sorted(self.wordfreq.items(), key=order)
        LOG.leave()

    def write_output(self):
        LOG.enter('writing optimized word frequencies')
        filename = CFG.PHASE1_DIR / 'Temp' / 'wordfreq.csv'
        LOG.message('to {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['WORD', 'FREQUENCY'])
            for row in self.wordfreq:
                target.writerow(row)
        unique_words = len(self.wordfreq)
        corpus_size = sum(freq for word, freq in self.wordfreq)
        LOG.message('{} unique words, {} tokens'.format(unique_words, corpus_size))
        LOG.leave()

if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    WordfreqOptimizer().run()
    LOG.leave()
