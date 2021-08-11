import os, sys, time
import copy
import multiprocessing, pickle
import subprocess, threading, signal
from natsort import natsorted

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
val_path = '/bin/Validate'

sys.path.insert(0, BASE_DIR) 

import translate
import subprocess
import utils
from planner import encoder, agile_encoder, modifier, search

# Timeout per instance in seconds
timeout = 1800

# Set upper bound
ub = 100

def main():
    run_comparison()
    #run_controlled_test()

def run_comparison():
    problems0 = [('fo_counters', r'pddl_examples/linear/fo_counters/domain.pddl',
     r'pddl_examples/linear/fo_counters/instances',0,3),
     ('zeno-travel-linear', r'pddl_examples/linear/zeno-travel-linear/domain.pddl',
     r'pddl_examples/linear/zeno-travel-linear/instances',0,1)]
    problems1 = [('zeno-travel-linear', r'pddl_examples/linear/zeno-travel-linear/domain.pddl',
     r'pddl_examples/linear/zeno-travel-linear/instances',0,0),#2nd run
     ('farmland_ln', r'pddl_examples/linear/farmland_ln/domain.pddl',
     r'pddl_examples/linear/farmland_ln/instances',0,0),
     ('fo_counters', r'pddl_examples/linear/fo_counters/domain.pddl',
     r'pddl_examples/linear/fo_counters/instances',0,0),#1st run
     ('fo_counters_seq', r'pddl_examples/linear/fo_counters_seq/domain.pddl',
     r'pddl_examples/linear/fo_counters_seq/instances',0,0),
     #('fo_counters_inv', r'pddl_examples/linear/fo_counters_inv/domain.pddl',
     #r'pddl_examples/linear/fo_counters_inv/instances',0,10),
     ('fo_counters_rnd', r'pddl_examples/linear/fo_counters_rnd/domain.pddl',
     r'pddl_examples/linear/fo_counters_rnd/instances',0,0),#1st run
     ('sailing_ln', r'pddl_examples/linear/sailing_ln/domain.pddl',
     r'pddl_examples/linear/sailing_ln/instances',0,0), # Does not seem to be solvable in reasonable time at horizon 24
     ('tpp', r'pddl_examples/linear/tpp/domain.pddl',
     r'pddl_examples/linear/tpp/instances',0,0),#2nd run
     ('depots_numeric', r'pddl_examples/simple/depots_numeric/domain.pddl',
     r'pddl_examples/simple/depots_numeric/instances',0,20),#3rd run
     ('gardening', r'pddl_examples/simple/gardening/domain.pddl',
     r'pddl_examples/simple/gardening/instances',0,20),#3rd run
     ('rover-numeric', r'pddl_examples/simple/rover-numeric/domain.pddl',
     r'pddl_examples/simple/rover-numeric/instances',0,0)]

    problems = problems1

    # Create Statistics
    manager = multiprocessing.Manager()
    result = manager.Queue()
    myReport = SimpleReport()

    for domain_name, domain, instance_dir, lowerbound, upperbound in problems:
        abs_instance_dir = os.path.join(BASE_DIR, instance_dir)

        counter = 0
        for filename in natsorted(os.listdir(abs_instance_dir)):
            if filename.endswith('.pddl') and counter >= lowerbound and counter < upperbound:
                counter+= 1

                print('Solving: '+ filename +' ********************')

                mySpringRoll = SpringrollWrapper()
                mySpringRoll.run_springroll(abs_instance_dir, filename, domain, domain_name, myReport)

                name = 'Timesteps-All__UnsatCore-True__Seq-check-General'
                p = multiprocessing.Process(target=relaxed_search_wrapper,
                    args=(abs_instance_dir, filename, domain, domain_name, 2, 
                        {'Timesteps':0,'UnsatCore':True,'Seq-check':'General'},
                        name, result
                    )
                )
                timeout_wrapper(p, name, domain_name, filename, result, myReport)

                '''name = 'Timesteps-Current__UnsatCore-True__Seq-check-General'
                p = multiprocessing.Process(target=relaxed_search_wrapper,
                    args=(abs_instance_dir, filename, domain, domain_name, 2, 
                        {'Timesteps':1,'UnsatCore':True,'Seq-check':'General'},
                        name, result
                    )
                )
                timeout_wrapper(p, name, domain_name, filename, result, myReport)'''

                '''name = 'Timesteps-Current__UnsatCore-True__Seq-check-Syntactical'
                p = multiprocessing.Process(target=relaxed_search_wrapper,
                    args=(abs_instance_dir, filename, domain, domain_name, 4, 
                        {'Timesteps':1,'UnsatCore':True,'Seq-check':'Syntactical'},
                        name, result
                    )
                )
                timeout_wrapper(p, name, domain_name, filename, result, myReport)'''
            
                name = 'parallel incremental'
                p = multiprocessing.Process(target=linear_search,
                    args=(abs_instance_dir, filename, domain, domain_name, result)
                )
                timeout_wrapper(p, name, domain_name, filename, result, myReport)
                
                name = 'parallel not incremental'
                p = multiprocessing.Process(target=linear_search_old,
                    args=(abs_instance_dir, filename, domain, domain_name, result)
                )
                timeout_wrapper(p, name, domain_name, filename, result, myReport)

                '''name = 'Timesteps-Dynamic__UnsatCore-True__Seq-check-FixedOrder'
                p = multiprocessing.Process(target=relaxed_search_wrapper,
                    args=(abs_instance_dir, filename, domain, domain_name, 2, 
                        {'Timesteps':2,'UnsatCore':True,'Seq-check':'FixedOrder'},
                        name, result
                    )
                )'''
                #timeout_wrapper(p, name, domain_name, filename, result, myReport)

    # Not explicit export call needed for simple logs.
    #myReport.export()

