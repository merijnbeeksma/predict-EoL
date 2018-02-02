from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

import math
import os
import random
from collections import Counter
from datetime import date
from pathlib import Path
import tensorflow as tf
import numpy as np
from datetime import datetime

class Patient:
    pass


class TensorFlower():

    def run(self, directory):
        LOG.enter(self.__class__.__name__ + '.run()')
        if PAR.WORKFLOW == 'DEVELOPMENT':
            # There are always 10 folds, but PAR.FOLDS allows us to calculate fewer of them.
            for fold in range(PAR.FOLDS):
                LOG.enter('fold {}'.format(fold))
                trainer = Trainer(fold, directory)
                trainer.run()
                LOG.leave()
        elif PAR.WORKFLOW == 'VALIDATION':
            trainer = Trainer(fold=None, directory=directory)
            trainer.run()
        LOG.leave()


class Trainer():

    def __init__(self, fold, directory):
        self.fold = fold
        self.directory = directory

    def run(self):
        if PAR.WORKFLOW == 'DEVELOPMENT':
            filename = str(self.directory / 'train_{}.csv'.format(self.fold))
            self.train_patienten = self.read_patienten(filename)
            filename = str(self.directory / 'test_{}.csv'.format(self.fold))
            self.test_patienten = self.read_patienten(filename)
            self.features = self.collect_features(self.train_patienten)
            self.train_lstm()
        elif PAR.WORKFLOW == 'VALIDATION':
            filename = str(self.directory / 'train.csv')
            self.train_patienten = self.read_patienten(filename)
            filename = str(self.directory / 'test.csv')
            self.test_patienten = self.read_patienten(filename)
            self.features = self.collect_features(self.train_patienten)
            self.train_lstm()

    def read_patienten(self, filename):
        patienten = []
        with CSV.FileReader(filename) as source:
            headers = next(source)
            assert headers[:2] == ['PRAKTIJK-ID', 'PATIENT-ID']
            del headers[:2]
            for maand, header in enumerate(headers):
                assert header == 'P{0}'.format(maand)
            self.num_bins = len(headers)
            for row in source:
                patient = Patient()
                patient.praktijk = row[0]
                patient.id = row[1]
                patient.historie = []
                for period_num, data in enumerate(row[2:]):  # data is something like 'r:abc=1,i:f39=2'
                    period = []
                    if data:
                        items = data.split(',')
                        for item in items:
                            feature, frequentie = item.split('=')
                            period.append((feature, float(frequentie)))
                    patient.historie.append(period)
                patienten.append(patient)
        return patienten

    def collect_features(self, patienten):
        features = set()
        for patient in patienten:
            for period in patient.historie:
                for feature, frequentie in period:
                    features.add(feature)
        features = {feature: index for index, feature in enumerate(sorted(features))}
        return features

    # Returns a list of feature vectors, with one feature vector for each period
    def generate_vectors(self, historie):
        feature_vectors = []
        for period in historie:
            feature_vector = len(self.features) * [0]
            for feature, frequentie in period:
                if feature in self.features:
                    index = self.features[feature]
                    feature_vector[index] = frequentie
            feature_vectors.append(np.array(feature_vector))
        return feature_vectors

    def train_lstm(self):
        # Prepare training data
        train_data = []
        for patient in self.train_patienten:
            feature_vectors = self.generate_vectors(patient.historie)
            win_begin, win_end = 0, PAR.WINDOW_SIZE
            while win_end <= PAR.HISTORY_LENGTH:
                window_vectors = feature_vectors[win_begin:win_end]
                if sum(np.count_nonzero(v) for v in window_vectors):
                    label = np.array([1 if period == win_begin else 0 for period in range(PAR.HISTORY_LENGTH - PAR.WINDOW_SIZE + 1)])  #one hot
                    if PAR.LAST_PERIOD == False:
                        if label[0] == 0:
                            train_data.append((window_vectors, label))
                    else:
                        train_data.append((window_vectors, label))
                win_begin += 1
                win_end += 1
        random.shuffle(train_data)

        # Prepare test data
        test_data = []
        for patient in self.test_patienten:
            feature_vectors = self.generate_vectors(patient.historie)
            win_begin, win_end = 0, PAR.WINDOW_SIZE
            while win_end <= PAR.HISTORY_LENGTH:
                window_vectors = feature_vectors[win_begin:win_end]
                if sum(np.count_nonzero(v) for v in window_vectors):
                    label = np.array([1 if period == win_begin else 0 for period in range(PAR.HISTORY_LENGTH - PAR.WINDOW_SIZE + 1)])  #one hot
                    if PAR.LAST_PERIOD == False:
                        if label[0] == 0:
                            test_data.append((patient.praktijk, patient.id, win_begin, window_vectors, label))  # win_begin is de ouderdom: periods to live
                    else:
                        test_data.append((patient.praktijk, patient.id, win_begin, window_vectors, label))  # win_begin is de ouderdom: periods to live
                win_begin += 1
                win_end += 1
        random.shuffle(test_data)

        # Build TensorFlow graph
        tf.reset_default_graph()
        data = tf.placeholder(tf.float32, [None, PAR.WINDOW_SIZE, len(self.features)])
        target = tf.placeholder(tf.float32, [None, PAR.HISTORY_LENGTH - PAR.WINDOW_SIZE + 1])
        layers = [] # network layers: each layer is a block of dropout cells
        for layer_num in range(PAR.NUM_LAYERS):
            cell_block = tf.nn.rnn_cell.LSTMCell(PAR.NUM_HIDDEN, state_is_tuple=True, use_peepholes=False) # LSTM cell block with PAR.NUM_HIDDEN hidden cells
            layer = tf.nn.rnn_cell.DropoutWrapper(cell=cell_block, input_keep_prob=1.0, output_keep_prob=1.0) # apply dropout to LSTM cell_block while training, but not while testing
            layers.append(layer) # add to stack
        network = tf.nn.rnn_cell.MultiRNNCell(layers, state_is_tuple=True) # connect layers into a network
        # train and test
        val, state = tf.nn.dynamic_rnn(network, data, dtype=tf.float32)
        val = tf.transpose(val, [1, 0, 2])
        last = tf.gather(val, int(val.get_shape()[0]) - 1)
        weight = tf.Variable(tf.truncated_normal([PAR.NUM_HIDDEN, int(target.get_shape()[1])]))
        bias = tf.Variable(tf.constant(0.1, shape=[target.get_shape()[1]]))
        prediction = tf.nn.softmax(tf.matmul(last, weight) + bias)
        cross_entropy = -tf.reduce_sum(target * tf.log(tf.clip_by_value(prediction,1e-10,1.0)))
        optimizer = tf.train.AdamOptimizer(PAR.LEARNING_RATE)
        minimize = optimizer.minimize(cross_entropy)
        # initialize
        init_op = tf.global_variables_initializer()
        sess = tf.Session()
        sess.run(init_op)
        no_of_batches = int(len(train_data) / PAR.BATCH_SIZE)
        loss_overview = {}

        if PAR.WORKFLOW == 'DEVELOPMENT':
            filename = str(self.directory / 'loss_{}.csv'.format(self.fold))
        elif PAR.WORKFLOW == 'VALIDATION':
            filename = str(self.directory / 'loss.csv')
        with CSV.FileWriter(filename) as output:
            output.writerow(['EPOCH', 'TRAIN', 'TEST'])

            for epoch in range(PAR.EPOCHS):
                LOG.enter('epoch {}'.format(epoch))

                # training
                LOG.enter('training')
                for layer in layers:
                    layer._input_keep_prob = PAR.DROPOUT
                    layer._output_keep_prob = 1.0
                pointer = 0
                for j in range(no_of_batches):
                    batch = train_data[pointer:pointer + PAR.BATCH_SIZE]
                    vectors = [v for v, l in batch]
                    labels = [l for v, l in batch]
                    pointer += PAR.BATCH_SIZE
                    _, batch_loss = sess.run([minimize, cross_entropy], {data: vectors, target: labels})
                train_loss = batch_loss / PAR.BATCH_SIZE # mean loss per train case
                LOG.leave() # training

                # Test
                LOG.enter('testing')
                for layer in layers:
                    layer._input_keep_prob = 1.0
                    layer._output_keep_prob = 1.0
                test_loss = 0
                for praktijk, patient_id, ouderdom, feature_vectors, label in test_data:
                    _, case_loss = sess.run([prediction, cross_entropy], {data: [feature_vectors], target: [label]})
                    test_loss += case_loss
                    predict = sess.run(prediction, {data: [feature_vectors], target: [label]})[0]
                    levensverwachting = np.argmax(predict)
                    predict = ','.join('{:7.4f}'.format(p) for p in predict)
                test_loss /= len(test_data) # mean loss per test case
                LOG.leave() # testing

                output.writerow([epoch, train_loss, test_loss])
                LOG.leave() # epoch

        # Write final test results
        if PAR.WORKFLOW == 'DEVELOPMENT':
            filename = str(self.directory / 'result_{}.csv'.format(self.fold))
        elif PAR.WORKFLOW == 'VALIDATION':
            filename = str(self.directory / 'result.csv')
        with CSV.FileWriter(filename) as output:
            output.writerow(['PRAKTIJK', 'PATIENT-ID', 'OUDERDOM', 'ARGMAX', 'PREDICTION'])
            for praktijk, patient_id, ouderdom, feature_vectors, label in test_data:
                predict = sess.run(prediction, {data: [feature_vectors], target: [label]})[0]
                levensverwachting = np.argmax(predict)
                predict = ','.join('{:7.4f}'.format(p) for p in predict)
                output.writerow([praktijk, patient_id, ouderdom, levensverwachting, predict])

        sess.close()


if __name__ == '__main__':
    LOG.enter(__file__)
    PAR.read(CFG.SOURCE_DIR)
    if PAR.WORKFLOW == 'DEVELOPMENT':
        TensorFlower().run(CFG.PHASE3_DIR)
    elif PAR.WORKFLOW == 'VALIDATION':
        TensorFlower().run(CFG.PHASE4_DIR)
    LOG.leave()
