import os
import sys

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

    problems = [('pddl_examples\linear\zeno-travel-linear\domain.pddl',
     '.\pddl_examples\linear\zeno-travel-linear\instances\pfile1.pddl')]

    # Set upper bound
    ub = 100
    
    for domain, instance in problems:
        instance_path = os.path.join(BASE_DIR, instance)
        domain_path = os.path.join(BASE_DIR, domain)

        task = translate.pddl.open(instance_path, domain_path)

        # Test parralel search for comparison
        try:
            e = encoder.EncoderSMT(task, modifier.ParallelModifier())
            s = search.SearchSMT(e,ub)
            found, horizon, solution = s.do_linear_search(True)
            create_log('parallel', domain_path, instance_path, found, horizon, solution)
        except:
            fail_log('parallel')


        # Test relaxed search
        try:
            e = encoder.EncoderSMT(task, modifier.ParallelModifier())
            s = search.SearchSMT(e,ub)
            found, horizon, solution = s.do_linear_search(True)
            create_log('relaxed', domain_path, instance_path, found, horizon, solution)
        except:
            fail_log('relaxed')

def create_log(mode, domain, instance, found, horizon, solution):
    val = BASE_DIR + val_path
    print(val)
    if(found):
        try:
            if solution.validate(val, domain, instance):
                print('Valid plan found!')
            else:
                print('Plan not valid.')
        except:
            print('Plan could not be validated')
    else:
        print('No plan found: ' + mode)

def fail_log(mode):
    print('Fail during search: ' + mode)

if __name__ == '__main__':
    main()