def timeout_wrapper(process, mode, domain_name, instance_name, result, report):
    logged = False
    start_time = time.time()

    process.start()
    process.join(timeout)
    # Terminate the search, if unfinished.
    if process.is_alive():
        process.terminate()
        process.join()
    
    # Log behaviour of the search-proc
    if result.empty():
        val_data = (None, None, None)
        if time.time() - start_time < timeout:
            # Log that the search must have crashed: errorcode time = -2
            log_metadata = {'mode':mode, 'domain':domain_name, 'instance':instance_name, 'found':False,
                'horizon':None, 'time':-2, 'time_log':None}
        else:
            # Log a timeout: errorcode: time = -1
            log_metadata = {'mode':mode, 'domain':domain_name, 'instance':instance_name, 'found':False,
                'horizon':None, 'time':-1, 'time_log':None}
    else:
        val_data, log_metadata = result.get()
    
    report.create_log(val_data, log_metadata)

def linear_search(dir, filename, domain, domain_name, result):

    instance_path = os.path.join(dir, filename)
    domain_path = os.path.join(BASE_DIR, domain)

    task = translate.pddl.open(instance_path, domain_path)

    print('Now solving: ' + str(domain_name) + ' ' + str(filename))

    # Log time consuption of subroutines
    log = Log()

    # Perform the search.
    m = modifier.ParallelModifier()
    e = agile_encoder.AgileEncoderSMT(task, m)
    s = search.SearchSMT(e,ub)
    found, horizon, solution = s.do_linear_incremental_search(analysis=True, log=log)

    # Log the behaviour of the search.
    total_time = log.finish()
    log_metadata = {'mode': 'parallel incremental', 'domain':domain_name, 'instance':filename, 'found':found,
        'horizon':horizon, 'time': total_time, 'time_log': log.export(), 'exclusion_cnt': m.ex_enc_cnt}
    val_data = (solution, domain_path, instance_path)

    # Return the information
    result.put((val_data, log_metadata))

def linear_search_old(dir, filename, domain, domain_name, result):

    instance_path = os.path.join(dir, filename)
    domain_path = os.path.join(BASE_DIR, domain)

    task = translate.pddl.open(instance_path, domain_path)

    print('Now solving: ' + str(domain_name) + ' ' + str(filename))

    # Log time consuption of subroutines
    log = Log()

    # Perform the search.
    m = modifier.ParallelModifier()
    e = encoder.EncoderSMT(task, m)
    s = search.SearchSMT(e,ub)
    found, horizon, solution = s.do_linear_search(analysis=True, log=log)

    # Log the behaviour of the search.
    total_time = log.finish()
    log_metadata = {'mode': 'parallel not incremental', 'domain':domain_name, 'instance':filename, 'found':found,
        'horizon':horizon, 'time': total_time, 'time_log': log.export(), 'exclusion_cnt': m.ex_enc_cnt}
    val_data = (solution, domain_path, instance_path)

    # Return the information
    result.put((val_data, log_metadata))

