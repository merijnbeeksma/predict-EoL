from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import epd_corpus
import unicodedata
from collections import Counter
import re


# Leestekes naar spaties converteren
PUNCTORS = ',:;!?/|\+=*"\'()[]<>«»'  # Niet de punt!
PUNCTUATION = str.maketrans(PUNCTORS, len(PUNCTORS) * ' ')

# Used to find all the tokens in a document.
# A token is defined as a sequence of 'word characters', full stops and dashes.
# This yields some words with unwanted characters, which are excluded in a separate step.
TOKEN_INCL = re.compile(r'[\w\.\-]{3,}')
TOKEN_EXCL = re.compile(r'[\d@]')

# An initialism consists of two or more letters, each letter followed by a full stop.
INITIALISM = re.compile(r'( |\A)([a-z]\.){2,}( |\Z)')   # ' d.w.z.'

# Tokens are further split at full stops, dashes and underscores.
SEPARATOR = re.compile('[-_\.]')


class Lemmatizer:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.corpus = epd_corpus.read(epd_corpus.DataSet.DEVELOPMENT)
        self.count_tokens()
        self.lemmatize_tokens()
        self.apply_whitelist()
        self.filter_lemmas()
        self.filter_tokens()
        self.write_tokens()
        self.write_lemmas()
        LOG.leave()

    def count_tokens(self):
        self.token_freq = Counter()
        for praktijk in self.corpus.praktijken:
            for patient in praktijk.patienten:
                for contact in patient.contacten:
                    for deelcontact in contact.deelcontacten:
                        for brief in deelcontact.brieven:
                            self.process_document(brief)
                        for notitie in deelcontact.notities:
                            self.process_document(notitie)

    def process_document(self, document):
        # Canonicalisatie: alles downcasen
        tekst = document.tekst.casefold()
        # Aanhef en slot van een brief verwijderen
        if isinstance(document, epd_corpus.Brief):
            for zoekterm in ['geachte']:
                p = tekst.find(zoekterm)
                if p >= 0:
                    p = tekst.find(',', p)
                    if p >= 0:
                        aanhef, tekst = tekst[:p+1], tekst[p+1:]
                        break
            for zoekterm in ['met vriendelijke', 'met collegiale', 'met hoogachting', 'hoogachtend', 'groet']:
                p = tekst.find(zoekterm)
                if p >= 0:
                    tekst, slot = tekst[:p], tekst[p:]
                    break
        # Woorden tellen
        for match in TOKEN_INCL.finditer(tekst):
            token = match.group(0)
            if not TOKEN_EXCL.search(token):  # Reject tokens with digits
                if token == 'misseleijk': print(token)
                self.token_freq[token] += 1

    def lemmatize_tokens(self):
        LOG.enter('lemmatizing tokens')
        # Spelling
        filename = CFG.DATA_DIR / 'spelling.csv'
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PATTERN', 'REPLACEMENT']
            self.spelling = [(re.compile(pattern), replacement) for pattern, replacement in source]
        # Prefixes
        filename = CFG.DATA_DIR / 'prefix.csv'
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PREFIX', 'REPLACEMENT']
            self.prefixes = [(prefix, replacement) for prefix, replacement in source]
        # Postfixes
        filename = CFG.DATA_DIR / 'postfix.csv'
        with CSV.FileReader(filename) as source:
            assert next(source) == ['POSTFIX', 'REPLACEMENT']
            self.postfixes = [(re.compile(postfix + r'\Z'), replacement) for postfix, replacement in source]
        # Lemmatiseren
        self.token_lemmas = {}
        for token in self.token_freq:
            lemmas = self.lemmatize(token)
            self.token_lemmas[token] = lemmas
        LOG.leave()

    # Converts a token into a list of zero or more lemmas.
    def lemmatize(self, token):
        # Initialisms (example: 'e.c.g.' => 'ecg')
        if INITIALISM.fullmatch(token):
            lemma = ''.join(c for c in token if c.isalpha())
            return [lemma]
        # Gently correct a few common spelling errors
        lemma = token
        for pattern, replacement in self.spelling:
            lemma = pattern.sub(replacement, lemma)
        # Tweak affixes just because we can!
        for prefix, replacement in self.prefixes:
            if lemma.startswith(prefix):
                lemma = replacement + lemma[len(prefix):]
                break
        for postfix, replacement in self.postfixes:
            lemma, count = postfix.subn(replacement, lemma)
            if count: break
        # Split the lemma into sublemmas at full stops and dashes
        if SEPARATOR.search(lemma):
            lemmas = SEPARATOR.split(lemma)  # Split at . and -
            lemmas = [lemma for lemma in lemmas if lemma]  # Remove empty sublemmas
            lemmas = [self.lemmatize(lemma) for lemma in lemmas]
            lemmas = sum(lemmas, [])  # Flatten the list of lists
            return lemmas
        # Klaar!
        return [lemma]

    def apply_whitelist(self):
        LOG.enter('apply whitelist')
        filename = CFG.DATA_DIR / 'white.csv'
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['TOKEN', 'LEMMA']
            for token, lemmas in source:
                self.token_lemmas[token] = lemmas.split()
        LOG.leave()

    def filter_lemmas(self):
        # Count lemmas
        self.lemma_freq = Counter()
        for token, lemmas in self.token_lemmas.items():
            freq = self.token_freq[token]
            for lemma in lemmas:
                self.lemma_freq[lemma] += freq
        # Discard all but the most frequent lemmas
        self.lemma_freq = list(self.lemma_freq.items())
        self.lemma_freq.sort(key=lambda lf: lf[1], reverse=True)
        #
        self.lemma_freq = dict(self.lemma_freq)

    def filter_tokens(self):
        # Adjust for deleted tokens
        for token, lemmas in self.token_lemmas.items():
            lemmas = [lemma for lemma in lemmas if lemma in self.lemma_freq]
            self.token_lemmas[token] = lemmas

    def write_tokens(self):
        LOG.enter('writing tokens')
        filename = CFG.PHASE1_DIR / 'tokens.csv'
        LOG.message('to {}'.format(filename))
        LOG.message('{} unique tokens'.format(len(self.token_lemmas)))
        with CSV.FileWriter(filename) as target:
            target.writerow(['FREQUENCY', 'TOKEN', 'LEMMAS'])
            for token, lemmas in self.token_lemmas.items():
                freq = self.token_freq[token]
                # hack
                lemmas = [l for l in lemmas if self.lemma_freq[l] >= PAR.MIN_LEMMA_FREQ]
                #
                lemmas = ' '.join(lemmas)
                target.writerow([freq, token, lemmas])
        LOG.leave()

    def write_lemmas(self):
        LOG.enter('writing lemmas')
        filename = CFG.PHASE1_DIR / 'lemmas.csv'
        LOG.message('to {}'.format(filename))
        LOG.message('{} lemmas'.format(len(self.lemma_freq)))
        with CSV.FileWriter(filename) as target:
            target.writerow(['FREQUENCY', 'LEMMA'])
            for lemma, freq in self.lemma_freq.items():
                target.writerow([freq, lemma])
        LOG.leave()


if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    Lemmatizer().run()
    LOG.leave()
