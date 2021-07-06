import os, sys, time
import copy
import multiprocessing
import signal
import subprocess, threading
import matplotlib.pyplot as plt
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
from natsort import natsorted

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
val_path = '/bin/validate'

sys.path.insert(0, BASE_DIR) 

import translate
import subprocess
import utils
from planner import encoder, agile_encoder, modifier, search

# Timeout per instance in seconds
timeout = 60

# Set upper bound
ub = 100

def main():
    run_comparison()

def run_comparison():
    problems0 = [('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',0,1),
     ('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',0,1)]
    problems1 = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',0,3),
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0,0), # Problem in domain definition. 
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',0,15),
     #('fo_counters_seq', r'pddl_examples\linear\fo_counters_seq\domain.pddl',
     #r'pddl_examples\linear\fo_counters_seq\instances',0,7),
     #('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     #r'pddl_examples\linear\fo_counters_inv\instances',0,10),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',0,10),
     #('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     #r'pddl_examples\linear\sailing_ln\instances',0,0), # Does not seem to be solvable in reasonable time at horizon 24
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',0,2),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',0,2),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',0,3),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',0,4)]

    problems = problems1

    # Create Statistics
    manager = multiprocessing.Manager()
    logs = manager.dict()
    myReport = SparseReport(logs)
    
    for domain_name, domain, instance_dir, lowerbound, upperbound in problems:
        abs_instance_dir = os.path.join(BASE_DIR, instance_dir)

        counter = 0
        for filename in natsorted(os.listdir(abs_instance_dir)):
            if filename.endswith('.pddl') and counter >= lowerbound and counter < upperbound:
                counter+= 1

                print('Solving: '+ filename +' ********************')

                mySpringRoll = SpringrollWrapper()
                mySpringRoll.run_springroll(abs_instance_dir, filename, domain, domain_name, myReport)

                p = multiprocessing.Process(target=relaxed_search_wrapper,
                    args=(abs_instance_dir, filename, domain, domain_name, myReport, 2, 
                        {'Timesteps':0,'UnsatCore':True,'Seq-check':'General'},
                        'Timesteps-Current__UnsatCore-True__Seq-check-General'
                    )
                )
                timeout_wrapper(p)

                '''p = multiprocessing.Process(target=relaxed_search_wrapper,
                    args=(abs_instance_dir, filename, domain, domain_name, myReport, 2, 
                        {'Timesteps':2,'UnsatCore':True,'Seq-check':'FixedOrder'},
                        'Timesteps-Dynamic__UnsatCore-True__Seq-check-FixedOrder'
                    )
                )
                timeout_wrapper(p)

                p = multiprocessing.Process(target=relaxed_search_wrapper,
                    args=(abs_instance_dir, filename, domain, domain_name, myReport, 4, 
                        {'Timesteps':0,'UnsatCore':True,'Seq-check':'Syntactical'},
                        'Timesteps-Current__UnsatCore-True__Seq-check-Syntactical'
                    )
                )
                timeout_wrapper(p)
            
                p = multiprocessing.Process(target=linear_search,
                    args=(abs_instance_dir, filename, domain, domain_name, myReport)
                )
                timeout_wrapper(p)'''

    myReport.export()

def timeout_wrapper(process):
    process.start()
    process.join(timeout)
    # Terminate the search, if unfinished.
    if process.is_alive():
        process.terminate()
        process.join()

def linear_search(dir, filename, domain, domain_name, report):

    instance_path = os.path.join(dir, filename)
    domain_path = os.path.join(BASE_DIR, domain)

    task = translate.pddl.open(instance_path, domain_path)

    print('Now solving: ' + str(domain_name) + ' ' + str(filename))

    #try:
    # Log time consuption of subroutines
    log = Log()

    # Perform the search.
    e = agile_encoder.AgileEncoderSMT(task, modifier.ParallelModifier())
    s = search.SearchSMT(e,ub)
    found, horizon, solution = s.do_linear_incremental_search(analysis=True, log=log)

    # Log the behaviour of the search.
    total_time = log.finish()
    log_metadata = {'mode': 'parallel incremental', 'domain':domain_name, 'instance':filename, 'found':found,
        'horizon':horizon, 'time': total_time, 'time_log': log.export()}
    report.create_log(solution, domain_path, instance_path, log_metadata)

    #except:
    #report.fail_log('parallel incremental', domain_name, filename)