def relaxed_search_wrapper(dir, filename, domain, domain_name, encoder_version, options, name, result):

    instance_path = os.path.join(dir, filename)
    domain_path = os.path.join(BASE_DIR, domain)

    task = translate.pddl.open(instance_path, domain_path)

    print('Now solving: ' + str(domain_name) + ' ' + str(filename))

    # Log time consuption of subroutines
    log = Log()

    # Perform the search.
    m = modifier.RelaxedModifier()
    e = agile_encoder.AgileEncoderSMT(task, m, version=encoder_version)
    s = search.SearchSMT(e,ub)
    log.register('Initializing encoder.')

    found, horizon, solution = s.do_relaxed_search(options, log=log)

    # Log the behaviour of the search.
    total_time = log.finish()
    log_metadata = {'mode': name, 'domain':domain_name, 'instance':filename, 'found':found,
        'horizon':horizon, 'time': total_time, 'time_log': log.export(), 'f_count': e.f_cnt,
        'semantics_f_count': e.semantics_f_cnt, 'exclusion_cnt': m.ex_enc_cnt}
    val_data = (solution, domain_path, instance_path)

    # Return the information
    result.put((val_data, log_metadata))

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
                # This does not necessarily work on any other os
                cmd = ['java -classpath testsuit/dist/lib/antlr-3.4-complete.jar:testsuit/dist/lib/jgraph-5.13.0.0.jar:testsuit/dist/lib/jgrapht-core-0.9.0.jar:testsuit/dist/lib/PPMaJal2.jar:testsuit/dist/springroll.jar runner.SMTHybridPlanner -o '
                    + domain_path + ' -f ' + instance_path]
                self.process = subprocess.Popen(
                    cmd, shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid)
                self.output = self.process.communicate()[0]

        thread = threading.Thread(target=target)
        start = time.time()
        thread.start()

        thread.join(timeout)
        duration = time.time() - start
        found = False
        if thread.is_alive():
            if os.name == 'nt':
                print 'Terminating process (in a sketchy way)'
                subprocess.Popen("TASKKILL /F /PID {pid} /T".format(pid=self.process.pid))
            else:
                # This does not necessarily work on any os
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            thread.join()
            
            # Log a timeout: errorcode: time = -1
            duration = -1
        else:
            print('OUTPUT START')
            print(self.output)
            print('OUTPUT END')
            if 'Solved: True' in self.output:
                found = True
            elif not ('Solved: False' in self.output):
                # Log a crash: errorcode: time = -2
                duration = -2
            else:
                print('*****************Parameters have to be changed!*****************')
                print('Finished within timeout, without solving.')
                duration = -3
        
        log_metadata = {'mode': 'springroll', 'domain':domain_name, 'instance':filename,
            'found':found, 'horizon':0, 'time':duration, 'time_log': None}
        val_data = (None, domain_path, instance_path)
        report.create_log(val_data, log_metadata)

        print(self.process.returncode)



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
    problems2 = [('zeno-travel-linear', r'pddl_examples/linear/zeno-travel-linear/domain.pddl',
     r'pddl_examples/linear/zeno-travel-linear/instances',0,4), 
     ('farmland_ln', r'pddl_examples/linear/farmland_ln/domain.pddl',
     r'pddl_examples/linear/farmland_ln/instances',0,0),
     ('fo_counters', r'pddl_examples/linear/fo_counters/domain.pddl',
     r'pddl_examples/linear/fo_counters/instances',0,5),
     ('fo_counters_seq', r'pddl_examples/linear/fo_counters_seq/domain.pddl',
     r'pddl_examples/linear/fo_counters_seq/instances',0,0),
     ('fo_counters_inv', r'pddl_examples/linear/fo_counters_inv/domain.pddl',
     r'pddl_examples/linear/fo_counters_inv/instances',0,0),
     ('fo_counters_rnd', r'pddl_examples/linear/fo_counters_rnd/domain.pddl',
     r'pddl_examples/linear/fo_counters_rnd/instances',0,0),
     ('sailing_ln', r'pddl_examples/linear/sailing_ln/domain.pddl',
     r'pddl_examples/linear/sailing_ln/instances',0,0),
     ('tpp', r'pddl_examples/linear/tpp/domain.pddl',
     r'pddl_examples/linear/tpp/instances',0,0),
     ('depots_numeric', r'pddl_examples/simple/depots_numeric/domain.pddl',
     r'pddl_examples/simple/depots_numeric/instances',0,0),
     ('gardening', r'pddl_examples/simple/gardening/domain.pddl',
     r'pddl_examples/simple/gardening/instances',0,0),
     ('rover-numeric', r'pddl_examples/simple/rover-numeric/domain.pddl',
     r'pddl_examples/simple/rover-numeric/instances',0,0)]
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

