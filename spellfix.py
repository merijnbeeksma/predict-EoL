from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from collections import Counter, defaultdict
import editdistance
import re

# Filter for acceptable spelling correction targets.
TRUE_WORD = re.compile('[-a-z]+')  # Only letters and dashes
WORD_LIKE = re.compile('[a-z]')    # At least one letter

class SpellingFixer:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        self.read_memo()
        LOG.enter('development set')
        self.read_tokens('dev')
        self.find_contexts()
        self.find_token_freq()
        self.read_opentaal()
        self.correct_spelling()
        self.reconstruct_texts()
        self.write_output('dev')
        LOG.leave()
        LOG.enter('validation set')
        self.read_tokens('val')
        self.find_contexts()
        self.find_token_freq()
        self.read_opentaal()
        self.correct_spelling()
        self.reconstruct_texts()
        self.write_output('val')
        LOG.leave()      
        self.close_transitively()
        self.write_memo()
        LOG.leave()

    # Read spelling corrections memoized during previous sessions.
    def read_memo(self):
        LOG.enter('reading memoized spelling corrections')
        filename = CFG.PHASE1_DIR / 'Temp' / 'spellfix.csv'
        LOG.message('from {}'.format(filename))
        with CSV.FileReader(filename) as source:
            assert next(source) == ['LPOSTAG', 'TYPO', 'RPOSTAG', 'CORRECT']
            self.spellfix = defaultdict(dict)
            for lpostag, typo, rpostag, correct in source:
                context = (lpostag, rpostag)
                self.spellfix[context][typo] = correct
        LOG.message('{} spelling corrections in {} contexts'.format(sum(len(x) for x in self.spellfix.values()), len(self.spellfix)))
        LOG.leave()

    # Form the transitive closure of the dictionary.
    def close_transitively(self):
        LOG.enter('Transitive closure')
        closed_spellfix = defaultdict(dict)
        count = 0
        for context, spellsub in self.spellfix.items():
            for typo, correct in spellsub.items():
                length = 1
                while correct in spellsub:
                    correct = spellsub[correct]
                    length += 1
                if length > 1:
                    count += 1
                closed_spellfix[context][typo] = correct
        self.spellfix = closed_spellfix
        LOG.message('{} corrections applied.'.format(count))
        LOG.leave()

    # Memoize spelling corrections for use in future sessions.
    def write_memo(self):
        LOG.enter('writing memoized spelling corrections')
        filename = CFG.PHASE1_DIR / 'Temp' / 'spellfix.csv'
        LOG.message('to {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['LPOSTAG', 'TYPO', 'RPOSTAG', 'CORRECT'])
            for context in self.spellfix:
                for typo, correct in self.spellfix[context].items():
                    target.writerow([context[0], typo, context[1], correct])
        LOG.message('{} spelling corrections in {} contexts'.format(sum(len(x) for x in self.spellfix.values()), len(self.spellfix)))
        LOG.leave()

    # Read the tokens to spellfix.
    # Memoized spelling corrections are applied immediately.
    def read_tokens(self, data_set):
        LOG.enter('reading tokens')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_tokens.csv'.format(data_set)
        LOG.message('from {}'.format(filename))
        self.tokens = []
        with CSV.FileReader(filename) as source:
            assert next(source) == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TOKEN', 'POSTAG']
            for praktijk_id, patient_id, levensverwachting, token, postag in source:
                self.tokens.append((praktijk_id, patient_id, levensverwachting, token, postag))
        # del self.tokens[100000:]
        LOG.message('{} tokens'.format(len(self.tokens)))
        LOG.leave()

    # Find the set of words that can appear in any given context.
    # Tokens containing punctuation or digits are rejected.
    def find_contexts(self):
        LOG.enter('finding tokens in context')
        self.contexts = defaultdict(set)
        for index in range(1, len(self.tokens) - 1):
            token = self.tokens[index][3]
            if TRUE_WORD.fullmatch(token):  # No punctuation, digits etc.
                left_postag = self.tokens[index - 1][4]
                right_postag = self.tokens[index + 1][4]
                context = (left_postag, right_postag)
                self.contexts[context].add(token)
        LOG.message('{} contexts'.format(len(self.contexts)))
        LOG.message('{} unique tokens-in-context'.format(sum(len(tokens) for tokens in self.contexts.values())))
        LOG.leave()
        
    # Find the frequency of all tokens over the entire corpus.
    def find_token_freq(self):
        LOG.enter('counting token frequencies')
        self.token_freq = Counter()
        for praktijk_id, patient_id, levensverwachting, token, postag in self.tokens:
            self.token_freq[token] += 1
        LOG.message('{} unique tokens'.format(len(self.token_freq)))
        LOG.leave()

    # Read the OpenTaal word frequencies,
    # but convert the words to lower case.
    def read_opentaal(self):
        LOG.enter('reading OpenTaal word frequencies')
        filename = CFG.DATA_DIR / 'word_frequencies.csv'
        LOG.message('from {}'.format(filename))
        # Read the frequency list, converting words to lower case
        self.opentaal_freq = Counter()
        with CSV.FileReader(filename) as source:
            for word, freq in source:
                word = word.lower()
                freq = int(freq)
                self.opentaal_freq[word] += freq
        self.opentaal_freq = {word: freq for word, freq in self.opentaal_freq.items() if freq >= PAR.MIN_OPENTAAL_FREQ}
        LOG.message('{} words'.format(len(self.opentaal_freq)))
        LOG.leave()

    # Run each token in turn through the decision tree.
    # TODO: Since different contexts have different numbers of tokens that appear
    # in that context, we should require a different minimum frequency for each
    # context. But how, exactly?
    def correct_spelling(self):
        LOG.enter('Correcting spelling')
        LOG.message('{} tokens to check'.format(len(self.tokens)))
        tokens = []
        for index, (praktijk_id, patient_id, levensverwachting, token, postag) in enumerate(self.tokens):
            if index % 1000 == 0: print(index, end='\r')
            lpostag = self.tokens[index - 1][4]
            rpostag = self.tokens[(index + 1) % len(self.tokens)][4]
            context = (lpostag, rpostag)
            if context in self.spellfix and token in self.spellfix[context]:
                # If a known spelling correction exists, apply that.
                replacement = self.spellfix[context][token]
                tokens.append((praktijk_id, patient_id, levensverwachting, replacement, postag))
            elif token in self.opentaal_freq:
                # If a token has a high OpenTaal frequency, we assume it's spelled correctly.
                tokens.append((praktijk_id, patient_id, levensverwachting, token, postag))
            elif self.token_freq[token] >= PAR.MIN_EPD_FREQ:
                # If a token has a high corpus frequency, we assume it's spelled correctly
                tokens.append((praktijk_id, patient_id, levensverwachting, token, postag))
            else:
                # Otherwise, we suspect a spelling mistake.
                replacement = self.find_replacement(context, token)
                if replacement:
                    token = replacement
                    tokens.append((praktijk_id, patient_id, levensverwachting, token, postag))
                else:
                    replacement = self.onterechte_samenstelling(context, token)
                    if replacement:
                        for token in replacement:
                            tokens.append((praktijk_id, patient_id, levensverwachting, token, postag))
                    else:
                        tokens.append((praktijk_id, patient_id, levensverwachting, token, postag))
        self.tokens = tokens
        LOG.leave()

    def find_replacement(self, context, token):
        candidates = []
        min_dist = PAR.MAX_REL_EDIT_DIST
        for candidate in self.contexts[context]:
            # Consider only candidates with a higher corpus frequency.
            if self.token_freq[candidate] <= self.token_freq[token]: continue
            if self.token_freq[candidate] <= PAR.MIN_EPD_FREQ: continue
            abs_edit_dist = editdistance.Levenshtein(candidate, token)
            rel_edit_dist = abs_edit_dist / len(token)
            if rel_edit_dist <= min_dist:
                if rel_edit_dist < min_dist:
                    candidates = []
                    min_dist = rel_edit_dist
                candidates.append(candidate)
        if len(candidates) == 0:
            return None
        elif len(candidates) == 1:
            replacement = candidates[0]
            self.add_spellfix(context, token, replacement)
            return replacement
        else:
            candidates = [(self.token_freq[candidate], candidate) for candidate in candidates]
            replacement = max(candidates)[1]
            # print(token, candidates, replacement)
            self.add_spellfix(context, token, replacement)
            return replacement
            
    def add_spellfix(self, context, typo, correct):
        if context not in self.spellfix or typo not in self.spellfix[context]:
            # New spelling correction
            self.spellfix[context][typo] = correct
        elif self.spellfix[context][typo] == correct:
            assert False
        else:
            # Correct the same token to a different replacement
            print('SPELLFIX COLLISION: {} {} {} => {}'.format(context[0], typo, context[1], self.spellfix[context][typo], correct))            
            pass

    def onterechte_samenstelling(self, context, token):
        # Don't try obvious non-words such as dates and numbers
        if not WORD_LIKE.search(token): return
        
        # Find the most plausible split. Plausibility is defined as the corpus frequency
        # of the least frequent of the left and right parts.
        best_plausibility = 0
        best_split = None
        for i in range(2, len(token) - 1):
            if token[i] == '-': continue
            left, right = token[:i].strip('-'), token[i:].strip('-')
            if left not in self.token_freq or right not in self.token_freq: continue
            plausibility = min(self.token_freq[left], self.token_freq[right])
            if plausibility < PAR.MIN_EPD_FREQ: continue  # Implausible
            if plausibility == best_plausibility:
                print('SPLIT COLLISION: {} => {} or {} with p = {}'.format(token, best_split, (left, right), plausibility))
                pass
            elif plausibility > best_plausibility:
                best_plausibility = plausibility
                best_split = (left, right)
        if best_split:
            self.add_spellfix(context, token, ' '.join(best_split))
        return best_split            

    def reconstruct_texts(self):
        self.texts = []
        current_key = None
        current_tokens = []
        for praktijk_id, patient_id, levensverwachting, token, postag in self.tokens:
            key = (praktijk_id, patient_id, levensverwachting)
            if key != current_key:
                if current_key:
                    text = ' '.join(current_tokens)
                    self.texts.append(current_key + (text,))
                current_key = key
                current_tokens = []
            current_tokens.append(token)
        text = ' '.join(current_tokens)
        self.texts.append(current_key + (text,))

    def write_output(self, data_set):
        LOG.enter('writing texts')
        filename = CFG.PHASE1_DIR / 'Temp' / '{}_texts3.csv'.format(data_set)
        LOG.message('to {}'.format(filename))
        with CSV.FileWriter(filename) as target:
            target.writerow(['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'TEXT'])
            for row in self.texts:
                target.writerow(row)
        LOG.message('{} texts'.format(len(self.texts)))
        LOG.leave()


if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    SpellingFixer().run()
    LOG.leave()
