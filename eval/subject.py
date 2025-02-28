import os
import config

def get_next_run_id(directory):
    existing_run_directories = os.listdir(directory)
    
    existing_numbers = []
    for name in existing_run_directories:
        if name.isdigit():
            existing_numbers.append(int(name))
    
    if not existing_numbers:
        return "1"
    
    next_number = max(existing_numbers) + 1
    return f"{next_number}"

class Subject:
    def __init__(self, subject: str):
        self.subject = subject
        self.subject_dir = os.path.join(config.root, f'subjects/{subject}')
        self.run_id = get_next_run_id(os.path.join(config.root, f'data/subjects/{subject}'))
        self.run_dir = os.path.join(config.root, f'data/subjects/{subject}/{self.run_id}')
        self.run_grammar_dir = os.path.join(self.run_dir, 'grammars/')
        self.run_eval_dir = os.path.join(self.run_dir, 'eval/')

        os.system(f"mkdir {self.run_dir}")
        os.system(f"mkdir {self.run_grammar_dir}")
        os.system(f"mkdir {self.run_eval_dir}")

        self.initial_grammar = os.path.join(self.run_grammar_dir, f'initial_grammar.json')
        self.refined_grammar = os.path.join(self.run_grammar_dir, f'refined_grammar.json')

        self.accuracy_csv_file = os.path.join(self.run_eval_dir, f'accuracy.csv') 
        self.readability_csv_file = os.path.join(self.run_eval_dir, f'readability.csv') 
        self.timestamps_file = os.path.join(self.run_eval_dir, f'timestamps.csv') 

        self.golden_grammar = os.path.join(config.root, f'data/golden_grammars/golden_grammar_{subject}.json')

        self.put = os.path.join(self.subject_dir, 'a.out')
        self.put_cov = os.path.join(self.subject_dir, 'cov')