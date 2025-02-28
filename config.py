# NOTE: The containing directory of this file must be in PYTHONPATH.

# `root` must be an absolute path
# `root` will be overriden by Dockerfile
root = '/home/bettscheider/SystemLevelSymbolicGrammarMining/klee-examples-programs'

###############################################
################# Evaluation ##################
###############################################

max_depths = [10]
cnt_inputs = 1000

###############################################
############ Token Generalization #############
###############################################

THRESHOLD_GENERALIZATION = 3
WS_RATIO = 0.05
ALLOWED_TOKEN_MISMATCH_RATE = 0.05
last_char_solution_count_unconstrained = 10

token_grammar_json = "tokengrammar.json"

###############################################
######## Overapproximation Reduction ##########
###############################################

parse_timeout_seconds = 60
stop_after_k_timeouts = 1
precision_threshold = 0.99 # Stop when precision is at least this good

max_refinements = 100
max_refinement_time_seconds = 60*60 # 1 hour
k_shortest = 100
cnt_inputs_refinement = cnt_inputs
min_count_valid = 1
k_subtrees =  10