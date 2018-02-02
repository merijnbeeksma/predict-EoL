from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import word2vec


class Word2vecRanker:

    def run(self):
        LOG.enter(self.__class__.__name__ + '.run()')
        source = CFG.PHASE2_DIR / 'Temp' / 'word2vec_train.txt'
        for dim in PAR.WORD2VEC_DIMS:
            LOG.enter('{} dimensions'.format(dim))
            target = CFG.PHASE2_DIR / 'Keywords' / 'word2vec_{}.txt'.format(dim)
            LOG.message('Reading {}'.format(source))
            LOG.message('Writing {}'.format(target))
            word2vec.word2vec(str(source), str(target), size=dim, cbow=1, threads=4, binary=0)
            LOG.leave()
        LOG.leave()


# Main program
if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    Word2vecRanker().run()
    LOG.leave()
