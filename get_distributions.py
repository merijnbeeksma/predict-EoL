from support import config as CFG
from support import my_csv as CSV
from support import logging as LOG
from support import parameters as PAR

from collections import Counter, defaultdict
from datetime import date


class TimeBin:

    def run(self):
        self.create_distributions()

    def create_distributions(self):
        self.events = defaultdict(list)
        for event_category in CFG.EVENT_CATEGORIES:
            events = defaultdict(list)
            # Read events
            filename = CFG.PHASE1_DIR / 'dev_ev_{}.csv'.format(event_category.tla)
            with CSV.FileReader(filename) as source:
                header = next(source)
                assert header == ['PRAKTIJK-ID', 'PATIENT-ID', 'LEVENSVERWACHTING', 'EVENT-TYPE', 'EVENT-DATA']
                count = defaultdict(int)
                for praktijk_id, patient_id, days_to_live, event_type, event_data in source:
                    count[event_data] += 1
            distribution = [(key, value) for key, value in count.items()]
            distribution = sorted(distribution, key=lambda distribution: distribution[1], reverse=True)
            print('\n{};FREQ'.format(event_category.full_name))
            for item in distribution:
                print('{};{}'.format(item[0], item[1]))

# Main program
if __name__ == '__main__':
    PAR.read(CFG.SOURCE_DIR)
    TimeBin().run()
