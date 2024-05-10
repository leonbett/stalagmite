#!/bin/bash

subjects=("tinyc" "lisp" "json" "calc")

create_session_all() {
    subject=$1
    mine_cmd="python3 eval.py --subject $subject --mine &> logs/eval_mine_log_$subject"
    refine_cmd="python3 eval.py --subject $subject --refine &> logs/eval_refine_log_$subject"
    data_cmd="python3 eval.py --subject $subject --data &> logs/eval_data_log_$subject"

    tmux new-session -d -s "staminag_$subject" "$mine_cmd;$refine_cmd;$data_cmd"
}

create_session_data_only() {
    subject=$1
    data_cmd="python3 eval.py --subject $subject --data &> logs/eval_data_log_$subject"
    echo $data_cmd
    tmux new-session -d -s "staminag_onlydata_$subject" "$data_cmd"
}


are_tmux_jobs_still_running() {
    num_sessions=$(tmux list-sessions | wc -l)
    if [ $num_sessions -eq 0 ]; then
        echo "All subjects have finished."
        return 0
    else
        echo "Some subjects are still running."
        return 1
    fi
}


if [ "$1" = "--data" ]; then
    echo "only data"
    for subject in "${subjects[@]}"; do
        create_session_data_only "$subject"
    done
else
    echo "all"
    echo "removing old data"
    rm logs/eval_* 2>/dev/null
    rm ../data/paper/accuracy/csv/*.csv 2>/dev/null
    rm ../data/paper/accuracy/tex/*.tex 2>/dev/null
    rm ../data/paper/grammars/initial/* 2>/dev/null
    rm ../data/paper/grammars/refined/* 2>/dev/null

    echo "starting tmux jobs"
    for subject in "${subjects[@]}"; do
        create_session_all "$subject"
    done

    echo "waiting for tmux jobs to finish"
    while ! are_tmux_jobs_still_running; do
        sleep 10 # seconds
    done

    echo "generating .tex tables"
    python3 tex/gen_tex_tables.py

    echo "done!"
fi
