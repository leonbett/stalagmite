import os
import json
import sys
import random
import logging
import ctypes

import config

from generalize_tokens import generalize_tokens
from generalize_helpers import load_json_file, load_jsons, is_nt, unreachable_nonterminals, serialize_grammar, print_grammar
from generalize_tidy import inline_single_rule_nts, opt_generalization


EventCharacter = "EventCharacter"
EventParseCall = "EventParseCall"
EventRevert = "EventRevert"
EventLoopEntry = "EventLoopEntry"
EventLoopExit = "EventLoopExit"
EventTokenByteCursor = "EventTokenByteCursor"
EventToken = "EventToken" # token cursor
EventUndoToken = "EventUndoToken"

d_loop_header_to_simple_id = {}

simple_id_ctr = 0
def NEXT_SIMPLE_ID():
    global simple_id_ctr
    simple_id_ctr += 1
    return simple_id_ctr

def get_simpleloopid(loop_header):
    if loop_header not in d_loop_header_to_simple_id:
        d_loop_header_to_simple_id[loop_header] = str(NEXT_SIMPLE_ID())
    return d_loop_header_to_simple_id[loop_header]

def print_events(name, d):
    print(f"{name}:")
    for key, j in d.items():
        logging.info(key)
        events = j["events"]
        i = 0
        for event in events:
            logging.info(f"event {i}")
            logging.info(json.dumps(event))
            i += 1
        logging.info("")

# Reverse direction, because get_next_token is offset by 1 always.
def fold_undo_tokencursor(events):
    # Sequential undo fold; no loops.
    # Iterate stack backwards: If EventUndoToken found, do not push the next EventToken.
    skip_next = False
    new_events = []
    i = len(events)
    while i > 0:
        i -= 1
        event = events[i]
        if event["event"] == EventUndoToken:
            assert not skip_next, "Read two sequential EventUndoTokens"
            skip_next = True
            continue
        if event["event"] == EventToken:
            if skip_next:
                skip_next = False
                continue
        new_events.append(event)
    new_events = list(reversed(new_events)) # reverse because we pushed in reverse order
    assert "EventUndoToken" not in str(new_events)
    return new_events

def fold_undo_bytecursor(events):
    # Sequential undo fold; no loops.
    # Iterate stack forwards: If EventUndoToken found, do not push the next EventTokenByteCursor.
    skip_next = False
    new_events = []
    i = 0
    while i < len(events):
        event = events[i]
        i += 1
        if event["event"] == EventUndoToken:
            assert not skip_next, "Read two sequential EventUndoTokens"
            skip_next = True
            continue
        if event["event"] == EventTokenByteCursor: #!
            if skip_next:
                skip_next = False
                continue
        new_events.append(event)
    assert "EventUndoToken" not in str(new_events)
    return new_events