def relaxed_search_wrapper(dir, filename, domain, domain_name, report, encoder_version, options, name):

    instance_path = os.path.join(dir, filename)
    domain_path = os.path.join(BASE_DIR, domain)

    task = translate.pddl.open(instance_path, domain_path)

    print('Now solving: ' + str(domain_name) + ' ' + str(filename))

    #try:

    # Log time consuption of subroutines
    log = Log()

    # Perform the search.
    e = agile_encoder.AgileEncoderSMT(task, modifier.RelaxedModifier(), version=encoder_version)
    s = search.SearchSMT(e,ub)
    log.register('Initializing encoder.')

    found, horizon, solution = s.do_relaxed_search(options, log=log)

    # Log the behaviour of the search.
    total_time = log.finish()
    log_metadata = {'mode': name, 'domain':domain_name, 'instance':filename, 'found':found,
        'horizon':horizon, 'time': total_time, 'time_log': log.export(), 'f_count': e.f_cnt,
        'semantics_f_count': e.semantics_f_cnt}
    report.create_log(solution, domain_path, instance_path, log_metadata)

    #except:

    #    report.fail_log(str(options), domain_name, filename)

class SpringrollWrapper:

    def __init__(self):
        self.process = None
        self.output = None

    def run_springroll(self, dir, filename, domain, domain_name, report):

        instance_path = os.path.join(dir, filename)
        domain_path = os.path.join(BASE_DIR, domain)

        def target():
            if os.name == 'nt':
                self.process = subprocess.Popen(
                    ['java', '-classpath', '\".\\testsuit\\dist\\lib\\antlr-3.4-complete.jar;.\\testsuit\\dist\\lib\\jgraph-5.13.0.0.jar;.\\testsuit\\dist\\lib\\jgrapht-core-0.9.0.jar;.\\testsuit\\dist\\lib\\PPMaJal2.jar;.\\testsuit\dist\\springroll_fixed.jar;\"','runner.SMTHybridPlanner',
                    '-o',domain_path, '-f',instance_path ],
                    shell=True, stdout=subprocess.PIPE)
                self.output = self.process.communicate()[0]
            else:
                print('Calling springroll not yet possible for this os.')

        thread = threading.Thread(target=target)
        start = time.time()
        thread.start()
        end = time.time() - start

        log_metadata = {'mode': 'springrill', 'domain':domain_name, 'instance':filename,
            'found':True, 'horizon':0, 'time': end, 'time_log': None}
        report.create_log(None, domain_path, instance_path, log_metadata)

        thread.join(timeout)
        if thread.is_alive():
            print 'Terminating process (in a brutal way)'
            subprocess.Popen("TASKKILL /F /PID {pid} /T".format(pid=self.process.pid))
            #self.process.terminate()
            thread.join()
        
        print self.process.returncode
        print('OUTPUT START')
        print(self.output)
        print('OUTPUT END')


