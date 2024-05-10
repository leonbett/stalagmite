# NOTE: The containing directory of this file must be in PYTHONPATH.
import os

subjects = ["tinyc", "lisp", "calc", "json"]
root = '/home/author/conf/klee_stuff/examples' # must be absolute

proxy_parse_functions_c = "proxy_parse_functions.c"

###############################################
#################### KLEE #####################
###############################################
max_memory = 32000 # 32 GB limit (default: 2GB)
max_time_tokens = "30min"
max_token_length = 10

max_time_syntax = "120min"
max_input_length = 20


###############################################
################# Evaluation ##################
###############################################

max_depths = [10]
cnt_inputs = 1000

accuracy_csv_dir = os.path.join(root, "data/paper/accuracy/csv")
accuracy_tex_dir = os.path.join(root, "data/paper/accuracy/tex")
accuracy_plot_dir = os.path.join(root, "data/paper/accuracy/plot")

grammars_golden_dir = os.path.join(root, "data/paper/grammars/golden")
grammars_initial_dir = os.path.join(root, "data/paper/grammars/initial")
grammars_refined_dir = os.path.join(root, "data/paper/grammars/refined")

###############################################
############ Token Generalization #############
###############################################
THRESHOLD_GENERALIZATION = 3
WS_RATIO = 0.05
ALLOWED_TOKEN_MISMATCH_RATE = 0.05
last_char_solution_count_unconstrained = 10

token_grammar_json = "tokengrammar.json"

###############################################
######## Overapproximation reduction ##########
###############################################

parse_timeout_seconds = 60 # 30
stop_after_k_timeouts = 1
precision_threshold = 0.99 # Stop when precision is at least this good

max_refinements = 100
k_shortest = 10 # Only consider the shortest 10 failing inputs to limit time consumption
cnt_inputs_refinement = cnt_inputs # Tune this up to avoid trading precision for recall (recall should never decline)
min_count_valid = 1
k_subtrees = 10 # 100