class SimpleReport():

    def __init__(self):
        self.file_id = str(time.time())
        self.path = os.path.join(BASE_DIR,'testsuit','output','analysis_' + self.file_id +'.rwal')

        # Save initial list, only conaining the timeout for the entire benchmark
        try:
            with open(self.path, 'wb') as output_file:
                    pickle.dump([{'timeout': timeout}], output_file)
        except Exception as e:
            print(e)
            print('Could not create file for export. Aborting...')
            sys.exit()

    def create_log(self, val_data, log_metadata):
        # Load file containing prev log entries, if existing.]
        logs = []
        loaded = True
        try:
            with open(self.path, 'rb') as file:
                logs = pickle.load(file)
        except:
            print('Previous log not found.')
            print('Latest result could not be saved.')
            loaded = False
        
        if(loaded):
            # Validate the plan
            solution, domain_path, instance_path = val_data
            val = BASE_DIR + val_path
            valid = -1
            # Validate
            try:
                if solution.validate(val, domain_path, instance_path):
                    print('Valid plan found! in time: ' + str(log_metadata['time']))
                    valid = 1
                else:
                    print('CAUTION! Plan not valid.' + log_metadata['domain'] + ' , ' + log_metadata['instance'])
                    valid = 0
            except:
                print('Exception during plan valitation.' + log_metadata['domain'] + ' , ' + log_metadata['instance'])

            log_metadata['valid'] = valid
            logs.append(log_metadata)

            # Save file
            try:
                with open(self.path, 'wb') as output_file:
                    pickle.dump(logs, output_file)
            except:
                print('Export failed.')


class SparseReport():

    def __init__(self):
        self.logs = {}
        self.time_logs = {}
    
    def create_log(self, val_data, log_metadata):
        # Unfold the input
        solution, domain_path, instance_path = val_data
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

        # Create entry for time_log
        # Format: {domain_instance: { mode: time_log}}}
        key = str(domain) + '_' + str(instance)
        if not self.time_logs.has_key(key):
            self.time_logs[key] = {}
        self.time_logs[key][mode] = log_metadata['time_log']
    
    def export(self):
        # Convert logs manager.dict into a normal dict
        print(self.logs)

        # The logs of the report will be pickled and stored in a file
        id = str(time.time())
        try:
            path = os.path.join('testsuit','output','analysis_' +id+'.sparse')
            with open(path, 'wb') as output_file:
                pickle.dump((timeout, self.logs), output_file)
        except Exception, e:
            print(e)
            print('Export of logs failed.')
        try:
            path = os.path.join('testsuit','output','analysis_' +id+'.timelog')
            with open(path, 'wb') as output_file:
                pickle.dump((timeout, self.time_logs), output_file)
        except Exception, e:
            print(e)
            print('Export of timelogs failed.')


class Report():

    def __init__(self):
        self.logs = {}
        self.time_logs = {}

    def create_log(self, val_data, log_metadata):
        # Unfold the input
        solution, domain_path, instance_path = val_data
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

        # The logs of the report will be pickled and stored in a file
        try:
            path = os.path.join(BASE_DIR,'testsuit','output','analysis_' + str(time.time())+'.detailed')
            with open(path, 'wb') as output_file:
                pickle.dump((timeout, self.logs, self.time_logs), output_file)
        except:
            print('Export failed.')


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