class TraceToGrammar():
    #d: filename to json with trace
    def __init__(self, d: dict, fua: str, token_dict: dict, isTokenCursor: bool):
        self.d = d
        self.fua = fua
        self.isTokenCursor = isTokenCursor
        self.ppfs = set()
        self.overapprox_tokens = {} # for isTokenCursor
        self.overapprox_ctr = 0
        self.token_dict = token_dict # Only relevant for byte cursor
        self.token_grammar = {} # Only relevant for byte cursor
        self.observed_token_ids = set() # Only relevant for *token* cursor
        self.simple_id_ctr = 0
        self.d_loop_entry_to_simple_id = {}
        self.loop_grammar = {}
        self.current_functionpath = None
        self.handle = {
            EventParseCall: self.handle_EventParseCall,
            EventTokenByteCursor: self.handle_EventTokenByteCursor, # byte cursor
            EventToken: self.handle_EventToken, # token cursor
            EventLoopEntry: self.handle_EventLoopEntry,
            EventLoopExit: self.handle_EventLoopExit
        }

    def handle_EventParseCall(self, event):
        ppf = event["ppf"]
        self.ppfs.add(ppf)
        self.stack[-1][1].append(f"<{ppf}>")

    '''
    EventToken is used only for token cursor subjects.
    '''
    def handle_EventToken(self, event):
        assert self.isTokenCursor
        possible_tokens = event["possible_tokens"]
        assert possible_tokens != []
        if len(possible_tokens) > 1:
            t_possible_tokens = tuple(sorted(event["possible_tokens"]))
            if t_possible_tokens not in self.overapprox_tokens:
                self.overapprox_tokens[t_possible_tokens] = self.overapprox_ctr 
                self.overapprox_ctr += 1
            token = f"<set_token_{self.fua}_{self.overapprox_tokens[t_possible_tokens]}>"
        else:
            token_id = possible_tokens[0]
            token = f"<TOK_{token_id}>"
            self.observed_token_ids.add(token_id)
        self.stack[-1][1].append(token)

    def handle_EventLoopEntry(self, event):
        loop_header = event["loop_id"]
        iter_cnt = event["iter_cnt"]
        if loop_header not in self.d_loop_entry_to_simple_id:
            self.d_loop_entry_to_simple_id[loop_header] = str(self.simple_id_ctr)
            self.simple_id_ctr += 1
            # First time we see this loop, so we set up the loop grammar structure.
            simpleloopid = self.d_loop_entry_to_simple_id[loop_header]
            loop_nt = f"<{self.fua}_loop_{simpleloopid}>"
            loop_nt_exit = f"<{self.fua}_loop_{simpleloopid}_exit>"
            loop_nt_cont = f"<{self.fua}_loop_{simpleloopid}_continue>"
            self.loop_grammar[loop_nt] = [[loop_nt_exit], [loop_nt_cont, loop_nt]]
            self.loop_grammar[loop_nt_exit] = []
            self.loop_grammar[loop_nt_cont] = []
        simpleloopid = self.d_loop_entry_to_simple_id[loop_header]
        loop_nt = f"<{self.fua}_loop_{simpleloopid}>"
        self.stack.append((loop_nt, []))

    def handle_EventLoopExit(self, event):
        loop_header = event["loop_id"]
        simpleloopid = self.d_loop_entry_to_simple_id[loop_header]
        loop_nt = f"<{self.fua}_loop_{simpleloopid}>"
        assert self.stack[-1][0] == loop_nt
        iterations = []
        while self.stack[-1][0] == loop_nt:
            iterations.append(self.stack[-1])
            self.stack = self.stack[:-1] # pop
        iterations.reverse() # Now the first iteration is first
        assert 1 <= len(iterations) <= 3
        loop_iter_exit_nt = f"<{self.fua}_loop_{simpleloopid}_exit>"
        if len(iterations) == 1:
            # if loop_rule == [] here, this is skipping the loop, we must not include this.
            if iterations[0][1] != []:
                if iterations[0][1] not in self.loop_grammar[loop_iter_exit_nt]:
                    self.loop_grammar[loop_iter_exit_nt].append(iterations[0][1])
                self.stack[-1][1].append(f"<{self.fua}_loop_{simpleloopid}>")

        elif len(iterations) == 2:
            joined_loop_rule = iterations[0][1] + iterations[1][1] # 1st iteration + exit iteration
            if joined_loop_rule not in self.loop_grammar[loop_iter_exit_nt]:
                self.loop_grammar[loop_iter_exit_nt].append(joined_loop_rule)
            self.stack[-1][1].append(f"<{self.fua}_loop_{simpleloopid}>")
        elif len(iterations) == 3:
            loop_cont_iter_nt = f"<{self.fua}_loop_{simpleloopid}_continue>"
            joined_loop_rule = iterations[1][1] + iterations[2][1] # 2nd iteration + exit iter

            if iterations[0][1] not in self.loop_grammar[loop_cont_iter_nt]: # cont iter = 1st iteration
                self.loop_grammar[loop_cont_iter_nt].append(iterations[0][1])
            if joined_loop_rule not in self.loop_grammar[loop_iter_exit_nt]: # exit iter
                self.loop_grammar[loop_iter_exit_nt].append(joined_loop_rule)
            self.stack[-1][1].append(f"<{self.fua}_loop_{simpleloopid}>")

    def handle_EventTokenByteCursor(self, event):
        assert not self.isTokenCursor
        token_id = event["exec_ctx"]
        nt, general_grammar = self.token_dict[self.current_functionpath][token_id]
        self.token_grammar = {**self.token_grammar, **general_grammar}
        self.stack[-1][1].append(nt)

    def to_grammar(self):
        fua = self.fua
        d = self.d

        main_grammar = { f"<{fua}>": [] }
        for filename, j in d.items():
            self.current_functionpath = j["functionpath"] # for EventTokenByteCursor
            events = j["events"]
            self.stack = [(None, [])] # The function scope `rule`
            for event in events:
                event_type = event["event"]
                self.handle[event_type](event)
            assert len(self.stack) == 1 and self.stack[0][0] is None, "seems like a EventLoopExit is missing"
            if self.stack[0][1] not in main_grammar[f"<{fua}>"]:
                logging.info("Adding rule to grammar: " + str(self.stack[0][1]))
                logging.info("the events were: ")
                logging.info(json.dumps(events, indent=1))
                # Do not add duplicates.
                main_grammar[f"<{fua}>"].append(self.stack[0][1])

        overapprox_grammar = {}
        for tup, ctr in self.overapprox_tokens.items():
            overapprox_grammar[f"<set_token_{fua}_{ctr}>"] = [[f"<TOK_{ctypes.c_int32(int(token_id)).value}>"] for token_id in tup]
            for token_id in tup:
                self.observed_token_ids.add(ctypes.c_int32(int(token_id)).value)


        return main_grammar, self.loop_grammar, self.token_grammar, overapprox_grammar, self.ppfs, self.observed_token_ids

