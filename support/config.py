from collections import namedtuple
from pathlib import Path

# Welke praktijken worden meegenomen
PRAKTIJK_IDS = ('p1', 'p2', 'p5', 'p6', 'p7', 'p8', 'p9')
# PRAKTIJK_IDS = ('p9',)

# Directories
PROJECT_DIR = Path('..').resolve()
SOURCE_DIR = PROJECT_DIR / 'Source'

DATA_DIR = PROJECT_DIR / 'Data'
CORPUS_DIR = DATA_DIR / 'Laatste vijf jaar'
CORPUS_PER_PRAKTIJK_DIR = CORPUS_DIR / 'Data per praktijk'
CORPUS_PER_TYPE_DIR = CORPUS_DIR / 'Data per type'

RESULTS_DIR = PROJECT_DIR / 'Results'
PHASE1_DIR = RESULTS_DIR / 'Phase1'
PHASE2_DIR = RESULTS_DIR / 'Phase2'
PHASE3_DIR = RESULTS_DIR / 'Phase3'
PHASE4_DIR = RESULTS_DIR / 'Phase4'
STAT_DIR = PROJECT_DIR / 'Statistics'

EXPERIMENT_DIR = PROJECT_DIR / 'Experiment'

# Event types
_EventCategory = namedtuple('EventCategory', ['tla', 'full_name'])
EVENT_CATEGORIES = [
    _EventCategory('ana', 'Anamnese'),
    _EventCategory('con', 'Consult'),
    _EventCategory('dia', 'Diagnose'),
    _EventCategory('icd', 'ICD10'),
    _EventCategory('int', 'Interventie'),
    _EventCategory('med', 'Medicatie'),
    _EventCategory('mtw', 'Meetwaarde'),
    _EventCategory('rfe', 'Reason for Encounter')
]