def run_controlled_test():
    # Sets of problem domains and instances:
    # First file to be included, fist file to be excluded
    problems1 = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',0,1),
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0,0), # Problem in domain definition. 
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',0,15),
     ('fo_counters_seq', r'pddl_examples\linear\fo_counters_seq\domain.pddl',
     r'pddl_examples\linear\fo_counters_seq\instances',0,7),
     ('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     r'pddl_examples\linear\fo_counters_inv\instances',0,10),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',0,10),
     ('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     r'pddl_examples\linear\sailing_ln\instances',0,0), # Does not seem to be solvable in reasonable time at horizon 24
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',0,2),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',0,2),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',0,3),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',0,4)]
    problems2 = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',0,4), 
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0,0),
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',0,5),
     ('fo_counters_seq', r'pddl_examples\linear\fo_counters_seq\domain.pddl',
     r'pddl_examples\linear\fo_counters_seq\instances',0,0),
     ('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     r'pddl_examples\linear\fo_counters_inv\instances',0,0),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',0,0),
     ('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     r'pddl_examples\linear\sailing_ln\instances',0,0),
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',0,0),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',0,0),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',0,0),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',0,0)]
    problems3 = [('zeno-travel-linear', r'pddl_examples\linear\zeno-travel-linear\domain.pddl',
     r'pddl_examples\linear\zeno-travel-linear\instances',0,3),
     ('farmland_ln', r'pddl_examples\linear\farmland_ln\domain.pddl',
     r'pddl_examples\linear\farmland_ln\instances',0,0), # Problem in domain definition. 
     ('fo_counters', r'pddl_examples\linear\fo_counters\domain.pddl',
     r'pddl_examples\linear\fo_counters\instances',0,6),
     ('fo_counters_seq', r'pddl_examples\linear\fo_counters_seq\domain.pddl',
     r'pddl_examples\linear\fo_counters_seq\instances',0,6),
     ('fo_counters_inv', r'pddl_examples\linear\fo_counters_inv\domain.pddl',
     r'pddl_examples\linear\fo_counters_inv\instances',0,6),
     ('fo_counters_rnd', r'pddl_examples\linear\fo_counters_rnd\domain.pddl',
     r'pddl_examples\linear\fo_counters_rnd\instances',0,6),
     ('sailing_ln', r'pddl_examples\linear\sailing_ln\domain.pddl',
     r'pddl_examples\linear\sailing_ln\instances',0,0), # Does not seem to be solvable in reasonable time at horizon 24
     ('tpp', r'pddl_examples\linear\tpp\domain.pddl',
     r'pddl_examples\linear\tpp\instances',0,2),
     ('depots_numeric', r'pddl_examples\simple\depots_numeric\domain.pddl',
     r'pddl_examples\simple\depots_numeric\instances',0,2),
     ('gardening', r'pddl_examples\simple\gardening\domain.pddl',
     r'pddl_examples\simple\gardening\instances',0,2),
     ('rover-numeric', r'pddl_examples\simple\rover-numeric\domain.pddl',
     r'pddl_examples\simple\rover-numeric\instances',0,3)]

    # Define which relaxed planning version should be tested:
    relaxed_planners = [
            #Active, Name, Encoder-version, search-version
            (0, 'relaxed e1 s1', 1, 1),
            (0, 'relaxed e2 s1', 2, 1),
            (0, 'relaxed e2 s2', 2, 2),
            (0, 'relaxed e2 s3', 2, 3), #Unsat core
            (1, 'relaxed e2 s3.1', 2, 31), #uc incremental
            (0, 'relaxed e2 s3.2', 2, 32), #one vs for all ts
            (0, 'relaxed e2 s4', 2, 4),  #Fixed order check
            (0, 'relaxed e3 s1', 3, 1),
            (0, 'relaxed e4 s5', 4, 5) #Syntactical
        ]
    og_planner = 0

    # Specify which to test:
    problems = problems2

    # Create report
    myReport = Report()

    # Set upper bound
    ub = 100
    
    for domain_name, domain, instance_dir, lb_files, ub_files in problems:
        counter = 0
        abs_instance_dir = os.path.join(BASE_DIR, instance_dir)
        #abs_instance_dir = BASE_DIR + instance_dir

        for filename in natsorted(os.listdir(abs_instance_dir)):
            if filename.endswith('.pddl') and counter < ub_files:

                counter = counter +1
                if counter <= lb_files:
                    continue

                instance_path = os.path.join(abs_instance_dir, filename)
                domain_path = os.path.join(BASE_DIR, domain)

                task = translate.pddl.open(instance_path, domain_path)

                print('Now solving: ' + str(domain_name) + ' ' + str(filename))

                # Test parralel incremental search for comparison
                try:
                    if og_planner:
                        log = Log()

                        # Perform the search.
                        e = agile_encoder.AgileEncoderSMT(task, modifier.ParallelModifier())
                        s = search.SearchSMT(e,ub)
                        found, horizon, solution = s.do_linear_incremental_search(analysis=True, log=log)

                        # Log the behaviour of the search.
                        total_time = log.finish()
                        log_metadata = {'mode':'parallel incremental', 'domain':domain_name, 'instance':filename, 'found':found,
                            'horizon':horizon, 'time': total_time, 'time_log':log.export(), 'f_count': e.f_cnt,
                            'semantics_f_count': e.semantics_f_cnt}
                        myReport.create_log(solution, domain_path, instance_path, log_metadata)
                except:
                    myReport.fail_log('parallel incremental' , domain_name, filename)

                for active, mode, encoder_v, search_v in relaxed_planners:
                    if active:
                        try:
                            # Log time consuption of subroutines
                            log = Log()

                            # Perform the search.
                            e = agile_encoder.AgileEncoderSMT(task, modifier.RelaxedModifier(), version=encoder_v)
                            s = search.SearchSMT(e,ub)
                            log.register('Initializing encoder.')

                            found, horizon, solution = s.do_relaxed_search_working(True, log=log, version=search_v)

                            # Log the behaviour of the search.
                            total_time = log.finish()
                            log_metadata = {'mode': mode, 'domain':domain_name, 'instance':filename, 'found':found,
                                'horizon':horizon, 'time': total_time, 'time_log': log.export(), 'f_count': e.f_cnt,
                                'semantics_f_count': e.semantics_f_cnt}
                            myReport.create_log(solution, domain_path, instance_path, log_metadata)

                        except:
                            myReport.fail_log(mode, domain_name, filename)
                
                
                # Log time consuption of subroutines
                log = Log()

                # Perform the search.
                e = agile_encoder.AgileEncoderSMT(task, modifier.RelaxedModifier(), version=4)
                s = search.SearchSMT(e,ub)
                log.register('Initializing encoder.')

                #options = {'UnsatCore': False}
                options = {'Seq-check':'Syntactical'}
                found, horizon, solution = s.do_relaxed_search(options, log=log)

                # Log the behaviour of the search.
                total_time = log.finish()
                log_metadata = {'mode': 'TBA', 'domain':domain_name, 'instance':filename, 'found':found,
                    'horizon':horizon, 'time': total_time, 'time_log': log.export(), 'f_count': e.f_cnt,
                    'semantics_f_count': e.semantics_f_cnt}
                myReport.create_log(solution, domain_path, instance_path, log_metadata)
    
    myReport.export()

