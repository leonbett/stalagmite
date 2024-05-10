import os
import pandas as pd

import config

class Subject:
    def __init__(self, subject, link):
        self.link = link

        self.csv_file_accuracy = os.path.join(config.accuracy_csv_dir, f"accuracy_{subject}.csv")
        self.df_accuracy = pd.read_csv(self.csv_file_accuracy, index_col=0)

        if subject == "tinyc":
            self.label = "TINY-C"
        else:
            self.label = subject.upper()