def is_token_unconstrained(event_next_token: dict):
    # Only called for token cursor subjects.
    assert event_next_token["event"] == EventToken

    this_token_values = set(event_next_token["possible_tokens"])
    token_grammar = load_json_file(config.token_grammar_json) # Assumption: token analysis was run before
    token_count = len([key for key in token_grammar.keys() if key.startswith("<TOK_")])
    # We say a token is (mostly) unconstrained if it can assume at least 50% of all posible values
    return len(this_token_values) >= (token_count//2)

def is_sequenced_by_token(following_events):
    for event in following_events:
        et = event["event"]
        if et == EventParseCall:
            return False
        elif et == EventToken:
            return True
        else:
            continue
    return False

def insert_undo_token(d_tokens, isTokenCursor: bool, isEntryPoint: bool = False):
    d_undo_tokens = {}
    last_event_token = None
    # Insert EventUndoToken before EventParseCall
    for key, j in d_tokens.items():
        events = d_tokens[key]["events"]
        new_events = []
        for i, event in enumerate(events):
            if event["event"] in [EventTokenByteCursor, EventToken]:
                last_event_token = event
            elif event["event"] == EventParseCall:
                # Prepend an additional EventUndoToken, because PPFs always do a next_token call inside.
                new_events.append({"event": EventUndoToken})
            new_events.append(event)
            if isTokenCursor and isEntryPoint and i==0:
                assert event["event"] == EventToken, "By our model, the first action should always be a next_token() call by the klee wrapper."
                # We delete the first token if it's unconstrained and we're in the entry point function *and* it is sequenced by another token without a PPF call in between.
                # Reason: Some entry point parse functions bootstrap themselves by doing an initial next_token call.
                # Hence, the one we do in the harness for every parse function is redundant.
                # We detect this if the first token in unconstrained and not followed by a PPF call.
                if is_token_unconstrained(event) and is_sequenced_by_token(events[i+1:]):
                    new_events.append({"event": EventUndoToken})
        # Delete last token if unconstrained
        if isTokenCursor and is_token_unconstrained(last_event_token):
            new_events.append({"event": EventUndoToken})
        j_new_events = {"functionpath": d_tokens[key]["functionpath"], "events": new_events}
        d_undo_tokens[key] = j_new_events
    print_events("d_undo_tokens", d_undo_tokens)
    return d_undo_tokens

def fold_undos(d_undo_tokens, isTokenCursor:bool):
    d_fold_tokens = {}

    # Step: Iterate stack backwards: If EventUndoToken found, do not push the next EventToken/EventTokenByteCursor.
    for key, j in d_undo_tokens.items():
        events = d_undo_tokens[key]["events"]
        if isTokenCursor: new_events = fold_undo_tokencursor(events)
        else: new_events = fold_undo_bytecursor(events)
        j_new_events = {"functionpath": d_undo_tokens[key]["functionpath"], "events": new_events}
        d_fold_tokens[key] = j_new_events
    assert "EventUndoToken" not in str(d_fold_tokens)
    #print_events("d_fold_tokens", d_fold_tokens)
    return d_fold_tokens

def apply_reverts_to_one_trace(events):
    # Sequential undo fold; no loops.
    # Iterate stack backwards: If EventUndoToken found, do not push the next EventToken.
    eat_ppfs = False # This is required because on revert, we want to undo also ppfs until the next EventToken.
    n_skip = 0
    new_events = []
    i = len(events)
    while i > 0:
        i -= 1
        event = events[i]
        if event["event"] == EventRevert:
            n_skip += event["count"]
            eat_ppfs = True
            continue
        else:
            if event["event"] == EventToken:
              if n_skip > 0:
                n_skip -= 1
                continue
              else:
                  eat_ppfs = False
            elif event["event"] == EventParseCall:
                if eat_ppfs: continue
            new_events.append(event)
    new_events = list(reversed(new_events)) # reverse because we pushed in reverse order
    return new_events

def apply_reverts(d):
    d_res = {}

    # Iterate stack backwards: If EventUndoToken found, do not push the next EventToken.
    for key, j in d.items():
        events = d[key]["events"]
        new_events = apply_reverts_to_one_trace(events)
        j_new_events = {"functionpath": d[key]["functionpath"], "events": new_events}
        d_res[key] = j_new_events
    assert "EventRevert" not in str(d_res)
    #print_events("d_res", d_res)
    return d_res

def configure_logger(fua):
    logging.basicConfig(
        level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s'  # Define the log message format
    )

    log_file_path = f'genlog_{fua}'
    # Delete the file if it already exists
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    # Create a FileHandler to write logs to a file
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)  # Set the logging level for the file handler
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Add the file handler to the logger
    logging.getLogger().addHandler(file_handler)

    # Remove the default console handler (if it exists) -> do not print to stdout.
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            logging.getLogger().removeHandler(handler)

