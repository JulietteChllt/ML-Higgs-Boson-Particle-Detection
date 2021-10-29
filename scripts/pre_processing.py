import numpy as np
from numpy import genfromtxt
import math
from proj1_helpers import *
from sklearn.preprocessing import PolynomialFeatures
import seaborn as sns


class LoadTrainingDataset():

    def __init__(self, path):
        my_dict = {'s': 1, 'b': 0}
        self.y = np.loadtxt(path, delimiter=",",
                            dtype=np.str_, skiprows=1, usecols=1)
        self.y = np.array([my_dict[i] for i in self.y])
        self.y = self.y.reshape(self.y.shape[0], 1)
        self.x = np.loadtxt(path, delimiter=",",
                            skiprows=1, usecols=range(2, 32))
        self.ids = np.loadtxt(path, delimiter=",", skiprows=1, usecols=0)
        self.ids = self.ids.reshape(self.ids.shape[0], 1)
        self.n_samples = self.x.shape[0]

    def __getitem__(self, i):
        return self.x[i], self.y[i], self.ids[i]

    def __len__(self):
        return self.n_samples

    def get_data(self):
        return self.x, self.y, self.ids


class LoadTestingDataset():
    def __init__(self, path):
        self.x = np.loadtxt(path, delimiter=",",
                            skiprows=1, usecols=range(2, 32))
        self.ids = np.loadtxt(path, delimiter=",", skiprows=1, usecols=0)
        self.ids = self.ids.reshape(self.ids.shape[0], 1)
        self.n_samples = self.x.shape[0]

    def __getitem__(self, i):
        return self.x[i], self.ids[i]

    def __len__(self):
        return self.n_samples

    def get_data(self):
        return self.x, self.ids


def separate_data(tx, y, ids):

    array_1 = np.where((tx[:, 22] != 0))[0]
    tx_1 = np.delete(tx, array_1, 0)
    y_1 = np.delete(y, array_1, 0)
    ids_1 = np.delete(ids, array_1, 0)

    array_2 = np.where((tx[:, 22] != 1))[0]
    tx_2 = np.delete(tx, array_2, 0)
    y_2 = np.delete(y, array_2, 0)
    ids_2 = np.delete(ids, array_2, 0)

    array_3 = np.nonzero(np.logical_or((tx[:, 22] == 0), (tx[:, 22] == 1)))[0]
    tx_3 = np.delete(tx, array_3, 0)
    y_3 = np.delete(y, array_3, 0)
    ids_3 = np.delete(ids, array_3, 0)

    return (tx_1, y_1, ids_1), (tx_2, y_2, ids_2), (tx_3, y_3, ids_3)


def adapt_features(data_n):

    tx_n = data_n[0]
    to_delete = np.zeros(tx_n.shape[0])-999
    indexes = []
    for i in range(tx_n.shape[1]):
        # Find unique values in column along with their length
        # if len is == 1 then it contains same values i.e -999 so features to drop or zeros
        if len(np.unique(tx_n[:, i])) == 1:
            indexes.append(i)

    tx_n = np.delete(tx_n, indexes, 1)

    return (tx_n, data_n[1], data_n[2]), indexes


def add_median(data_n):

    tx_n = data_n[0]
    for i in range(tx_n.shape[1]):
        column = tx_n[:, i]
        m = np.median(column[column != -999])
        column[column == -999] = m
        tx_n[:, i] = column

    return (tx_n, data_n[1], data_n[2])


def dimensionality_reduction_corr(data_n):
    tx_n = data_n[0]
    corr = np.corrcoef(tx_n.T)
    pairs = np.argwhere(np.triu(np.isclose(corr, 1, rtol=2e-01), 1))
    indexes = pairs[:, 1]
    tx_n = np.delete(tx_n, indexes, axis=1)
    return (tx_n, data_n[1], data_n[2]), indexes


