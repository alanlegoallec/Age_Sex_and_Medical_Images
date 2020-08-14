import sys
from MI_Classes import PredictionsEids

# Options
# Only compute the results for the first 1000 eids
debug_mode = False

# Default parameters
if len(sys.argv) != 4:
    print('WRONG NUMBER OF INPUT PARAMETERS! RUNNING WITH DEFAULT SETTINGS!\n')
    sys.argv = ['']
    sys.argv.append('Age')  # target
    sys.argv.append('train')  # fold
    sys.argv.append('False')  # ensemble_models. Set False for MI03C and True for MI05B

# Compute results
Predictions_Eids = PredictionsEids(target=sys.argv[1], fold=sys.argv[2], ensemble_models=sys.argv[3],
                                   debug_mode=debug_mode)
Predictions_Eids.preprocessing()
Predictions_Eids.processing()
Predictions_Eids.postprocessing()
Predictions_Eids.save_predictions()

# Exit
print('Done.')
sys.exit(0)