def EventCharacters_to_EventTokenByteCursor(eventstack):
    used_random = False
    events = []

    cur_tok = None # exec_ctx
    cur_chars = []
    for entry in eventstack["events"]:
        if entry["event"] != EventCharacter:
            # This might have ended a token
            if cur_tok:
                events.append({"event": EventTokenByteCursor, "concrete_characters": cur_chars, "exec_ctx": cur_tok})
                cur_tok = None
                cur_chars = []
            events.append(entry)
        else:
            possible_solutions = entry['possible_solutions']
            concrete_character = random.choice(possible_solutions)
            if len(possible_solutions) > 1:
                used_random = True
                while concrete_character == 0 and not all(c==0 for c in possible_solutions):
                    concrete_character = random.choice(possible_solutions)

            if cur_tok:
                # There is an ongoing token
                if entry["exec_ctx"] == cur_tok:
                    # We have another character of the same token
                    cur_chars.append(concrete_character)
                else:
                    # We finish the previous token
                    events.append({"event": EventTokenByteCursor, "concrete_characters": cur_chars, "exec_ctx": cur_tok})
                    # ... and start a new one
                    cur_tok = entry["exec_ctx"]
                    cur_chars = [concrete_character]
            else:
                # There is no ongoing token
                # So we start a new one
                cur_tok = entry['exec_ctx']
                cur_chars = [concrete_character]

    if cur_tok:
        # At the end, there might be a leftover token, which we have to push.
        events.append({"event": EventTokenByteCursor, "concrete_characters": cur_chars, "exec_ctx": cur_tok})

    return {"functionpath": eventstack["functionpath"], "events": events}, used_random

