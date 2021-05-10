import os
import sys
import time
import matplotlib.pyplot as plt
from natsort import natsorted

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

    problems = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',7),
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0),
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',10),
     ('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     r'pddl_examples\linear\fo_counters_inv\instances',10),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',10),
     ('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     r'pddl_examples\linear\sailing_ln\instances',0),
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',4),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',3),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',5),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',5)]

    '''problems = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',1),
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0),
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',2),
     ('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     r'pddl_examples\linear\fo_counters_inv\instances',1),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',1),
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',0),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',0),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',0),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',0),
     ('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     r'pddl_examples\linear\sailing_ln\instances',0)]'''

    # Create report
    myReport = Report()

    # Set upper bound
    ub = 100
    
    for domain_name, domain, instance_dir, domain_bound in problems:
        counter = 0
        abs_instance_dir = os.path.join(BASE_DIR, instance_dir)
        #abs_instance_dir = BASE_DIR + instance_dir

        for filename in natsorted(os.listdir(abs_instance_dir)):
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
        for key1, dom  in self.sorted.iteritems():
            # New fig for each domain
            figure = plt.figure()
            fig, axes = plt.subplots(nrows=1, ncols=2, sharex=False, sharey=False, squeeze=False)
            x = []
            t1 = []
            t2 = []
            s1 = []
            s2 = []
            n = 1

            #TODO make this failsafe
            for key2, ins in dom.iteritems():
                x.append(n)
                n = n + 1
                t1.append(ins['parallel_time'])
                t2.append(ins['relaxed_time'])

                s1.append(ins['parallel_steps'])
                s2.append(ins['relaxed_steps'])
            
            # Plot in subplot
            axes[0,0].set_title(key1)
            axes[0,0].set_xlabel('Instance')
            axes[0,0].set_ylabel('t in s')
            axes[0,1].set_xlabel('Instance')
            axes[0,1].set_ylabel('Steps')

            for k in range(len(x)):
                if k == 0:
                    axes[0,0].bar(x[k]-0.2, t1[k], width=0.4, color='b', align='center',
                        label='parallel')
                    axes[0,0].bar(x[k]+0.2, t2[k], width=0.4, color='g', align='center',
                        label='relaxed')
                else:
                    axes[0,0].bar(x[k]-0.2, t1[k], width=0.4, color='b', align='center')
                    axes[0,0].bar(x[k]+0.2, t2[k], width=0.4, color='g', align='center')

                axes[0,1].bar(x[k]-0.2, s1[k], width=0.4, color='b', align='center')
                axes[0,1].bar(x[k]+0.2, s2[k], width=0.4, color='g', align='center')
                

        
            axes[0,0].legend()
            plt.savefig(r'output/analysis_'+str(key1)+'.png')

if __name__ == '__main__':
    main()
