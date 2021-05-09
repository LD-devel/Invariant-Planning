import os
import sys
import time
import matplotlib.pyplot as plt

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
val_path = '/bin/validate'

sys.path.insert(0, BASE_DIR) 

import translate
import subprocess
import utils
from planner import encoder
from planner import modifier
from planner import search

def main():

    problems = [('zeno-travel-linear', 'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     '.\pddl_examples\linear\zeno-travel-linear\instances',1)]

    # Create report
    myReport = Report()

    # Set upper bound
    ub = 100
    
    for domain_name, domain, instance_dir, domain_bound in problems:
        counter = 0
        abs_instance_dir = os.path.join(BASE_DIR, instance_dir)

        for filename in os.listdir(abs_instance_dir):
            if filename.endswith('.pddl') and counter < domain_bound:

                counter = counter +1

                instance_path = os.path.join(abs_instance_dir, filename)
                domain_path = os.path.join(BASE_DIR, domain)

                task = translate.pddl.open(instance_path, domain_path)

                # Test parralel search for comparison
                try:
                    start_time = time.time()
                    e = encoder.EncoderSMT(task, modifier.ParallelModifier())
                    s = search.SearchSMT(e,ub)
                    found, horizon, solution = s.do_linear_search(True)
                    myReport.create_log('parallel', domain_path, instance_path, domain_name, 
                        filename, found, horizon, solution, (time.time()-start_time))
                except:
                    myReport.fail_log('parallel' , domain_name, filename)


                # Test relaxed search
                try:
                    start_time = time.time()
                    e = encoder.EncoderSMT(task, modifier.ParallelModifier())
                    s = search.SearchSMT(e,ub)
                    found, horizon, solution = s.do_linear_search(True)
                    myReport.create_log('relaxed', domain_path, instance_path, domain_name, 
                        filename, found, horizon, solution, (time.time()-start_time))
                except:
                    myReport.fail_log('relaxed', domain_name, filename)
    
    myReport.export()

class Report():

    def __init__(self):
        self.logs = []

    def create_log(self, mode, domain_path, instance_path, domain, instance, found, horizon, solution, time):
        val = BASE_DIR + val_path
        print(val)
        if(found):
            try:
                if solution.validate(val, domain_path, instance_path):
                    print('Valid plan found! in time: ' + str(time))
                    self.logs.append({'mode' : mode, 'domain' : domain, 'instance' : instance, 
                        'found' : True, 'valid' : True, 'steps' : horizon, 'time' : time})
                else:
                    print('Plan not valid.')
                    self.logs.append({'mode' : mode, 'domain' : domain, 'instance' : instance, 
                        'found' : True, 'valid' : False, 'steps' : horizon, 'time' : time})
            except:
                print('Plan could not be validated')
        else:
            print('No plan found: ' + mode)
            self.logs.append({'mode' : mode, 'domain' : domain, 'instance' : instance, 
                'found' : False, 'valid' : False, 'steps' : horizon, 'time' : time})

    def fail_log(self, mode, domain_name, filename):
        print('***************** Fail during search: ' + mode + domain_name + filename)

    def export(self):
        print(self.logs)
        self.sorted = {}

        # Clean up the log
        for log in self.logs:
            if not self.sorted.has_key(log['domain']):
                self.sorted[log['domain']] = {}
            if not self.sorted[log['domain']].has_key(log['instance']):
                self.sorted[log['domain']][log['instance']] = {}
            
            # Insert number of steps in plan
            key = log['mode'] + '_steps'
            self.sorted[log['domain']][log['instance']][key] = log['steps']

            # Time to compute
            key = log['mode'] + '_time'
            self.sorted[log['domain']][log['instance']][key] = log['time']

            # Validity
            key = log['mode'] + '_valid'
            self.sorted[log['domain']][log['instance']][key] = log['valid']
        
        # Plot the log
        figure = plt.figure()
        fig, axes = plt.subplots(nrows=len(self.sorted), ncols=2, sharex=True, sharey=True, squeeze=False)

        i = 0
        for key, dom  in self.sorted.iteritems():
            x = []
            t1 = []
            t2 = []
            s1 = []
            s3 = []
            n = 1
            for key, ins in dom.iteritems():
                x.append(n)
                n = n + 1
                t1.append(ins['parallel_time'])
                t2.append(ins['relaxed_time'])
            # Plot in subplot
            for k in range(len(x)):
                axes[i,0].bar(x[k]-0.2, t1[k], width=0.4, color='b', align='center')
                axes[i,0].bar(x[k]+0.2, t2[k], width=0.4, color='g', align='center')
            i = i+1
        
        #plt.show()
        figure.savefig('analysis_figure.png', bbox_inches='tight')
        plt.savefig('analysis.png')

if __name__ == '__main__':
    main()