def meta_EventCharacters_to_EventTokenByteCursor(d):
    repeat = []
    d_tokens = {}
    for key, j in d.items():
        tok_eventstack, used_random = EventCharacters_to_EventTokenByteCursor(j)
        if used_random:
            repeat.append((key, j))
        d_tokens[key] = tok_eventstack
    
    # For each trace with multiple options, for which we did a random selection, duplicate this 100 times, to get more diversity
    for key, j in repeat:
        for i in range(100):
            tok_eventstack, _ = EventCharacters_to_EventTokenByteCursor(j)
            d_tokens[key + f'_rep_{str(i)}'] = tok_eventstack

    return d_tokens

def inline_single_rules_and_opt_generalization(grammar):
    # Do (inline fix point, opt fix point) in another fix point loop,
    # as they depend on each other.
    global_change = True
    while global_change:
        global_change = False
        # Inline single rule non-terminals.
        # Fix-point iteration, because inlined rules, in turn, can have inlineable nts.
        change = True
        while change:
            grammar, change = inline_single_rule_nts(grammar)
            global_change = change

        # Do "<opt>" cleanup
        grammar, _global_change = opt_generalization(grammar)
        global_change |= _global_change

    return grammar

def generalize(fua: str, isTokenCursor: bool, isEntryPoint: bool):
    configure_logger(fua)

    # `d` maps file names to jsons.
    d = load_jsons('jsons/')
    #print_events("d", d)

    if isTokenCursor:
        d = apply_reverts(d)
        d_undo_tokens = insert_undo_token(d, isTokenCursor, isEntryPoint)
        d_fold_tokens = fold_undos(d_undo_tokens, isTokenCursor)
        d = d_fold_tokens
        token_dict = None # only used for byte cursor
    else:
        d = meta_EventCharacters_to_EventTokenByteCursor(d)
        d_undo_tokens = insert_undo_token(d, isTokenCursor)
        d_fold_tokens = fold_undos(d_undo_tokens, isTokenCursor)
        d = d_fold_tokens
        token_dict = generalize_tokens(d)

    converter = TraceToGrammar(d, fua, token_dict, isTokenCursor)

    main_grammar, loop_grammar, token_grammar, overapprox_grammar, ppfs, observed_token_ids = converter.to_grammar()
    print_grammar("token_dict", token_dict) # only for byte-cursor
    print_grammar("main_grammar", main_grammar)
    print_grammar("loop_grammar", loop_grammar)

    ppf_grammar = {f'<{ppf}>': [[]] for ppf in ppfs}
    if isTokenCursor: token_grammar = {f"<TOK_{token_id}>": [[]] for token_id in observed_token_ids}
    # Join all grammars (required for inlining, opt)
    grammar = {**ppf_grammar, **token_grammar, **main_grammar, **loop_grammar, **overapprox_grammar} # Order is important here: Otherwise we could override grammar ruleset we just mined with an empty PPF ruleset, if the FUA calls itself. 

    inline_single_rules_and_opt_generalization(grammar)

    for nt in unreachable_nonterminals(grammar, start_symbol=f'<{fua}>'):
        del grammar[nt]

    for ppf in ppfs:
        if ppf != fua: # FUA could call itself, and we definitely do not want to remove the FUA rule set.
            if f'<{ppf}>' in grammar:
                del grammar[f'<{ppf}>'] # removing these dummies as they will be replaced later anyway by FUAs

    serialize_grammar(grammar, f'grammar_{fua}.json')
    return ppfs
