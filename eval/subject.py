import os
import config

class Subject:
    def __init__(self, subject: str):
        self.subject = subject
        self.subject_dir = os.path.join(config.root, f'subjects/{subject}')
        self.initial_grammar = os.path.join(config.grammars_initial_dir, f'initial_grammar_{subject}.json')
        self.refined_grammar = os.path.join(config.grammars_refined_dir, f'refined_grammar_{subject}.json')
        self.golden_grammar = os.path.join(config.grammars_golden_dir, f'golden_grammar_{subject}.json')

        self.put = os.path.join(self.subject_dir, 'a.out')
        self.put_cov = os.path.join(self.subject_dir, 'cov')