def dimensionality_reduction_PCA(data_n, k):
    # Compare performance with dimen reduc correlation first
    tx_n = data_n[0]
    # standardize the data
    tx_n = (tx_n - np.mean(tx_n, axis=0))/np.std(tx_n, axis=0)
    # compute covariance matrix
    cov = np.cov(tx_n.T)
    # find eighenvalues and eighenvector
    ei_val, ei_vect = np.linalg.eig(cov)
    # Make list of tuples and sort in decreasing eighenvalue order
    ei_tuple = [(np.abs(ei_val[i]), ei_vect[:, i]) for i in range(len(ei_val))]
    ei_tuple.sort(key=lambda k: k[0], reverse=True)
    # Keep the eighenvectors corresponding to the K largest eighenvalues (TRADE-OFF TO BE MADE)
    ei_tuple_largest = ei_tuple[:k]
    # Construct a projection matrix W from the these eigenvectors
    w = np.stack([vec for val, vec in ei_tuple_largest], axis=1)

    return ei_tuple, ei_tuple_largest, w


def expand_without_pairwise_products(X, M):
    ans = np.ones((X.shape[0], 1))
    for idx in range(1, M+1):
        ans = np.hstack((ans, X**idx))
    return ans


def expand_with_pairwise_products(X, M):
    without_pairwise_products = expand_without_pairwise_products(X, M)
    # create the interactions between two variable
    # X is (N, d), we first make it as (N, d, 1) and (N, 1, d), then compute the interaction
    X_inter = np.expand_dims(X, axis=1)
    X_inter_ = np.expand_dims(X, axis=2)
    full_interactions = np.matmul(X_inter_, X_inter)
    # np.triu_indices: Return the indices for the upper-triangle of a matrix
    indices = np.triu_indices(full_interactions.shape[1], k=1)
    interactions = np.zeros((X.shape[0], len(indices[0])))
    for n in range(X.shape[0]):
        interactions[n] = full_interactions[n][indices]

    return np.concatenate((without_pairwise_products, interactions), axis=1)


def add_bias(X):
    X = np.append(X, np.ones(shape=(X.shape[0], 1)), axis=1)
    return (X)


def build_poly(x, degree):
    ones_col = np.ones((len(x), 1))
    poly = x
    m, n = x.shape
    for deg in range(2, degree+1):
        poly = np.c_[poly, np.power(x, deg)]
    multi_indices = {}
    cpt = 0
    for i in range(n):
        for j in range(i+1, n):
            multi_indices[cpt] = [i, j]
            cpt = cpt+1

    gen_features = np.zeros(shape=(m, len(multi_indices)))

    for i, c in multi_indices.items():
        gen_features[:, i] = np.multiply(x[:, c[0]], x[:, c[1]])

    poly = np.c_[poly, gen_features]
    poly = np.c_[ones_col, poly]

    return poly


def scale_transform(data_n, skewed):
    tx_n = data_n[0]
    # Scaling Data to apply Log function
    dividor = np.max(tx_n, axis=0)-np.min(tx_n, axis=0)
    tx_n = (tx_n - np.min(tx_n, axis=0))/dividor
    # Analyze skewed Data

    tx_n[:, skewed] = np.log(tx_n[:, skewed]+1)

    mean = np.mean(tx_n, axis=0)
    centered_data = tx_n - mean
    std = np.std(centered_data, axis=0)
    std_data = centered_data / std
    data_n = (std_data, data_n[1], data_n[2])
    parameters = (mean, std)
    return data_n, parameters


