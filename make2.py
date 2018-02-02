from support import config as CFG
from support import logging as LOG
from support import parameters as PAR

from frequency_rank import FrequencyRanker
from word2vec_train import Word2vecTrainer
from word2vec_rank import Word2vecRanker
from entropy_rank import EntropyRanker
from get_arff import ArffGenerator


class Phase2Maker:

    def run(self):
        PAR.read(CFG.SOURCE_DIR)
        FrequencyRanker().run()
        Word2vecTrainer().run()
        Word2vecRanker().run()
        EntropyRanker().run()
        ArffGenerator().run()

if __name__ == '__main__':
    LOG.enter(__file__)
    Phase2Maker().run()
    LOG.leave()
