#coding:utf-8

import time
import warnings
import numpy as np
import scipy.io as sio
# import matplotlib.pyplot as plt
from numpy import newaxis
from keras.optimizers import SGD
from keras.models import Sequential
from keras.layers import Convolution2D, AtrousConvolution2D, UpSampling2D
from keras.layers import ZeroPadding2D, MaxPooling2D
from keras.layers.normalization import BatchNormalization
from keras.layers.core import Dense, Dropout, Activation, Flatten, Reshape
from keras.layers.noise import GaussianDropout
from keras.layers.noise import GaussianNoise

warnings.filterwarnings("ignore")


def load_data():
    # f = open(filename, 'rb').read()
    # data = f.split('\n')

    # sequence_length = seq_len + 1
    # result = []
    # for index in range(len(data) - sequence_length):
    #    result.append(data[index: index + sequence_length])

    # if normalise_window:
    #     result = normalise_windows(result)

    # plt.plot(result)
    # plt.show()

    mat_input = 'inputShortV.mat'
    input = sio.loadmat(mat_input)
    input = 3 * input['inputShortV']

    # plt.plot(input)
    # plt.show()

    mat_target = 'targetCodeShortV.mat'
    target = sio.loadmat(mat_target)
    target = target['targetCodeShortV']

    # fig = plt.figure(facecolor='white')
    # ax = fig.add_subplot(111)
    # ax.plot(target, label='True Data')
    # plt.plot(input[:,1]/3,label='Quantization')
    # plt.legend()
    # plt.show()

    input = np.array(input)
    target = np.array(target)

    row = int(round(0.86 * input.shape[0]))
    train_input = input[:row, :]
    train_target = target[:row, :]

    train = np.column_stack((train_input, train_target))
    np.random.shuffle(train)

    x_train = train[:, 0:20]
    y_train = train[:, 20:84]
    # plt.plot(y_train)
    # plt.show()
    train_input = []
    train_target = []
    train = []

    x_test = input[row:, :]
    y_test = target[row:, :]
    input = []
    target = []

    x_train = np.reshape(x_train, (x_train.shape[0], 1, x_train.shape[1]))  # (examples, values in sequences, dim. of each value)
    x_test = np.reshape(x_test, (x_test.shape[0], 1, x_test.shape[1]))      # (examples, values in sequences, dim. of each value)

    data = np.empty((x_train.shape[0], 1, 20, 20), dtype="float64")
    test = np.empty((x_test.shape[0], 1, 20, 20), dtype="float64")
    for i in range(20):
        data[:, :, :, i] = np.roll(x_train, i, axis=2)
        test[:, :, :, i] = np.roll(x_test, i, axis=2)

    x_train = data
    data = []
    x_test = test
    test = []

    return [x_train, y_train, x_test, y_test]


def normalise_windows(window_data):
    normalised_data = []
    for window in window_data:
        normalised_window = [((float(p) / float(window[0])) - 1) for p in window]
        normalised_data.append(normalised_window)

    return normalised_data


def build_model():
    model = Sequential()

    # 第一个卷积层，4个卷积核
    model.add(ZeroPadding2D((1, 1), dim_ordering='th', input_shape=(1, 20, 20)))
    model.add(Convolution2D(32, 3, 3, activation='relu'), dim_ordering='th')

    model.add(ZeroPadding2D((1, 1)))
    model.add(Convolution2D(32, 3, 3, activation='relu', dim_ordering='th'))
    model.add(MaxPooling2D((2, 2), dim_ordering='th'))

    model.add(ZeroPadding2D((1, 1)))
    model.add(Convolution2D(64, 3, 3, activation='relu', dim_ordering='th'))
    model.add(MaxPooling2D((2, 2), dim_ordering='th'))

    model.add(Flatten())
    model.add(Dense(64, activation='relu'))
    model.add(Dropout(0.2))
    model.add(Dense(64, activation='softmax'))

    start = time.time()

    # 使用SGD + momentum
    # model.compile里的参数loss就是损失函数(目标函数)
    sgd = SGD(lr=0.1, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(optimizer=sgd, loss='categorical_crossentropy')
    # model.compile(loss="mse", optimizer="rmsprop") # mse kld # Nadam  rmsprop
    print "Compilation Time : ", time.time() - start
    return model


def predict_point_by_point(model, data):
    # Predict each time step given the last sequence of true data, in effect only predicting 1 step ahead each time
    predicted = model.predict(data)
    # predicted = np.reshape(predicted, (predicted.size,))
    return predicted


def predict_sequence_full(model, data, window_size):
    # Shift the window by 1 new prediction each time, re-run predictions on new window
    curr_frame = data[0]
    predicted = []
    for i in xrange(len(data)):
        predicted.append(model.predict(curr_frame[newaxis,:,:])[0,0])
        curr_frame = curr_frame[1:]
        curr_frame = np.insert(curr_frame, [window_size-1], predicted[-1], axis=0)

    return predicted


def predict_sequences_multiple(model, data, window_size, prediction_len):
    # Predict sequence of 50 steps before shifting prediction run forward by 50 steps
    prediction_seqs = []
    for i in xrange(len(data)/prediction_len):
        curr_frame = data[i*prediction_len]
        predicted = []
        for j in xrange(prediction_len):
            predicted.append(model.predict(curr_frame[newaxis,:,:])[0,0])
            curr_frame = curr_frame[1:]
            curr_frame = np.insert(curr_frame, [window_size-1], predicted[-1], axis=0)
        prediction_seqs.append(predicted)

    return prediction_seqs