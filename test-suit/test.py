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

    # Sets of problem domains and instances:

    problems1 = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',7),
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0), # Problem in domain definition. 
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',10),
     ('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     r'pddl_examples\linear\fo_counters_inv\instances',10),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',10),
     ('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     r'pddl_examples\linear\sailing_ln\instances',0), # Problem in domain definition. 
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',3),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',2),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',0),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',4)]

    problems2 = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',0),
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0),
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',2),
     ('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     r'pddl_examples\linear\fo_counters_inv\instances',0),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',0),
     ('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     r'pddl_examples\linear\sailing_ln\instances',0),
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',0),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',0),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',0),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',0)]

    # Specify which to test:
    problems = problems2

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

                print('Now solving: ' + str(domain_name) + ' ' + str(filename))

                # Test parralel search for comparison
                try:
                    start_time = time.time()

                    # Perform the search.
                    print('encoding task....')
                    e = encoder.EncoderSMT(task, modifier.ParallelModifier())
                    print('.... task encoded!')
                    s = search.SearchSMT(e,ub)

                    # Log the behaviour of the search.
                    found, horizon, solution = s.do_linear_search(True)
                    log_metadata = {'mode':'parallel', 'domain':domain_name, 'instance':filename, 'found':found,
                        'horizon':horizon, 'time': (time.time()-start_time)}
                    myReport.create_log(solution, domain_path, instance_path, log_metadata)
                except:
                    myReport.fail_log('parallel' , domain_name, filename)


                # Test relaxed search
                try:
                    start_time = time.time()

                    # Perform the search.
                    e = encoder.EncoderSMT(task, modifier.RelaxedModifier())
                    s = search.SearchSMT(e,ub)
                    found, horizon, solution, time_log = s.do_relaxed_search(True)

                    # Log the behaviour of the search.
                    log_metadata = {'mode':'relaxed', 'domain':domain_name, 'instance':filename, 'found':found,
                        'horizon':horizon, 'time': (time.time()-start_time)}
                    myReport.create_log(solution, domain_path, instance_path, log_metadata)

                    myReport.time_logs[str(domain_name)+ '_' + str(filename) + '_timelog'] = time_log
                except:
                    myReport.fail_log('relaxed', domain_name, filename)
    
    myReport.export()

class Report():

    def __init__(self):
        self.logs = {}
        self.time_logs = {}

    def create_log(self, solution, domain_path, instance_path, log_metadata):
        val = BASE_DIR + val_path
        domain = log_metadata['domain']
        instance = log_metadata['instance']
        mode = log_metadata['mode']

        # Format: {domain : { instance: { mode: {steps: ?, time: ?, found: ?, valid: ?}}}}

        # Create dict of dicts according to above format.
        if not self.logs.has_key(domain):
            self.logs[domain] = {}
        if not self.logs[domain].has_key(instance):
            self.logs[domain][instance] = {}
        if not self.logs[domain][instance].has_key(mode):
            self.logs[domain][instance][mode] = {}
        
        # Insert number of steps in plan
        self.logs[domain][instance][mode]['steps'] = log_metadata['horizon']

        # Time to compute
        self.logs[domain][instance][mode]['time'] = log_metadata['time']

        # Found
        self.logs[domain][instance][mode]['found'] = log_metadata['found']
        self.logs[domain][instance][mode]['valid'] = False #default
        
        # Validate
        try:
            if solution.validate(val, domain_path, instance_path):
                print('Valid plan found! in time: ' + str(log_metadata['time']))
                self.logs[domain][instance][mode]['valid'] = True
            else:
                print('Plan not valid.' + str(domain) + ' , ' + str(instance))
        except:
            print('Exception during plan valitation.' + str(domain) + ' , ' + str(instance))

    def fail_log(self, mode, domain_name, filename):
        print('***************** Fail during search: ' + mode + domain_name + filename)

    def export(self):
        print(self.logs)

        # Here the files will be stored.
        folder = os.path.join(BASE_DIR, r'test-suit/output/analysis_' + str(time.time()))
        try:
            os.makedirs(folder)
        except FileExistsError:
            print('Output directory already exists. Test results cannot be stored properly.')
            print('Exeting ...')
            sys.exit()
        
        # Plot the log
        # Format: {domain : { instance: { mode: {steps: ?, time: ?, found: ?, valid: ?}}}}
        for domain, dom  in self.logs.iteritems():
            # New fig for each domain
            _, axes = plt.subplots(nrows=1, ncols=2, sharex=False, sharey=False, squeeze=False)
            
            # Plot in subplot
            axes[0,0].set_title(domain)
            axes[0,0].set_xlabel('Instance')
            axes[0,0].set_ylabel('t in s')
            axes[0,1].set_xlabel('Instance')
            axes[0,1].set_ylabel('Steps')

            countr_instance = 0

            for _, ins in dom.iteritems():
                countr_mode = 0
                total_width = 0.8

                for mode, data in ins.iteritems():
                    bar_width = total_width / len(ins)
                    position = countr_instance - (total_width/2) + bar_width*countr_mode
                    t = data['time']
                    s = data['steps']

                    # Color of a bar remains black, if the mode is unknown or no valid plan was found.
                    color = 'black'
                    if data['found'] and data['valid'] and mode == 'parallel':
                        color = 'b'
                    elif data['found'] and data['valid'] and mode == 'relaxed':
                        color = 'g'

                    # Bar showing the time needed.
                    if countr_instance == 0:
                        axes[0,0].bar(position, t, width=bar_width, color=color, align='center',
                            label= mode)
                    else :
                        axes[0,0].bar(position, t, width=bar_width, color=color, align='center')

                    # Bar showing the parallel-steps needed.
                    axes[0,1].bar(position, s, width=bar_width, color=color, align='center')
                    
                    countr_mode += 1
                
                countr_instance += 1
            
            axes[0,0].legend()
            plt.savefig(os.path.join(folder, str(domain)+'.png'))

        for instance, timelog in self.time_logs.iteritems():
            width = 0.35
            _, ax = plt.subplots()

            first = True
            bottom = 0
            for label, t in timelog:
                if not first:
                    ax.bar('_', t, width, label=label)
                else :
                    ax.bar('_', t, width, bottom=bottom, label=label)
                bottom += t

            ax.set_ylabel('time in s')
            ax.set_title(instance)
            ax.legend()
            plt.xlim([0, 1])
            plt.savefig(os.path.join(folder, str(instance)+'.png'))


if __name__ == '__main__':
    main()
