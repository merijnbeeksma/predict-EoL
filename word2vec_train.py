# Prepares training sets for word2vec.


from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR


class Word2vecTrainer:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        source_name = CFG.PHASE1_DIR / 'Keywords' / 'dev_kwd.csv'
        LOG.message('Reading {}'.format(source_name))
        target_name = CFG.PHASE2_DIR / 'Temp' / 'word2vec_train.txt'
        LOG.message('Writing {}'.format(target_name))
        with CSV.FileReader(source_name) as source:
            header = next(source)
            assert header == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'LEMMA', 'POSTAG']
            with open(str(target_name), 'w') as target:
                doc_key = None
                doc_words = []
                doc_count, word_count = 0, 0
                for praktijk_id, patient_id, levensverwachting, lemma, postag in source:
                    if (praktijk_id, patient_id, levensverwachting) != doc_key:
                        if doc_key:
                            target.write(' '.join(doc_words))
                            target.write('\n')
                            doc_count += 1
                            word_count += len(doc_words)
                        doc_words = []
                        doc_key = (praktijk_id, patient_id, levensverwachting)
                    doc_words.append('{}:{}'.format(lemma, postag))
                target.write(' '.join(doc_words))
                target.write('\n')
                doc_count += 1
                word_count += len(doc_words)
        LOG.message('{} words in {} documents'.format(word_count, doc_count))
        LOG.leave()


# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    Word2vecTrainer().run()
    LOG.leave()