class SparseReport():

    def __init__(self, logs):
        self.logs = logs
    
    def create_log(self, solution, domain_path, instance_path, log_metadata):
        val = BASE_DIR + val_path
        domain = log_metadata['domain']
        instance = log_metadata['instance']
        mode = log_metadata['mode']

        #{domain: [[ mode name, time1, time2, ...] , ... ]}
        # Create dict of lists of lists according to above format.
        if not self.logs.has_key(domain):
            self.logs[domain] = []
        local_domain = self.logs[domain]

        mode_log = None
        for v in local_domain:
            if v[0] == mode:
                mode_log = v
        if mode_log is None:
            mode_log = [mode]
            local_domain += [mode_log]
        mode_log.append(log_metadata['time'])

        self.logs[domain] = local_domain

        # Validate
        try:
            if solution.validate(val, domain_path, instance_path):
                print('Valid plan found! in time: ' + str(log_metadata['time']))
            else:
                print('CAUTION! Plan not valid.' + str(domain) + ' , ' + str(instance))
        except:
            print('Exception during plan valitation.' + str(domain) + ' , ' + str(instance))
    
    def export(self):
        
        # Here the files will be stored.
        folder = os.path.join(BASE_DIR, r'testsuit/output/analysis_' + str(time.time()))
        try:
            os.makedirs(folder)
        except FileExistsError:
            print('Output directory already exists. Test results cannot be stored properly.')
            print('Exeting ...')
            sys.exit()
        
        print(self.logs)

        for name, domain in self.logs.items():
            for mode1 in domain:
                for mode2 in domain:
                    if mode1 != mode2:
                        print(str(mode1) + str(mode2))
                        self.scatter_plot(name, mode1, mode2, folder)
                domain.remove(mode1)

    def scatter_plot(self, domain_name, mode1, mode2, folder):

        figure = plt.figure()

        nameA = str(mode1[0])
        modeA = copy.copy(mode1)[1:]
        nameB = str(mode2[0])
        modeB = copy.copy(mode2)[1:]

        maximum = max([max(modeA), max(modeB)])

        if len(modeA) < len(modeB):
            modeA.extend([maximum + 0.2*maximum for i in range(len(modeB) - len(modeA))])
        else:
            modeB.extend([maximum + 0.2*maximum for i in range(len(modeA) - len(modeB))])

        plt.plot([0,maximum],[maximum,maximum])
        plt.plot([maximum,maximum],[0,maximum])
        plt.plot([0,maximum],[0,maximum])

        print(modeA)
        print(modeB)
        plt.scatter(modeA, modeB)
        plt.xlabel(nameA)
        plt.ylabel(nameB)
        plt.savefig(os.path.join(folder, str(domain_name)+'_'+nameA+nameB+'.png'))

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

        # Formula numbers
        self.logs[domain][instance][mode]['f_count'] = log_metadata['f_count']
        self.logs[domain][instance][mode]['semantics_f_count'] = log_metadata['semantics_f_count']

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

        # Create entry for time_log
        # Format: {domain_instance: { mode: time_log}}}

        key = str(domain) + '_' + str(instance)
        if not self.time_logs.has_key(key):
            self.time_logs[key] = {}
        self.time_logs[key][mode] = log_metadata['time_log']

    def fail_log(self, mode, domain_name, filename):
        print('***************** Fail during search: ' + mode + domain_name + filename)

    def export(self):
        print(self.logs)

        # Here the files will be stored.
        folder = os.path.join(BASE_DIR, r'testsuit/output/analysis_' + str(time.time()))
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
            _, axes = plt.subplots(nrows=2, ncols=2, sharex=False, sharey=False, squeeze=True, constrained_layout=True)
            
            # Plot in subplot
            axes[0,0].set_title(domain)
            axes[0,0].set_xlabel('Instance')
            axes[0,0].set_ylabel('t in s')
            axes[0,1].set_xlabel('Instance')
            axes[0,1].set_ylabel('Steps')
            axes[1,0].set_xlabel('Instance')
            axes[1,0].set_ylabel('Basic Subformulas')
            axes[1,1].set_xlabel('Instance')
            axes[1,1].set_ylabel('Learned/Mutex Subformulas')

            countr_instance = 0

            for instance in natsorted(dom.keys()):
                ins = dom[instance]
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
                        color = '#d2a58e'
                    elif data['found'] and data['valid'] and mode == 'parallel incremental':
                        color = '#ff95d5'
                    elif data['found'] and data['valid'] and mode == 'relaxed e1 s1':
                        color = '#eebbf5'
                    elif data['found'] and data['valid'] and mode == 'relaxed e1 s2':
                        color = '#afb5fc'
                    elif data['found'] and data['valid'] and mode == 'relaxed e1 s3':
                        color = '#99ff61'
                    elif data['found'] and data['valid'] and mode == 'relaxed e2 s1':
                        color = '#ffcc99'
                    elif data['found'] and data['valid'] and mode == 'relaxed e2 s2':
                        color = '#bada55'
                    elif data['found'] and data['valid'] and mode == 'relaxed e2 s3':
                        color = '#800020'
                    elif data['found'] and data['valid'] and mode == 'relaxed e2 s3.1':
                        color = '#d2a58e'
                    elif data['found'] and data['valid'] and mode == 'relaxed e2 s3.2':
                        color = '#eebbf5'
                    elif data['found'] and data['valid'] and mode == 'relaxed e3 s1':
                        color = '#fa626d'
                    elif data['found'] and data['valid'] and mode == 'relaxed e3 s2':
                        color = '#f94552'                    
                    elif data['found'] and data['valid'] and mode == 'relaxed e2 s4':
                        color = 'green'
                    elif data['found'] and data['valid'] and mode == 'relaxed e4 s5':
                        color = 'yellow'
                    
                    # Bar showing the time needed.
                    if countr_instance == 0:
                        axes[0,0].bar(position, t, width=bar_width, color=color, align='center',
                            label= mode)
                    else :
                        axes[0,0].bar(position, t, width=bar_width, color=color, align='center')

                    # Bar showing the parallel-steps needed.
                    axes[0,1].bar(position, s, width=bar_width, color=color, align='center')

                    # Bar showing the number of basic formulas needed.
                    axes[1,0].bar(position, data['f_count'], width=bar_width, color=color, align='center')

                    # Bar showing the number of semantics-formulas needed.
                    axes[1,1].bar(position, data['semantics_f_count'], width=bar_width, color=color, align='center')
                    
                    countr_mode += 1
                
                countr_instance += 1
            
            axes[0,0].legend()
            plt.savefig(os.path.join(folder, str(domain)+'.png'))

        for domain_instance, modes in self.time_logs.iteritems():

            # Calculate height and scale.
            min_height = 400
            image_height = 0
            scale = 1
            # This fails if the time log only consists of intervalls of duration 0!
            for mode, time_log in modes.iteritems():
                mode_height = 0
                for _, t in time_log:
                    mode_height += t
                image_height = max(image_height, mode_height)
            if image_height < min_height:
                scale = min_height / image_height

            bar_width = 15
            bar_offset_x = 25
            mode_width = 200
            text_threshold = 5

            image = Image.new('RGBA', (mode_width*len(modes),int(image_height*scale)+10), 'white')
            draw = ImageDraw.Draw(image)

            for mode, time_log in modes.iteritems():
                y = 0
                for _, t in time_log:
                    point1 = (bar_offset_x,y)
                    point2 = (bar_offset_x+bar_width,y+int(t*scale))
                    draw.rectangle((point1,point2),outline='red', fill='#e6e6e6')
                    y += (t*scale)
                y = 0
                for label, t in time_log:
                    if (t*scale) > text_threshold:
                        draw.line(((bar_offset_x+bar_width,y),(bar_offset_x+bar_width+10,y)),fill='black')
                        point1 = (bar_offset_x+bar_width+2,y)
                        draw.multiline_text(point1,label, fill='black', font=ImageFont.truetype("arial"))
                    y += (t*scale)
                
                point1 = (bar_offset_x,y)
                draw.multiline_text(point1,mode, fill='black', font=ImageFont.truetype("arial"))
                
                bar_offset_x += mode_width

            image.save(os.path.join(folder, str(domain_instance)+'.png'),'png')

class Log():

    def __init__(self):
        self.start_time = time.time()
        self.last_time = self.start_time
        self.time_log = []

    def register(self,note):
        self.time_log.append((note,time.time()-self.last_time))
        self.last_time = time.time()
    
    def finish(self):
        curr = time.time()
        fin_time = self.last_time - curr
        self.time_log.append(('Finishing',fin_time))
        return curr-self.start_time

    def export(self):
        return self.time_log

if __name__ == '__main__':

    main()
