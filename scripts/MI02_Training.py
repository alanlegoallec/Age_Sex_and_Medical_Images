#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 00:07:03 2019

@author: Alan
"""

#load libraries, import functions and import parameters (nested import in the line below)
from MI_helpers import *

#options
#load weights from previous best training results, VS. start from scratch
continue_training = True
#try to find a similar model among those already trained and evaluated to perform transfer learning
max_transfer_learning = False
#use a small subset of the data VS. run the actual full data pipeline to get accurate results
debunk_mode = False
#compute the metrics during training on the train and val sets VS. only compute loss (faster)
display_full_metrics = False

#default parameters
if len(sys.argv) != 10:
    print('WRONG NUMBER OF INPUT PARAMETERS! RUNNING WITH DEFAULT SETTINGS!\n')
    sys.argv = ['']
    sys.argv.append('Age') #target
    sys.argv.append('Heart_20208_3chambers') #image_type, e.g PhysicalActivity_90001_main, Liver_20204_main or Heart_20208_3chambers
    sys.argv.append('raw') #transformation
    sys.argv.append('InceptionResNetV2') #architecture
    sys.argv.append('Adam') #optimizer
    sys.argv.append('0.001') #learning_rate
    sys.argv.append('0.0') #weight decay
    sys.argv.append('0.0') #dropout
    sys.argv.append('1') #outer_fold

#read parameters from command
target, image_type, organ, field_id, view, transformation, architecture, optimizer, learning_rate, weight_decay, dropout_rate, outer_fold, id_set = read_parameters_from_command(sys.argv)

#set other parameters accordingly
functions_version = 'Keras' #use 'Keras' for functions during training, and 'sklearn' for functions during testing
version = target + '_' + image_type + '_' + transformation + '_' + architecture + '_' + optimizer + '_' + np.format_float_positional(learning_rate) + '_' + str(weight_decay) + '_' + str(dropout_rate) + '_' + str(outer_fold)
dir_images = '../images/' + organ + '/' + field_id + '/' + view + '/' + transformation + '/'
image_size = input_size_models[architecture]
batch_size = dict_batch_sizes[architecture]
prediction_type = dict_prediction_types[target]
loss_name = dict_losses_names[prediction_type]
loss_function = dict_metrics[loss_name][functions_version]
main_metric_name = dict_main_metrics_names[target]
main_metric_mode = main_metrics_modes[main_metric_name]
main_metric = dict_metrics[main_metric_name][functions_version]
metrics_names = dict_metrics_names[prediction_type] if display_full_metrics else [main_metric_name]
metrics = [dict_metrics[metric_name][functions_version] for metric_name in metrics_names]

#Determine which weights to load, if any.
path_weights = path_store + 'model-weights_' + version + '.h5'
path_load_weights, keras_weights= weights_for_transfer_learning(continue_training=continue_training, max_transfer_learning=max_transfer_learning, path_weights=path_weights, list_parameters_to_match = ['organ', 'transformation', 'field_id', 'view'])

#double the batch size for the teslaM40 cores that have bigger memory
GPUs = GPUtil.getGPUs()
if GPUs[0].memoryTotal > 20000:
    batch_size = batch_size*2

#configure cpus and gpus
n_cpus = len(os.sched_getaffinity(0))
gpu_session = configure_gpus()

#generate data_features
DATA_FEATURES = load_data_features(folds=folds_tune, path_store=path_store, image_field=dict_image_field_to_ids[organ + '_' + field_id], target=dict_target_to_ids[target], outer_fold=outer_fold)

if debunk_mode:
    DATA_FEATURES = take_subset_data_features(DATA_FEATURES=DATA_FEATURES, batch_size=batch_size, fraction=0.1)

#generate the class weights for the training set
class_weights = generate_class_weights(data_features=DATA_FEATURES['train'], target=target)

#generate the data generators
GENERATORS, STEP_SIZES = generate_generators(DATA_FEATURES=DATA_FEATURES, target=target, dir_images=dir_images, image_size=image_size, batch_size=batch_size, folds=folds_tune, seed=seed, mode='model_training')

#define the model
"""
cnn_input, cnn_output = generate_cnn(architecture=architecture, weight_decay=weight_decay, dropout_rate=dropout_rate, keras_weights=keras_weights)
side_nn_input, side_nn_output = generate_side_nn(dim):
model = complete_architecture(cnn_input=cnn_input, cnn_output=cnn_output, scalar_predictors =, activation=dict_activations[prediction_type], weight_decay=weight_decay, dropout_rate=dropout_rate)
"""
x, base_model_input = generate_base_model(architecture=architecture, weight_decay=weight_decay, dropout_rate=dropout_rate, keras_weights=keras_weights)
model = complete_architecture(x=x, input_shape=base_model_input, activation=dict_activations[prediction_type], weight_decay=weight_decay, dropout_rate=dropout_rate)

#(re-)set the learning rate
set_learning_rate(model=model, optimizer=optimizer, learning_rate=learning_rate, loss=loss_function, metrics=metrics)

"""
#load weights to continue training
if keras_weights == None:
    try:
        model.load_weights(path_load_weights)
    except:
        #load backup weights if the main weights are corrupted
        model.load_weights(path_load_weights.replace('model-weights', 'backup-model-weights'))
else:
    #save imagenet weights as baseline in case no better weights can be found before convergence
    model.save_weights(path_weights.replace('model-weights', 'backup-model-weights'))
    model.save_weights(path_weights)
"""
#load weights to continue training
try:
    model.load_weights(path_load_weights)
except:
    #load backup weights if the main weights are corrupted
    try:
        model.load_weights(path_load_weights.replace('model-weights', 'backup-model-weights'))
    except:
        try:
            model.load_weights('../data_WrongAge/model-weights_' + target + '_' + image_type + '_' + transformation + '_' + architecture + '_' + optimizer + '_' + str(0.0001) + '_' + str(weight_decay) + '_' + str(dropout_rate) + '_' + str(outer_fold) + '.h5')
        except:
            model.load_weights(('../data_WrongAge/model-weights_' + target + '_' + image_type + '_' + transformation + '_' + architecture + '_' + optimizer + '_' + str(0.0001) + '_' + str(weight_decay) + '_' + str(dropout_rate) + '_' + str(outer_fold) + '.h5').replace('model-weights', 'backup-model-weights'))
        model.save_weights(path_weights)

#calculate initial val_loss value
if continue_training:
    baseline = model.evaluate_generator(GENERATORS['val'], steps=GENERATORS['val'].n//GENERATORS['val'].batch_size)[([loss_name] + metrics_names).index(main_metric_name)]
elif main_metric_mode == 'min':
    baseline = np.Inf
elif main_metric_mode == 'max':
    baseline = -np.Inf
print('Baseline validation performance is: ' + str(baseline))

#define callbacks
callbacks = define_callbacks(path_store=path_store, version=version, baseline=baseline, continue_training=continue_training, main_metric=main_metric, main_metric_mode=main_metric_mode)

#garbage collector
gc.collect()

#train the model
model.fit_generator(generator=GENERATORS['train'], steps_per_epoch=STEP_SIZES['train'], validation_data=GENERATORS['val'], validation_steps=STEP_SIZES['val'], use_multiprocessing = True, workers=n_cpus, epochs=n_epochs_max, class_weight=class_weights, callbacks=callbacks, verbose=2)

#exit
print('\nTHE MODEL CONVERGED!\n')
gpu_session.close()
sys.exit(0)

