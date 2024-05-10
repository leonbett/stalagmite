import os
import pandas as pd
import numpy as np

from config import accuracy_csv_dir, accuracy_tex_dir

from subject import Subject

bs = '\\'
newline = '\n'

dc = 1 # decimal places

def format(n):
    if np.isnan(n):
        return "N/A"
    else:
        return f"{n}\%"

def generate_precision_recall_latex_row(subject: Subject):
    print("df for ", subject.label)
    df = subject.df_accuracy

    initial_precision = round(100 * df.at['initial', 'precision depth 10'], dc)
    initial_recall = round(100 * df.at['initial', 'recall depth 10'], dc)
    initial_f1 = round(100 * df.at['initial', 'F1 depth 10'], dc)

    refined_precision = round(100 * df.at['refined', 'precision depth 10'], dc)
    refined_recall = round(100 * df.at['refined', 'recall depth 10'], dc)
    refined_f1 = round(100 * df.at['refined', 'F1 depth 10'], dc)


    return f"{bs}href{{{subject.link}}}{{{subject.label}}}  & {initial_precision}{bs}%    & {initial_recall}{bs}%    & {initial_f1}{bs}% \
                                                            & {refined_precision}{bs}%   & {refined_recall}{bs}%     & {refined_f1}{bs}% \
                                                            {bs}{bs}"

def compute_AverageRefinedPrecision(subjects: list[Subject]):
    refined_precisions = []
    for subject in subjects:
        df = subject.df_accuracy
        refined_precision = df.at['refined', 'precision depth 10']
        refined_precisions.append(refined_precision)
    return round(100 * (sum(refined_precisions) / len(refined_precisions)), dc)

def compute_AverageRefinedRecall(subjects: list[Subject]):
    refined_recalls = []
    for subject in subjects:
        df = subject.df_accuracy
        refined_recall = df.at['refined', 'recall depth 10']
        refined_recalls.append(refined_recall)
    return round(100 * (sum(refined_recalls) / len(refined_recalls)), dc)

def compute_LowestInitialPrecision(subjects: list[Subject]):
    initial_precisions = []
    for subject in subjects:
        df = subject.df_accuracy
        initial_precision = df.at['initial', 'precision depth 10']
        initial_precisions.append(initial_precision)
    return round(100 * (min(initial_precisions)), dc)

def compute_HighestInitialPrecision(subjects: list[Subject]):
    initial_precisions = []
    for subject in subjects:
        df = subject.df_accuracy
        initial_precision = df.at['initial', 'precision depth 10']
        initial_precisions.append(initial_precision)
    return round(100 * (max(initial_precisions)), dc)

def compute_LowestRefinedPrecision(subjects: list[Subject]):
    refined_precisions = []
    for subject in subjects:
        df = subject.df_accuracy
        refined_precision = df.at['refined', 'precision depth 10']
        refined_precisions.append(refined_precision)
    return round(100 * (min(refined_precisions)), dc)

def generate_precision_recall_latex_table(subjects: list[Subject]):
    template = f'''\
{bs}def{bs}AverageRefinedPrecision{{{compute_AverageRefinedPrecision(subjects)}{bs}%{bs}xspace}}
{bs}def{bs}AverageRefinedRecall{{{compute_AverageRefinedRecall(subjects)}{bs}%{bs}xspace}}
{bs}def{bs}LowestInitialPrecision{{{compute_LowestInitialPrecision(subjects)}{bs}%{bs}xspace}}
{bs}def{bs}HighestInitialPrecision{{{compute_HighestInitialPrecision(subjects)}{bs}%{bs}xspace}}
{bs}def{bs}LowestRefinedPrecision{{{compute_LowestRefinedPrecision(subjects)}{bs}%{bs}xspace}}

{bs}begin{{table*}}[t]
{bs}caption{{Grammar accuracy}}
{bs}label{{tab:accuracy}}
{bs}rowcolors{{2}}{{gray!25}}{{white}}
{bs}begin{{tabular}}{{l|rrr|rrr|rrr}}
{bs}rowcolor{{lime}}
        & {bs}multicolumn{{3}}{{c}}{{{bs}textbf{{Initial}}}}
        & {bs}multicolumn{{3}}{{c}}{{{bs}textbf{{Refined}}}}
        {bs}{bs}
{bs}rowcolor{{lime}}
{bs}textbf{{Subject}} & {bs}textbf{{precision}} & {bs}textbf{{recall}} & {bs}textbf{{F1}}
                      & {bs}textbf{{precision}} & {bs}textbf{{recall}} & {bs}textbf{{F1}}
                      {bs}{bs}
{newline.join(generate_precision_recall_latex_row(subject) for subject in subjects)}
{bs}end{{tabular}}
{bs}end{{table*}}
'''

    output_file = os.path.join(accuracy_tex_dir, "accuracy.tex")
    with open(output_file, "w") as f:
        f.write(template)
    print(f'serialized {output_file}')
