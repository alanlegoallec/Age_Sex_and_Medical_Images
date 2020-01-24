#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  8 18:59:15 2019

@author: Alan
"""

###LIBRARIES

#read and write
import os
import sys
import glob
import csv
import json
import pickle
import tarfile
import shutil
import pyreadr
import fnmatch

#maths
import numpy as np
import pandas as pd
import math
import random
from math import sqrt
from numpy.polynomial.polynomial import polyfit

#images
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import shift, rotate
from skimage.color import gray2rgb

#miscellaneous
import warnings
import multiprocessing as mp
from tqdm import tqdm_notebook as tqdm
import gc
import GPUtil
from datetime import datetime

#sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, log_loss, roc_auc_score, accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, precision_recall_curve, average_precision_score
from sklearn.utils import class_weight, resample

#tensorflow
import tensorflow as tf
from tensorflow import set_random_seed

#keras
import keras
from keras import backend as K
from keras_preprocessing.image import ImageDataGenerator
from keras.layers import Flatten, Dense, Activation, Input, Reshape, BatchNormalization, InputLayer, Dropout, Conv1D, Conv2D, MaxPooling1D, MaxPooling2D, Conv3D, MaxPooling3D, GlobalAveragePooling2D, LSTM
from keras.models import Sequential, Model, model_from_json, clone_model
from keras import regularizers, optimizers
from keras.optimizers import Adam, RMSprop, Adadelta
from keras.callbacks import Callback, EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, CSVLogger, TerminateOnNaN, TensorBoard


### PARAMETERS
names_model_parameters = ['target', 'organ', 'field_id', 'view', 'transformation', 'architecture', 'optimizer', 'learning_rate', 'weight_decay', 'dropout_rate']
dict_prediction_types={'Age':'regression', 'Sex':'binary'}
dict_losses_names={'regression':'MSE', 'binary':'Binary-Crossentropy', 'multiclass':'categorical_crossentropy'}
dict_main_metrics_names={'Age':'R-Squared', 'Sex':'ROC-AUC', 'imbalanced_binary_placeholder':'F1-Score'}
main_metrics_modes={'loss':'min', 'R-Squared':'max', 'ROC-AUC':'max'}
dict_metrics_names={'regression':['RMSE', 'R-Squared'], 'binary':['ROC-AUC', 'F1-Score', 'PR-AUC', 'Binary-Accuracy', 'Sensitivity', 'Specificity', 'Precision', 'Recall', 'True-Positives', 'False-Positives', 'False-Negatives', 'True-Negatives'], 'multiclass':['Categorical-Accuracy']}
dict_activations={'regression':'linear', 'binary':'sigmoid', 'multiclass':'softmax', 'saliency':'linear'}
folds = ['train', 'val', 'test']
folds_tune = ['train', 'val']
models_names = ['VGG16', 'VGG19', 'MobileNet', 'MobileNetV2', 'DenseNet121', 'DenseNet169', 'DenseNet201', 'NASNetMobile', 'NASNetLarge', 'Xception', 'InceptionV3', 'InceptionResNetV2']
images_sizes = ['224', '299', '331']
targets_regression = ['Age']
targets_binary = ['Sex']
image_quality_ids = {'Liver':'22414-2.0', 'Heart':None, 'PhysicalActivity':None}
id_sets = ['A', 'B']
dict_organ_to_idset={'PhysicalActivity':'A', 'Liver':'B', 'Heart':'B'}
metrics_needing_classpred = ['F1-Score', 'Binary-Accuracy', 'Precision', 'Recall']
metrics_displayed_in_int = ['True-Positives', 'True-Negatives', 'False-Positives', 'False-Negatives']
modes = ['', '_sd', '_str']

#define dictionary of batch sizes to fit as many samples as the model's architecture allows
dict_batch_sizes = dict.fromkeys(['NASNetMobile'], 128)
dict_batch_sizes.update(dict.fromkeys(['MobileNet', 'MobileNetV2'], 64))
dict_batch_sizes.update(dict.fromkeys(['InceptionV3', 'VGG16', 'VGG19', 'DenseNet121', 'DenseNet169'], 32))
dict_batch_sizes.update(dict.fromkeys(['DenseNet201', 'InceptionResNetV2', 'Xception'], 16))
dict_batch_sizes.update(dict.fromkeys(['NASNetLarge'], 4))

#define dictionaries to format the text
dict_folds_names={'train':'Training', 'val':'Validation', 'test':'Testing'}

#define dictionary to resize the images to the right size depending on the model
input_size_models = dict.fromkeys(['VGG16', 'VGG19', 'MobileNet', 'MobileNetV2', 'DenseNet121', 'DenseNet169', 'DenseNet201', 'NASNetMobile'], 224)
input_size_models.update(dict.fromkeys(['Xception', 'InceptionV3', 'InceptionResNetV2'], 299))
input_size_models.update(dict.fromkeys(['NASNetLarge'], 331))

#dictionary of dir_images used to generate the IDs split during preprocessing
dict_default_dir_images={}
dict_default_dir_images['Liver_20204'] = '../images/Liver/20204/main/raw/'
dict_default_dir_images['Heart_20208'] = '../images/Heart/20208/4chambers/raw/'
dict_default_dir_images['PhysicalActivity_90001'] = '../images/PhysicalActivity/90001/main/raw/'

#dict to choose the IDs mapping, depending on the UKB research proposal application that provided the data
dict_eids_version = dict.fromkeys(['PhysicalActivity'], 'A')
dict_eids_version.update(dict.fromkeys(['Liver', 'Heart'], 'B'))

#dict to decide which field is used to generate the ids when several organs/fields share the same ids (e.g Liver_20204 and Heart_20208)
dict_image_field_to_ids = dict.fromkeys(['PhysicalActivity_90001'], 'PhysicalActivity_90001')
dict_image_field_to_ids.update(dict.fromkeys(['Liver_20204', 'Heart_20208'], 'Liver_20204'))
dict_image_field_to_ids.update(dict.fromkeys(['Heart_20208'], 'Heart_20208'))

#dict to decide which field is used to generate the ids when several targets share the same ids (e.g Age and Sex)
dict_target_to_ids = dict.fromkeys(['Age', 'Sex'], 'Age')

#dict to decide in which order targets should be used when trying to transfer weight from a similar model
dict_alternative_targets_for_transfer_learning={'Age':['Age', 'Sex'], 'Sex':['Sex', 'Age']}


#define paths
if '/Users/Alan/' in os.getcwd():
    os.chdir('/Users/Alan/Desktop/Aging/Medical_Images/scripts/')
    path_store = '../data/'
    path_compute = '../data/'
else:
    os.chdir('/n/groups/patel/Alan/Aging/Medical_Images/scripts/')
    path_store = '../data/'
    path_compute = '/n/scratch2/al311/Aging/Medical_Images/data/'

#preprocessing
n_CV_outer_folds = 10
outer_folds = [str(x) for x in list(range(n_CV_outer_folds))]

#compiler
n_epochs_max = 1000

#postprocessing
boot_iterations=10000

#set parameters
seed=0
random.seed(seed)
set_random_seed(seed)

#postprocessing
n_bootstrap = 1000

#garbage collector
gc.enable()


### HELPER FUNCTIONS

def read_parameters_from_command(args):
    parameters={}
    parameters['target'] = args[1]
    parameters['image_type'] = args[2]
    parameters['transformation'] = args[3]
    parameters['architecture'] = args[4]
    parameters['optimizer'] = args[5]
    parameters['learning_rate'] = args[6]
    parameters['weight_decay'] = args[7]
    parameters['dropout_rate'] = args[8]
    if len(args) > 9:
        parameters['outer_fold'] = args[9]
    else:
        parameters['outer_fold'] = None
    parameters['organ'], parameters['field_id'], parameters['view'] = parameters['image_type'].split('_')
    #convert parameters to float if a specific value other than 'all' was selected
    for parameter_name in ['learning_rate', 'weight_decay', 'dropout_rate']:
        if(parameters[parameter_name] != '*'):
            parameters[parameter_name] = float(parameters[parameter_name])
    return parameters['target'], parameters['image_type'], parameters['organ'], parameters['field_id'], parameters['view'], parameters['transformation'], parameters['architecture'], parameters['optimizer'], parameters['learning_rate'], parameters['weight_decay'], parameters['dropout_rate'], parameters['outer_fold']

def version_to_parameters(model_name, names_model_parameters):
    parameters={}
    parameters_list = model_name.split('_')
    for i, parameter in enumerate(names_model_parameters):
        parameters[parameter] = parameters_list[i]
    if len(parameters_list) > 10:
        parameters['outer_fold'] = parameters_list[10]
    return parameters

def parameters_to_version(parameters):
    return '_'.join(parameters.values())


def configure_gpus():
   print('tensorflow version : ', tf.__version__)
   print('Build with Cuda : ', tf.test.is_built_with_cuda())
   print('Gpu available : ', tf.test.is_gpu_available())
   #print('Available ressources : ', tf.config.experimental.list_physical_devices())
   #device_count = {'GPU': 1, 'CPU': mp.cpu_count() },log_device_placement =  True)
   config = tf.ConfigProto()
   config.gpu_options.allow_growth = True
   sess= tf.Session(config = config)
   K.set_session(session= sess)
   K.tensorflow_backend._get_available_gpus()
   warnings.filterwarnings('ignore') 

def append_ext(fn):
    return fn+".jpg"

def load_data_features(path_store, image_field, target, folds, outer_fold):
    DATA_FEATURES = {}
    for fold in folds:
        DATA_FEATURES[fold] = pd.read_csv(path_store + 'data-features_' + image_field + '_' + target + '_' + fold + '_' + outer_fold + '.csv')
    return DATA_FEATURES

def generate_data_features(image_field, organ, target, dir_images, image_quality_id):
    DATA_FEATURES = {}
    if image_quality_id == None:
        # load the selected features
        if organ in ["PhysicalActivity"]: #different set of eids
            data_features = pd.read_csv("/n/groups/patel/uk_biobank/main_data_9512/data_features.csv")[['f.eid', 'f.31.0.0', 'f.21003.0.0']]
            data_features.replace({'f.31.0.0': {'Male': 0, 'Female': 1}}, inplace=True)
        else:
            data_features = pd.read_csv('/n/groups/patel/uk_biobank/main_data_52887/ukb37397.csv', usecols=['eid', '31-0.0', '21003-0.0'])
        data_features.columns = ['eid', 'Sex', 'Age']
        data_features['eid'] = data_features['eid'].astype(str)
        data_features['eid'] = data_features['eid'].apply(append_ext)
        data_features = data_features.set_index('eid', drop=False)
    else:
        # load the selected features
        if organ in ["PhysicalActivity"]: #different set of eids
            print("TODO")
            sys.exit()
        else:
            data_features = pd.read_csv('/n/groups/patel/uk_biobank/main_data_52887/ukb37397.csv', usecols=['eid', '31-0.0', '21003-0.0', image_quality_id])
        data_features.columns = ['eid', 'Sex', 'Age', 'Data_quality']
        data_features['eid'] = data_features['eid'].astype(str)
        data_features['eid'] = data_features['eid'].apply(append_ext)
        data_features = data_features.set_index('eid', drop=False)
        # remove the samples for which the image data is low quality
        data_features = data_features[data_features['Data_quality'] != np.nan]
        data_features = data_features.drop('Data_quality', axis=1)
    # get rid of samples with NAs
    data_features = data_features.dropna()
    # list the samples' ids for which liver images are available
    all_files = os.listdir(dir_images)
    data_features = data_features.loc[all_files]
    #files = data_features.index.values
    ids = data_features.index.values.copy()
    np.random.shuffle(ids)
    #distribute the ids between the different outer and inner folds
    n_samples = len(ids)
    n_samples_by_fold = n_samples/n_CV_outer_folds
    FOLDS_IDS = {}
    for outer_fold in outer_folds:
        FOLDS_IDS[outer_fold] = np.ndarray.tolist(ids[int((int(outer_fold))*n_samples_by_fold):int((int(outer_fold)+1)*n_samples_by_fold)])
    TRAINING_IDS={}
    VALIDATION_IDS={}
    TEST_IDS={}
    for i in outer_folds:
        TRAINING_IDS[i] = []
        VALIDATION_IDS[i] = []
        TEST_IDS[i] = []
        for j in outer_folds:
            if (j == i):
                VALIDATION_IDS[i].extend(FOLDS_IDS[j])
            elif (int(j) == ((int(i)+1)%n_CV_outer_folds)):
                TEST_IDS[i].extend(FOLDS_IDS[j])
            else:
                TRAINING_IDS[i].extend(FOLDS_IDS[j])
    IDS = {'train':TRAINING_IDS, 'val':VALIDATION_IDS, 'test':TEST_IDS}
    #generate inner fold split for each outer fold
    for outer_fold in outer_folds:
        print(outer_fold)
        # compute values for scaling of regression targets
        if target in targets_regression:
            idx = np.where(np.isin(data_features.index.values, TRAINING_IDS[outer_fold]))[0]
            data_features_train = data_features.iloc[idx, :]
            target_mean = data_features_train[target].mean()
            target_std = data_features_train[target].std()
        #generate folds
        indices = {}
        for fold in folds:
            indices[fold] = np.where(np.isin(data_features.index.values, IDS[fold][outer_fold]))[0]
            data_features_fold = data_features.iloc[indices[fold], :]
            data_features_fold['outer_fold'] = outer_fold
            data_features_fold = data_features_fold[['eid', 'outer_fold', 'Sex', 'Age']]
            if target in targets_regression:
                data_features_fold[target + '_raw'] = data_features_fold[target]
                data_features_fold[target] = (data_features_fold[target] - target_mean) / target_std
            DATA_FEATURES[fold] = data_features_fold
            data_features_fold.to_csv(path_store + 'data-features_' + image_field + '_' + target + '_' + fold + '_' + outer_fold + '.csv', index=False)
    return DATA_FEATURES

def take_subset_data_features(DATA_FEATURES, batch_size, fraction=0.1):
    for fold in DATA_FEATURES.keys():
        DATA_FEATURES[fold] = DATA_FEATURES[fold].iloc[:(batch_size*int(len(DATA_FEATURES[fold].index)/batch_size*fraction)), :]
    return DATA_FEATURES

def generate_class_weights(data_features, target):
    class_weights = None
    if dict_prediction_types[target] == 'binary':
        class_weights={}
        counts = data_features[target].value_counts()
        for i in counts.index.values:
            class_weights[i] = 1/counts.loc[i]
    return class_weights

def generate_generators(DATA_FEATURES, target, dir_images, image_size, batch_size, folds, seed, mode):
    GENERATORS = {}
    STEP_SIZES = {}
    for fold in folds:
        if fold == 'train':
            datagen = ImageDataGenerator(rescale=1./255., rotation_range=20, width_shift_range=0.2, height_shift_range=0.2)
            shuffle = True if mode == 'model_training' else False
        else:
            datagen = ImageDataGenerator(rescale=1./255.)
            shuffle = False
        
        #define batch size for testing: data is split between a part that fits in batches, and leftovers
        batch_size_fold = min(batch_size, len(DATA_FEATURES[fold].index)) if mode == 'model_testing' else batch_size
        
        # define data generator
        generator_fold = datagen.flow_from_dataframe(
            dataframe=DATA_FEATURES[fold],
            directory=dir_images,
            x_col='eid',
            y_col=target,
            color_mode='rgb',
            batch_size= batch_size_fold,
            seed=seed,
            shuffle=shuffle,
            class_mode='raw',
            target_size=(image_size, image_size))
        
        # assign variables to their names
        GENERATORS[fold] = generator_fold
        STEP_SIZES[fold] = generator_fold.n//generator_fold.batch_size
    return GENERATORS, STEP_SIZES

def generate_base_model(architecture, weight_decay, dropout_rate, keras_weights):
    if architecture in ['VGG16', 'VGG19']:
        if architecture == 'VGG16':
            from keras.applications.vgg16 import VGG16
            base_model = VGG16(include_top=False, weights=keras_weights, input_shape=(224,224,3))
        elif architecture == 'VGG19':
            from keras.applications.vgg19 import VGG19
            base_model = VGG19(include_top=False, weights=keras_weights, input_shape=(224,224,3))
        x = base_model.output
        x = Flatten()(x)
        x = Dense(4096, activation='relu', kernel_regularizer=regularizers.l2(weight_decay))(x)
        x = Dropout(dropout_rate)(x)
        x = Dense(4096, activation='relu', kernel_regularizer=regularizers.l2(weight_decay))(x)
        x = Dropout(dropout_rate)(x) 
    elif architecture in ['MobileNet', 'MobileNetV2']:
        if architecture == 'MobileNet':
            from keras.applications.mobilenet import MobileNet
            base_model = MobileNet(include_top=False, weights=keras_weights, input_shape=(224,224,3))
        elif architecture == 'MobileNetV2':
            from keras.applications.mobilenet_v2 import MobileNetV2
            base_model = MobileNetV2(include_top=False, weights=keras_weights, input_shape=(224,224,3))
        x = base_model.output
        x = GlobalAveragePooling2D()(x)
    elif architecture in ['DenseNet121', 'DenseNet169', 'DenseNet201']:
        if architecture == 'DenseNet121':
            from keras.applications.densenet import DenseNet121
            base_model = DenseNet121(include_top=True, weights=keras_weights, input_shape=(224,224,3))
        elif architecture == 'DenseNet169':
            from keras.applications.densenet import DenseNet169
            base_model = DenseNet169(include_top=True, weights=keras_weights, input_shape=(224,224,3))
        elif architecture == 'DenseNet201':
            from keras.applications.densenet import DenseNet201
            base_model = DenseNet201(include_top=True, weights=keras_weights, input_shape=(224,224,3))            
        base_model = Model(base_model.inputs, base_model.layers[-2].output)
        x = base_model.output
    elif architecture in ['NASNetMobile', 'NASNetLarge']:
        if architecture == 'NASNetMobile':
            from keras.applications.nasnet import NASNetMobile
            base_model = NASNetMobile(include_top=True, weights=keras_weights, input_shape=(224,224,3))
        elif architecture == 'NASNetLarge':
            from keras.applications.nasnet import NASNetLarge
            base_model = NASNetLarge(include_top=True, weights=keras_weights, input_shape=(331,331,3))
        base_model = Model(base_model.inputs, base_model.layers[-2].output)
        x = base_model.output
    elif architecture == 'Xception':
        from keras.applications.xception import Xception
        base_model = Xception(include_top=False, weights=keras_weights, input_shape=(299,299,3))
        x = base_model.output
        x = GlobalAveragePooling2D()(x)
    elif architecture == 'InceptionV3':
        from keras.applications.inception_v3 import InceptionV3
        base_model = InceptionV3(include_top=False, weights=keras_weights, input_shape=(299,299,3))
        x = base_model.output        
        x = GlobalAveragePooling2D()(x)
    elif architecture == 'InceptionResNetV2':
        from keras.applications.inception_resnet_v2 import InceptionResNetV2
        base_model = InceptionResNetV2(include_top=False, weights=keras_weights, input_shape=(299,299,3))
        x = base_model.output        
        x = GlobalAveragePooling2D()(x)
    return x, base_model.input

def complete_architecture(x, input_shape, activation, weight_decay, dropout_rate):
    x = Dense(1024, activation='selu', kernel_regularizer=regularizers.l2(weight_decay))(x)
    x = Dropout(dropout_rate)(x)
    x = Dense(512, activation='selu', kernel_regularizer=regularizers.l2(weight_decay))(x)
    x = Dropout(dropout_rate)(x)
    x = Dense(256, activation='selu', kernel_regularizer=regularizers.l2(weight_decay))(x)
    x = Dropout(dropout_rate)(x)
    x = Dense(128, activation='selu', kernel_regularizer=regularizers.l2(weight_decay))(x)
    x = Dropout(dropout_rate)(x)
    x = Dense(64, activation='selu', kernel_regularizer=regularizers.l2(weight_decay))(x)
    x = Dropout(dropout_rate)(x)
    predictions = Dense(1, activation=activation)(x)
    model = Model(inputs=input_shape, outputs=predictions)
    return model

"""Find the most similar model for transfer learning.
The function returns path_load_weights, keras_weights """
def weights_for_transfer_learning(continue_training, max_transfer_learning, path_weights, list_parameters_to_match):
    
    print('Looking for models to transfer weights from...')
    
    #define parameters
    version = path_weights.replace('../data/model-weights_', '').replace('.h5', '')
    parameters = version_to_parameters(version, names_model_parameters)
    
    #continue training if possible
    if continue_training and os.path.exists(path_weights):
        print('Loading the weights from the model\'s previous training iteration.')
        return path_weights, None
    
    #Look for similar models, starting from very similar to less similar
    if max_transfer_learning:
        while(True):  
            #print('Matching models for the following criterias:'); print(['architecture', 'target'] + list_parameters_to_match)
            #start by looking for models trained on the same target, then move to other targets
            for target_to_load in dict_alternative_targets_for_transfer_learning[parameters['target']]:
                #print('Target used: ' + target_to_load)
                parameters_to_match = parameters.copy()
                parameters_to_match['target'] = target_to_load
                #load the ranked performances table to select the best performing model among the similar models available
                path_performances_to_load = path_store + 'PERFORMANCES_ranked_' + parameters_to_match['target'] + '_' + 'val' + '_' + dict_eids_version[parameters['organ']] + '.csv'
                try:
                    Performances = pd.read_csv(path_performances_to_load)
                    Performances['field_id'] = Performances['field_id'].astype(str)
                except:
                    #print("Could not load the file: " + path_performances_to_load)
                    break
                #iteratively get rid of models that are not similar enough, based on the list
                for parameter in ['architecture', 'target'] + list_parameters_to_match:
                    Performances = Performances[Performances[parameter] == parameters_to_match[parameter]]
                #if at least one model is similar enough, load weights from the best of them
                if(len(Performances.index) != 0):
                    path_weights_to_load = path_store + 'model-weights_' + Performances['version'][0] + '.h5'
                    print('transfering the weights from: ' + path_weights_to_load)
                    return path_weights_to_load, None
            
            #if no similar model was found, try again after getting rid of the last selection criteria
            if(len(list_parameters_to_match) == 0):
                print('No model found for transfer learning.')
                break
            list_parameters_to_match.pop()
    
    #Otherwise use imagenet weights to initialize
    print('Using imagenet weights.')
    return 'load_path_weights_should_not_be_used', 'imagenet'

class myModelCheckpoint(ModelCheckpoint):
    """Take as input baseline instead of np.Inf, useful if model has already been trained.
    """
    def __init__(self, filepath, monitor='val_loss', baseline=np.Inf, verbose=0,
                 save_best_only=False, save_weights_only=False,
                 mode='auto', period=1):
        super(ModelCheckpoint, self).__init__()
        self.monitor = monitor
        self.verbose = verbose
        self.filepath = filepath
        self.save_best_only = save_best_only
        self.save_weights_only = save_weights_only
        self.period = period
        self.epochs_since_last_save = 0
        
        if mode not in ['auto', 'min', 'max']:
            warnings.warn('ModelCheckpoint mode %s is unknown, '
                          'fallback to auto mode.' % (mode),
                          RuntimeWarning)
            mode = 'auto'
        
        if mode == 'min':
            self.monitor_op = np.less
            self.best = baseline
        elif mode == 'max':
            self.monitor_op = np.greater
            self.best = baseline
        else:
            if 'acc' in self.monitor or self.monitor.startswith('fmeasure'):
                self.monitor_op = np.greater
                self.best = -np.Inf
            else:
                self.monitor_op = np.less
                self.best = baseline

#model_checkpoint_backup is used in case the weights file gets corrupted because the job gets killed during its writing
def define_callbacks(path_store, version, baseline, continue_training, main_metric, main_metric_mode):
    csv_logger = CSVLogger(path_store + 'logger_' + version + '.csv', separator=',', append=continue_training)
    model_checkpoint_backup = myModelCheckpoint(path_store + 'backup-model-weights_' + version + '.h5', monitor='val_' + main_metric.__name__, baseline=baseline, verbose=1, save_best_only=True, save_weights_only=True, mode=main_metric_mode, period=1)
    model_checkpoint = myModelCheckpoint(path_store + 'model-weights_' + version + '.h5', monitor='val_' + main_metric.__name__, baseline=baseline, verbose=1, save_best_only=True, save_weights_only=True, mode=main_metric_mode, period=1)
    reduce_lr_on_plateau = ReduceLROnPlateau(monitor='loss', factor=0.5, patience=2, verbose=1, mode='min', min_delta=0, cooldown=0, min_lr=0)
    early_stopping = EarlyStopping(monitor= 'val_' + main_metric.__name__, min_delta=0, patience=5, verbose=0, mode=main_metric_mode, baseline=None, restore_best_weights=False)
    return [csv_logger, model_checkpoint_backup, model_checkpoint, reduce_lr_on_plateau, early_stopping]

def R2_K(y_true, y_pred):
    SS_res =  K.sum(K.square( y_true-y_pred )) 
    SS_tot = K.sum(K.square( y_true - K.mean(y_true) ) ) 
    return ( 1 - SS_res/(SS_tot + K.epsilon()) )

def RMSE_K(y_true, y_pred):
    return K.sqrt(K.mean(K.square(y_pred - y_true)))

def sensitivity_K(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    return true_positives / (possible_positives + K.epsilon())

def specificity_K(y_true, y_pred):
    true_negatives = K.sum(K.round(K.clip((1-y_true) * (1-y_pred), 0, 1)))
    possible_negatives = K.sum(K.round(K.clip(1-y_true, 0, 1)))
    return true_negatives / (possible_negatives + K.epsilon())

def ROC_AUC_K(y_true, y_pred):
    auc = tf.metrics.auc(y_true, y_pred, curve='ROC')[1]
    K.get_session().run(tf.local_variables_initializer())
    return auc

def recall_K(y_true, y_pred):
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
        recall = true_positives / (possible_positives + K.epsilon())
        return recall

def precision_K(y_true, y_pred):
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
        precision = true_positives / (predicted_positives + K.epsilon())
        return precision

def PR_AUC_K(y_true, y_pred):
    auc = tf.metrics.auc(y_true, y_pred, curve='PR', summation_method='careful_interpolation')[1]
    K.get_session().run(tf.local_variables_initializer())
    return auc

def F1_K(y_true, y_pred):
    precision = precision_K(y_true, y_pred)
    recall = recall_K(y_true, y_pred)
    return 2*((precision*recall)/(precision+recall+K.epsilon()))

def true_positives_K(y_true, y_pred):
    return K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))

def false_positives_K(y_true, y_pred):
    return K.sum(K.round(K.clip((1 - y_true) * y_pred, 0, 1)))

def false_negatives_K(y_true, y_pred):
    return K.sum(K.round(K.clip(y_true * (1-y_pred), 0, 1)))

def true_negatives_K(y_true, y_pred):
    return K.sum(K.round(K.clip((1-y_true) * (1-y_pred), 0, 1)))

def rmse(y_true, y_pred):
    return sqrt(mean_squared_error(y_true, y_pred))

def sensitivity_score(y, pred):
    _, _, fn, tp = confusion_matrix(y, pred.round()).ravel()
    return tp/(tp+fn)

def specificity_score(y, pred):
    tn, fp, _, _ = confusion_matrix(y, pred.round()).ravel()
    return tn/(tn+fp)

def true_positives_score(y, pred):
    _, _, _, tp = confusion_matrix(y, pred.round()).ravel()
    return tp

def false_positives_score(y, pred):
    _, fp, _, _ = confusion_matrix(y, pred.round()).ravel()
    return fp

def false_negatives_score(y, pred):
    _, _, fn, _ = confusion_matrix(y, pred.round()).ravel()
    return fn

def true_negatives_score(y, pred):
    tn, _, _, _ = confusion_matrix(y, pred.round()).ravel()
    return tn

def bootstrap(data, n_bootstrap, function):
    results = []
    for i in range(n_bootstrap):
        data_i = resample(data, replace=True, n_samples=len(data.index))
        results.append(function(data_i['y'], data_i['pred']))
    return np.mean(results), np.std(results)

def set_learning_rate(model, optimizer, learning_rate, loss, metrics):
    opt = globals()[optimizer](lr=learning_rate, clipnorm=1.0)
    model.compile(optimizer=opt, loss=loss, metrics=metrics)

def save_model_weights(model, path_store, version):
    model.save_weights(path_store + "model_weights_" + version + ".h5")
    print("Model's best weights for "+ version + " were saved.")

def plot_training(path_store, version, display_learning_rate):
    try:
        logger = pd.read_csv(path_store + 'logger_' + version + '.csv')
    except:
        print('ERROR: THE FILE logger_' + version + '.csv' ' WAS NOT FOUND OR WAS EMPTY/CORRUPTED. SKIPPING PLOTTING OF THE TRAINING FOR THIS MODEL.')
        return
    #Amend column names for consistency
    logger.columns = [name[:-2] if name.endswith('_K') else name for name in logger.columns]
    metrics_names = [metric[4:] for metric in logger.columns.values if metric.startswith('val_')]
    logger.columns = ['train_' + name if name in metrics_names else name for name in logger.columns]
    #rewrite epochs numbers based on nrows, because several loggers might have been appended if the model has been retrained.
    logger['epoch'] = [i+1 for i in range(len(logger.index))]
    #multiplot layout
    n_rows=3
    n_metrics = len(metrics_names)
    fig, axs = plt.subplots(math.ceil(n_metrics/n_rows), min(n_metrics,n_rows), sharey=False, sharex=True, squeeze=False)
    fig.set_figwidth(5*n_metrics)
    fig.set_figheight(5)

    #plot evolution of each metric during training, train and val values
    for k, metric in enumerate(metrics_names):
        i=int(k/n_rows)
        j=k%n_rows
        for fold in folds_tune:
            axs[i,j].plot(logger['epoch'], logger[fold + '_' + metric])
        axs[i,j].legend(['Training', 'Validation'], loc='upper left')
        axs[i,j].set_title(metric + ' = f(Epoch)')
        axs[i,j].set_xlabel('Epoch')
        axs[i,j].set_ylabel(metric)
        if metric not in ['true_positives', 'false_positives', 'false_negatives', 'true_negatives']:
            axs[i,j].set_ylim((-0.2, 1.1))
        #use second axis for learning rate
        if display_learning_rate & ('lr' in logger.columns):
            ax2 = axs[i,j].twinx()
            ax2.plot(logger['epoch'], logger['lr'], color='green')
            ax2.tick_params(axis='y', labelcolor='green')
            ax2.legend(['Learning Rate'], loc='upper right')
    fig.tight_layout()
    #save figure as pdf before closing
    fig.savefig("../figures/Training_" + version + '.pdf', bbox_inches='tight')
    plt.close('all')

def build_ensemble_model(Performances_subset, Predictions, y, main_metric_function, main_metric_mode):
    best_perf = -np.Inf if main_metric_mode == 'max' else np.Inf
    ENSEMBLE_COLS={'select':[], 'all':[]}
    #iteratively add models to the ensemble
    for i, version in enumerate(Performances_subset['version']):
        #added_pred_name = 'Pred_' + version
        #TODO remove below keep above
        added_pred_name = 'Pred_' + version.replace('_str.csv','')
        for ensemble_type in ENSEMBLE_COLS.keys():
            #print(ensemble_type)
            ENSEMBLE_COLS[ensemble_type].append(added_pred_name)
            Ensemble_predictions = Predictions[ENSEMBLE_COLS[ensemble_type]].mean(axis=1)
            df_ensemble = pd.concat([y, Ensemble_predictions], axis=1).dropna()
            df_ensemble.columns = ['y', 'pred']
            #evaluate the ensemble predictions
            new_perf = main_metric_function(df_ensemble['y'],df_ensemble['pred'])
            if new_perf > best_perf:
                #print('BETTER! ')
                best_perf = new_perf
                best_pred = df_ensemble['pred']
                best_ensemble_namecols = ENSEMBLE_COLS[ensemble_type].copy()
                #print('New best performance = ' + str(round(best_perf, 4)) + ', using the ensemble type: ' + ensemble_type)
            elif ensemble_type == 'select':
                #print('The new ensemble did not perform as well: ' + str(round(new_perf, 4)))
                ENSEMBLE_COLS[ensemble_type].pop()
    return best_ensemble_namecols

#returns True if the dataframe is a single column duplicated. Used to check if the folds are the same for the entire ensemble model
def is_rank_one(df):
    for i in range(len(df.columns)):
        for j in range(i+1,len(df.columns)):
            if not df.iloc[:,i].equals(df.iloc[:,j]):
                return False
    return True 

def update_predictions_with_ensemble(PREDICTIONS, version, id_set, folds, Performances_subset, Predictions, y, main_metric_function, main_metric_mode):
    best_ensemble_namecols = build_ensemble_model(Performances_subset, Predictions, y, main_metric_function, main_metric_mode)
    best_ensemble_outerfolds = [model_name.replace('Pred_', 'outer_fold_') for model_name in best_ensemble_namecols]
    Ensemble_predictions = Predictions[best_ensemble_namecols].mean(axis=1)
    Ensemble_outerfolds = Predictions[best_ensemble_outerfolds]
    for fold in folds:
        PREDICTIONS[id_set][fold]['Ensemble_Pred_' + version] = Ensemble_predictions
        if is_rank_one(Ensemble_outerfolds):
            print('The folds were shared by all the models in the ensemble models. Saving the folds too.')
            PREDICTIONS[id_set][fold]['Ensemble_outer_fold_' + version] = Ensemble_outerfolds.mean(axis=1)
            print(PREDICTIONS[id_set][fold]['Ensemble_outer_fold_' + version])
        else:
            PREDICTIONS[id_set][fold]['Ensemble_outer_fold_' + version] = np.nan    


### PARAMETERS THAT DEPEND ON FUNCTIONS

#dict of Keras and sklearn losses and metrics
dict_metrics={}
dict_metrics['MSE']={'Keras':'mean_squared_error', 'sklearn':mean_squared_error}
dict_metrics['RMSE']={'Keras':RMSE_K, 'sklearn':rmse}
dict_metrics['R-Squared']={'Keras':R2_K, 'sklearn':r2_score}
dict_metrics['Binary-Crossentropy']={'Keras':'binary_crossentropy', 'sklearn':log_loss}
dict_metrics['ROC-AUC']={'Keras':ROC_AUC_K, 'sklearn':roc_auc_score}
dict_metrics['F1-Score']={'Keras':F1_K, 'sklearn':f1_score}
dict_metrics['PR-AUC']={'Keras':PR_AUC_K, 'sklearn':average_precision_score}
dict_metrics['Binary-Accuracy']={'Keras':'binary_accuracy', 'sklearn':accuracy_score}
dict_metrics['Sensitivity']={'Keras':sensitivity_K, 'sklearn':sensitivity_score}
dict_metrics['Specificity']={'Keras':specificity_K, 'sklearn':specificity_score}
dict_metrics['Precision']={'Keras':precision_K, 'sklearn':precision_score}
dict_metrics['Recall']={'Keras':recall_K, 'sklearn':recall_score}
dict_metrics['True-Positives']={'Keras':true_positives_K, 'sklearn':true_positives_score}
dict_metrics['False-Positives']={'Keras':false_positives_K, 'sklearn':false_positives_score}
dict_metrics['False-Negatives']={'Keras':false_negatives_K, 'sklearn':false_negatives_score}
dict_metrics['True-Negatives']={'Keras':true_negatives_K, 'sklearn':true_negatives_score}