def process_data(path):
    # load the initial training set
    train_data = LoadTrainingDataset(path)
    # extract features, predictions and ids
    tx, y, ids = train_data.get_data()
    # separate data into 3 categories according to the PRI_JEST_NUM
    data_1, data_2, data_3 = separate_data(tx, y, ids)
    # remove column that contain only 1 data value (-999, 0 or 1 in our case)
    data_1, indexes1 = adapt_features(data_1)
    data_2, indexes2 = adapt_features(data_2)
    data_3, indexes3 = adapt_features(data_3)
    # replace -999 coefficients with the mediane of the column (-999 coefficients discared)
    data_1 = add_median(data_1)
    data_2 = add_median(data_2)
    data_3 = add_median(data_3)
    # dimentionality reduction : remove column that are strongly correlated
    data_1, indexes4 = dimensionality_reduction_corr(data_1)
    data_2, indexes5 = dimensionality_reduction_corr(data_2)
    data_3, indexes6 = dimensionality_reduction_corr(data_3)
    # Expanding features (adding artificial non linearity)

    # scaling and transforming data
    skewed1 = [2, 4, 6, 10, 15]
    skewed2 = [2, 3, 5, 7, 10, 13, 15]
    skewed3 = [1, 2, 3, 4, 7, 8, 11, 14, 17, 22]
    data_1, parameters1 = scale_transform(data_1, skewed1)
    data_2, parameters2 = scale_transform(data_2, skewed2)
    data_3, parameters3 = scale_transform(data_3, skewed3)
    tx_n = data_1[0]

    # for data in (data_1,data_2,data_3):
    #     fig=plt.figure(figsize=(40,100))
    #     for i in range(data[0].shape[1]):
    #         plt.subplot(data[0].shape[1],2,i+1)
    #         sns.distplot(data[0][:, i],ax=plt.gca(),hist=False)
    #         plt.subplots_adjust
    #     plt.show()

    # storing indexes of the columns to drop for the test data for each model
    indexes = (indexes1, indexes2, indexes3, indexes4, indexes5, indexes6)

    # storing means and std of each training set model
    parameters = (parameters1, parameters2, parameters3)
    return data_1, data_2, data_3, indexes, parameters


def process_test(path, indexes, parameters):
    # load the initial test set
    test_data = LoadTestingDataset(path)
    # extract features and ids
    tX_test, ids_test = test_data.get_data()
    # separate data into 3 categories according to the PRI_JEST_NUM
    y = np.ones((tX_test.shape[0], 1))
    data_1, data_2, data_3 = separate_data(tX_test, y, ids_test)
    # remove column that have been dropped during test phase
    xtest1 = data_1[0]
    xtest1 = np.delete(xtest1, indexes[0], 1)
    xtest2 = data_2[0]
    xtest2 = np.delete(xtest2, indexes[1], 1)
    xtest3 = data_3[0]
    xtest3 = np.delete(xtest3, indexes[2], 1)
    data_1 = (xtest1, data_1[1], data_1[2])
    data_2 = (xtest2, data_2[1], data_2[2])
    data_3 = (xtest3, data_3[1], data_3[2])
    data_1 = add_median(data_1)
    data_2 = add_median(data_2)
    data_3 = add_median(data_3)
    # dimentionality reduction : remove column that are strongly correlated
    xtest1 = data_1[0]
    xtest1 = np.delete(xtest1, indexes[3], 1)
    xtest2 = data_2[0]
    xtest2 = np.delete(xtest2, indexes[4], 1)
    xtest3 = data_3[0]
    xtest3 = np.delete(xtest3, indexes[5], 1)
    data_1 = (xtest1, data_1[1], data_1[2])
    data_2 = (xtest2, data_2[1], data_2[2])
    data_3 = (xtest3, data_3[1], data_3[2])
    # Expanding features (adding artificial non linearity)

    skewed1 = [2, 4, 6, 10, 15]
    skewed2 = [2, 3, 5, 7, 10, 13, 15]
    skewed3 = [1, 2, 3, 4, 7, 8, 11, 14, 17, 22]
    data_1, parameters1 = scale_transform(data_1, skewed1)
    data_2, parameters2 = scale_transform(data_2, skewed2)
    data_3, parameters3 = scale_transform(data_3, skewed3)

    return (data_1[0], data_1[2]), (data_2[0], data_2[2]), (data_3[0], data_3[2])
