############################################################################
##    This file is part of OMTPlan.
##
##    OMTPlan is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    OMTPlan is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with OMTPlan.  If not, see <https://www.gnu.org/licenses/>.
############################################################################

from z3 import *
from planner import plan
from planner import encoder, agile_encoder
import utils
import numpy as np
import time

COMMENTARY = 1

class Search():
    """
    Base class defining search schemes.
    """

    def __init__(self, encoder,ub):
        self.encoder = encoder
        self.found = False
        self.solution = None
        self.solver = None
        self.ub = ub



class SearchSMT(Search):
    """
    Search class for SMT-based encodings.
    """
class SearchSMT(Search):
    """
    Search class for SMT-based encodings.
    """

    def do_linear_search(self, analysis = False, log = None):
        """
        Linear search scheme for SMT encodings with unit action costs.
        Optimal plan is obtained by simple ramp-up strategy
        """

        # Time log for analysis
        self.last_time = time.time()
        self.time_log = []
        formula_cnt = 0 

        # Defines initial horizon for ramp-up SMT search

        self.horizon = 1

        print('Start linear search SMT')

        # Build formula until a plan is found or upper bound is reached

        while not self.found and self.horizon < self.ub:
            # Create SMT solver instance
            self.solver = Solver()

            # Build planning subformulas
            formula_cnt = 0
            formula =  self.encoder.encode(self.horizon)

            # Analysis
            if(analysis):
                log.register('Formula encoding at horizon: '+ str(self.horizon))

            # Assert subformulas in solver
            for k,v in formula.items():
                formula_cnt += 1
                self.solver.add(v)

            # Check for satisfiability
            res = self.solver.check()

            # Analysis
            if(analysis):
                log.register('Sat-check at horizon: '+ str(self.horizon))

            if res == sat:
                print(self.horizon)
                self.found = True
            else:
                # Increment horizon until we find a solution
                self.horizon = self.horizon + 1

        # Return useful metrics for testsuit
        if(analysis):
            if(self.found):
                # Extract plan from model
                model = self.solver.model()
                self.solution = plan.Plan(model, self.encoder)

            return (self.found, self.horizon, self.solution)

        # Extract plan from model
        model = self.solver.model()
        self.solution = plan.Plan(model, self.encoder)
        
        return self.solution

    def do_linear_incremental_search(self, analysis = False, log = None):
        """
        Linear search scheme for SMT encodings with unit action costs.

        Optimal plan is obtained by simple ramp-up strategy
        """

        # Time log for analysis
        self.last_time = time.time()
        self.time_log = []

        # Defines initial horizon for ramp-up SMT search
        self.horizon = 1
        
        # Create SMT solver instance
        self.solver = Solver()

        # Encode Initial state
        self.encoder.createVariables(0)
        self.solver.add(self.encoder.encodeInitialState())
        self.solver.push()

        print('Start linear search SMT')

        # Build formula until a plan is found or upper bound is reached

        while not self.found and self.horizon < self.ub:

            # Encode next step
            for enc in self.encoder.encode_step(self.horizon-1):
                self.solver.add(enc)
            self.solver.push()

            # Encode goal step
            self.solver.add(self.encoder.encodeGoalState(self.horizon))

            # Analysis
            if(analysis):
                log.register('Formula encoding at horizon: '+ str(self.horizon))

            # Check for satisfiability
            res = self.solver.check()

            # Analysis
            if(analysis):
                log.register('Sat-check at horizon: '+ str(self.horizon))

            if res == sat:
                print(self.horizon)
                self.found = True
            else:
                # Increment horizon until we find a solution
                self.horizon = self.horizon + 1

                # Remove the goal encoding from the solver
                self.solver.pop()

        # Return useful metrics for testsuit
        if(analysis):
            if(self.found):
                # Extract plan from model
                model = self.solver.model()
                self.solution = plan.Plan(model, self.encoder)

            log.register('Exiting search')
            return (self.found, self.horizon, self.solution)

        # Extract plan from model
        model = self.solver.model()
        self.solution = plan.Plan(model, self.encoder)
        
        return self.solution

    def do_relaxed_search(self, options, log = None):
        """
        Invariant guided search scheme.
        """

        # Define default search behaviour.
        if not options.has_key('UnsatCore'):
            options['UnsatCore'] = True
        if not options.has_key('Timesteps'):
            options['Timesteps'] = 0
            # 0 corresponds to all timsteps
            # 1 corresponds to only the corresponding timestep
            # 2 allows for dynamic behaviour
        if not options.has_key('Seq-check'):
            options['Seq-check'] = 'General'
        
        # Defines initial horizon for ramp-up search
        self.horizon = 1

        # Create SMT solver instances
        self.solver = Solver()

        # One solver for seq. tests
        # The solver has to be set up depending on options
        self.local_solver = Solver()
        if options['UnsatCore']:
            self.local_solver.set(unsat_core=True)
        if options['Seq-check'] == 'General':
            # Create dict for bookkeeping
            self.solver_log = {a:-1 for a in self.encoder.actions}
            self.solver_log['MAX'] = -1

        # Encode Initial state
        self.encoder.createVariables(0)
        self.solver.add(self.encoder.encodeInitialState())
        self.solver.push()

        # Create empty plan, to be amended during seq.-tests
        self.plan = {}
        print('Start CEGAR search with options:')
        print('Seq-check:' + str(options['Seq-check']))
        print('Timesteps:' + str(options['Timesteps']))
        print('UnsatCore:' + str(options['UnsatCore']))

        # Build formula until a plan is found or upper bound is reached
        while not self.found and self.horizon < self.ub:

            # Encode next step
            for enc in self.encoder.encode_step(self.horizon-1):
                self.solver.add(enc)

            # Create backtracking mark, for incrementality
            self.solver.push()
        
            # Encode goal step
            goal = self.encoder.encodeGoalState(self.horizon)
            self.solver.add(goal)

            # Analysis
            if not log is None:
                log.register('Initial formula encoding at horizon: '+ str(self.horizon))
            
            # Check for satisfiability
            res = self.solver.check()

            # Check sequentializability and refine search
            # until the current horizion can be precluded
            while res == sat and not self.found:
                # Check the sequentializibility
                seq, invariants, inv_step = False, None, None

                if options['Seq-check'] == 'General':

                    if not self.encoder.version == 2:
                        print('Encoder unsuitable for the selected options.')
                    
                    seq, invariants, inv_step = self._seq_check_orderless(
                        u_core=options['UnsatCore'], log=log)
                
                elif options['Seq-check'] == 'FixedOrder':
                    
                    if not self.encoder.version == 2:
                        print('Encoder unsuitable for the selected options.')
                    
                    seq, invariants, inv_step = self._seq_check_ordered(
                        u_core=options['UnsatCore'], log=log)
                
                elif options['Seq-check'] == 'Syntactical':
                    
                    if not self.encoder.version == 4:
                        print('Encoder unsuitable for the selected options.')
                    
                    seq, invariants, inv_step = self._seq_check_syntactical(
                        log=log)

                if seq:
                    print('Plan fully sequentializable')
                    self.found = True
                else:
                    # Discard the generated plan
                    self.plan = {}

                    # Handle invariant creation, depending on options
                    encoded_invars = []

                    if ((options['Timesteps'] == 2 and str(inv_step) == 'All')
                        or options['Timesteps'] == 0):
                        # Encode invariant for all timesteps

                        # Add constraint for future horizons
                        self.encoder.mutexes.extend(invariants)

                        # Encode invariant for all previous and the current timesteps
                        encoded_invars = self.encoder.modifier.do_encode(
                            self.encoder.action_variables,
                            self.encoder.boolean_variables,
                            self.encoder.numeric_variables,
                            invariants, self.encoder.horizon)

                    elif options['Timesteps'] == 1:
                        # Encode invariant for current timestep
                        encoded_invars = self.encoder.modifier.do_encode_stepwise(
                        self.encoder.action_variables,
                        self.encoder.boolean_variables,
                        self.encoder.numeric_variables,
                        invariants, [inv_step]).values()

                    # Remove the goal encoding
                    self.solver.pop()

                    # Assert the encoded invariant into the solver
                    for v in encoded_invars:
                        self.solver.add(v)
                    self.solver.push()

                    # Analysis
                    if not log is None:
                        log.register('Invariant encoding & assertion.')
                    
                    # Assert the goal encoding before the sat check
                    self.solver.add(goal)
                    res = self.solver.check()

                    # Analysis
                    if not log is None:
                        log.register('Refined sat-check.')
            
            # If no plan canbe found, move to the next horizon
            if not self.found:
                # Remove the goal encoding
                self.solver.pop()

                # Increment the horizon variable
                self.horizon += 1
        
        # Create plan object, if possible.
        if self.found:
            self.solution = plan.Plan(None, None, None, self.plan)

        # Return usefull metrics for analysis purposes
        if not log is None:
            log.register('Exiting search')
            return (self.found, self.horizon, self.solution)
        
        if not self.found:
            print('No plan found within upper bound.')

        return self.solution

    def _seq_check_syntactical(self, log = None):
        
        model = self.solver.model()

        # Extract parallel plan steps from the model
        actionsPerStep = self._extract_actions(model)
        booleanVarsPerStep, numVarsPerStep = self._extract_vars(model)

        # Analysis
        if not log is None:
            log.register('Extract model at horizon '+ str(self.horizon))
        
        # Check for each step
        for step in range(self.encoder.horizon):

            # Compute via a syntactical check whether two
            # two actions interfere
            mutexes = self.encoder.computeLocalParallelMutexes(actionsPerStep[step])

            # Analysis
            if not log is None:
                log.register('Syntax check at step '+ str(step))

            if len(mutexes) != 0:
                invars = [{'actions': [a1,a2]} for (a1,a2) in mutexes]
                return (False, invars, step)

            index = len(self.plan)
            for action in actionsPerStep[step]:
                self.plan[index] = action.name
                index = index +1

        return (True, None, None)

    def _seq_check_orderless(self, u_core = True, log = None):

        model = self.solver.model()

        # Extract parallel plan steps from the model
        actionsPerStep = self._extract_actions(model)
        booleanVarsPerStep, numVarsPerStep = self._extract_vars(model)

        # Analysis
        if not log is None:
            log.register('Extract model at horizon '+ str(self.horizon))
        
        # Check for each step
        for step in range(self.encoder.horizon):

            # Steps containing only one action are trivially seq.
            if(len(actionsPerStep[step]) == 1):
                self.plan[len(self.plan)] = actionsPerStep[step][0].name
                continue

            # Pop seq-prefix, only if asserted before.
            if self.solver_log['MAX'] > -1:
                self.local_solver.pop()
            last_step = len(actionsPerStep[step])
            
            # Encode and assert only the actions needed
            action_formulas, active_actions = self.encoder.encode_general_seq_increment(
                actionsPerStep[step], self.solver_log
            )
            for a in action_formulas:
                self.local_solver.add(a)

            trackers = active_actions.keys()

            exec_formulas, exec_trackers = self.encoder.encode_exec_increment(
                actionsPerStep[step], self.solver_log
            )
            for e in exec_formulas:
                self.local_solver.add(e)

            trackers.extend(exec_trackers)

            self.local_solver.push()

            # Encode Frame
            frame = self.encoder.encodeFrame(0, last_step, actions=actionsPerStep[step])
            for step_enc in frame.values():
                self.local_solver.add(step_enc)
                    
            # Analysis
            if not log is None:
                log.register('Encode seq-form of one step '+ str(step))

            concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix( 
                booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                numVarsPerStep[step], numVarsPerStep[step+1],
                last_step)
        
            for v in concrete_seq_prefix:
                self.local_solver.add(v)

            # Analysis
            if not log is None:
                log.register('Encode seq-prefix of one step '+ str(step))

            # Check for satisfiability
            res = self.local_solver.check(trackers)

            # Analysis
            if not log is None:
                log.register('Check sat of seq-formula '+ str(step))
            
            if not res == sat:

                if u_core:
                    # Checking the unsat core using an incremental solver
                    core = self.local_solver.unsat_core()
                    core_names = {active_actions[a] for a in core if a in active_actions}
                    invar = [a for a in actionsPerStep[step] if a.name in core_names]
                    return (False, [{'actions': invar}], step)
                
                # Default invariant
                return (False, [{'actions': actionsPerStep[step]}], step)
            else:
                local_model = self.local_solver.model()
                self._plan_extraction(local_model, actionsPerStep[step])
        
        return True, None, None

    def _seq_check_ordered(self, u_core = True, log = None):
        # The order is defined in the encoder
        model = self.solver.model()

        # Extract parallel plan steps from the model
        actionsPerStep = self._extract_actions(model)
        booleanVarsPerStep, numVarsPerStep = self._extract_vars(model)

        # Analysis
        if not log is None:
            log.register('Extract model at horizon '+ str(self.horizon))
        
        # Check for each step
        for step in range(self.encoder.horizon):

            # Steps containing only one action are trivially seq.
            if(len(actionsPerStep[step]) == 1):
                self.plan[len(self.plan)] = actionsPerStep[step][0].name
                continue

            last_step = len(actionsPerStep[step])
            general_seq_forumla, trackers = self.encoder.encode_fixed_order_gen_seq(
                actionsPerStep[step]
            )
    
            # Assert subformulas in local solver.
            self.local_solver.reset()
            for v in general_seq_forumla:
                #print(v)
                self.local_solver.add(v)
            
            # Analysis
            if not log is None:
                log.register('Encode & assert general seq-form step '+ str(step))

            # Check general satisfiability
            res = self.local_solver.check(trackers)

            # Analysis
            if not log is None:
                log.register('Check sat of gen. seq-formula '+ str(step))
            
            # For dynamic invariant timesteps
            all = (res != sat)

            if res == sat:
                concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix( 
                    booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                    numVarsPerStep[step], numVarsPerStep[step+1],
                    last_step)
            
                for v in concrete_seq_prefix:
                    #print(v)
                    self.local_solver.add(v)

                # Analysis
                if not log is None:
                    log.register('Encode & assert seq-prefix step '+ str(step))

                # Check general satisfiability
                res = self.local_solver.check(trackers)

                # Analysis
                if not log is None:
                    log.register('Check sat of seq-formula '+ str(step))
            
            if not res == sat:

                if u_core:
                    # Checking the unsat core for fixed order checks
                    invar = []
                    core = set(self.local_solver.unsat_core())
                    for s in range(len(actionsPerStep[step])):
                        for action in actionsPerStep[step]:
                            if self.encoder.action_variables[s][action.name] in core:
                                invar.append(action)
                                break
                    if all:
                        return (False, [{'actions': invar}], 'All')
                    return (False, [{'actions': invar}], step)
                
                # Default invariant
                return (False, [{'actions': actionsPerStep[step]}], step)
            
            else:
                local_model = self.local_solver.model()
                self._plan_extraction(local_model, actionsPerStep[step])
        
        return True, None, None

    def _plan_extraction(self, model, actions):
        index = len(self.plan)
        for seq_step in range(len(actions)):
            for action in actions:
                if is_true(model[self.encoder.action_variables[seq_step][action.name]]):
                    self.plan[index] = action.name
                    index = index +1

    def _extract_actions(self, model):
        """
        Extract actions in parallel plan steps from the model
        """

        actionsPerStep = []
        
        for step in range(self.encoder.horizon):
            actionsPerStep.append([])

            for action in self.encoder.actions:
                if is_true(model[self.encoder.action_variables[step][action.name]]):
                    actionsPerStep[step].append(action)
        
        return actionsPerStep

    def _extract_vars(self, model):
        """
        Extract varibale values in parallel plan steps from the model
        """

        booleanVarsPerStep = []
        numVarsPerStep = []

        for step in range(self.encoder.horizon+1):
            booleanVarsPerStep.append([])
            numVarsPerStep.append([])

            for key, var in self.encoder.boolean_variables[step].iteritems():
                var_val = model[self.encoder.boolean_variables[step][key]]
                booleanVarsPerStep[step].append((key, var_val))

            for key, var in self.encoder.numeric_variables[step].iteritems():
                var_val = model[self.encoder.numeric_variables[step][key]]
                numVarsPerStep[step].append((key, var_val))\
        
        return booleanVarsPerStep, numVarsPerStep

    def do_relaxed_search_working(self, analysis = False, log = None, version = 1):
        """
        Invariant guided search scheme.
        """

        # Defines initial horizon for ramp-up search
        self.horizon = 1

        # Create SMT solver instances
        self.solver = Solver()

        # One solver for seq. tests
        self.local_solver = Solver()
        if version in {3,31,32,4}:
            self.local_solver.set(unsat_core=True)
            # Create dict for bookkeeping
            self.solver_log = {a:-1 for a in self.encoder.actions}
            self.solver_log['MAX'] = -1

        # Encode Initial state
        self.encoder.createVariables(0)
        self.solver.add(self.encoder.encodeInitialState())
        self.solver.push()

        # Create empty plan, to be amended during seq.-tests
        self.plan = {}
        print('Start invariant guided search.')

        # Build formula until a plan is found or upper bound is reached

        while not self.found and self.horizon < self.ub:

            # Encode next step
            for enc in self.encoder.encode_step(self.horizon-1):
                self.solver.add(enc)
            self.solver.push()

            # Encode goal step
            goal = self.encoder.encodeGoalState(self.horizon)
            self.solver.add(goal)

            # Analysis
            if(analysis):
                log.register('Initial formula encoding at horizon: '+ str(self.horizon))

            # Check for satisfiability
            res = self.solver.check()

            # Analysis
            if(analysis):
                log.register('Inital Sat-check at horizon: '+ str(self.horizon))

            while res == sat and not self.found:
                #check sequentializability
                seq, invariant, inv_step = self.check_sequentializability(analysis=analysis, log=log, sv=version)

                if(seq):
                    print('Plan fully sequentializable')
                    self.found = True
                else:
                    # Discard the generated plan
                    self.plan = {}

                    # Invariant handling depends on the search-version
                    if version in {1,31} or str(inv_step) == 'All':
                        # Add constraint for future horizons
                        self.encoder.mutexes.append(invariant)

                        # Encode invariant for all previous timesteps
                        encoded_invars = self.encoder.modifier.do_encode(
                            self.encoder.action_variables,
                            self.encoder.boolean_variables,
                            self.encoder.numeric_variables,
                            [invariant], self.encoder.horizon)
                    
                    elif version in {2,3,32,4}:
                        # Encode invariant only for the current timestep
                        encoded_invars = self.encoder.modifier.do_encode_stepwise(
                            self.encoder.action_variables,
                            self.encoder.boolean_variables,
                            self.encoder.numeric_variables,
                            [invariant], [inv_step]).values()
                    
                    elif version == 5:
                        # Encode all new invariants only for the current timestep
                        encoded_invars = self.encoder.modifier.do_encode_stepwise(
                            self.encoder.action_variables,
                            self.encoder.boolean_variables,
                            self.encoder.numeric_variables,
                            [{'actions': [a1,a2]} for (a1,a2) in invariant], [inv_step]).values()
                    
                    # Analysis
                    if(analysis):
                        log.register('Invariant-encoding')

                    # Remove the goal encoding
                    self.solver.pop()

                    # self.solver.add the encoded invariant
                    for v in encoded_invars:
                        self.solver.add(v)
                        self.encoder.semantics_f_cnt += 1
                    self.solver.push()

                    # Add the goal before sat-check and remove it afterwards
                    self.solver.add(goal)
                    res = self.solver.check()

                    # Analysis
                    if(analysis):
                        log.register('Refined sat-check')
                
            if not self.found:
                
                # Remove the goal encoding
                self.solver.pop()

                # Increment horizon until we find a solution
                self.horizon = self.horizon + 1
        
        # Return useful metrics for testsuit
        if(analysis):
            if(self.found):
                self.solution = plan.Plan(None, None, None, self.plan)

            log.register('Exiting search')
            return (self.found, self.horizon, self.solution)

        if self.found:
            # Create plan object from found plan
            self.solution = plan.Plan(None, None, None, self.plan)
            return self.solution
        else:
            print('No plan found within upper bound.')
            sys.exit()

    def check_sequentializability(self, analysis = False, log= None, sv=1):

        # Extract parallel plan steps from the model
        actionsPerStep = []
        booleanVarsPerStep = []
        numVarsPerStep = []

        model = self.solver.model()
        
        for step in range(self.encoder.horizon):
            actionsPerStep.append([])

            for action in self.encoder.actions:
                if is_true(model[self.encoder.action_variables[step][action.name]]):
                    actionsPerStep[step].append(action)

        for step in range(self.encoder.horizon+1):
            booleanVarsPerStep.append([])
            numVarsPerStep.append([])

            for key, var in self.encoder.boolean_variables[step].iteritems():
                var_val = model[self.encoder.boolean_variables[step][key]]
                booleanVarsPerStep[step].append((key, var_val))

            for key, var in self.encoder.numeric_variables[step].iteritems():
                var_val = model[self.encoder.numeric_variables[step][key]]
                numVarsPerStep[step].append((key, var_val))

        # Analysis
        if(analysis):
            log.register('Extract model at horizon '+ str(self.horizon))

        for step in range(self.encoder.horizon):

            # Steps containing only one action are trivially seq.
            if(len(actionsPerStep[step]) == 1):
                self.plan[len(self.plan)] = actionsPerStep[step][0].name
                continue

            if self.encoder.version == 3:

                # Simulate the execution of the actions.
                seq, plan = self.encoder.simulator.simulate(
                    actionsPerStep[step],
                    numVarsPerStep[step] + booleanVarsPerStep[step],
                    numVarsPerStep[step+1] + booleanVarsPerStep[step+1]
                )

                # Analysis
                if(analysis):
                    log.register('Simulate actions in par. step '+ str(self.horizon))

                # Handle the result of the simulation.
                if not seq:
                    return (False, {'actions': actionsPerStep[step]}, step)
                else:
                    # Insert action sequence into plan
                    for a in plan:
                        self.plan[len(self.plan)] = a
                
            elif self.encoder.version == 4 and sv == 5:

                mutexes = self.encoder.computeLocalParallelMutexes(actionsPerStep[step])
                if len(mutexes) != 0:
                    return(False, mutexes, step)

                index = len(self.plan)
                for action in actionsPerStep[step]:
                    self.plan[index] = action.name
                    index = index +1

            else:
                # Generate forumla expressing sequentializability
                # for each step

                if (self.encoder.version == 1):

                    seq_encoder, general_seq_forumla = self.encoder.encode_general_seq(
                        actionsPerStep[step])
                                    
                    # Analysis
                    if(analysis):
                        log.register('Encode seq-form of one step '+ str(step))
                    
                    concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix_v1(
                        seq_encoder,
                        booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                        numVarsPerStep[step], numVarsPerStep[step+1])
                    
                    # Analysis
                    if(analysis):
                        log.register('Encode seq-prefix of one step '+ str(step))

                    # Assert subformulas in local solver.
                    self.local_solver.reset()

                    for v in concrete_seq_prefix:
                        self.local_solver.add(v)

                    for v in general_seq_forumla:
                        self.local_solver.add(v)

                    # Analysis
                    if(analysis):
                        log.register('Assert subformulas-seq of one step '+ str(step))

                    # Check for satisfiability
                    res = self.local_solver.check()

                elif (self.encoder.version == 2 and (sv == 1 or sv == 2)):

                    last_step = len(actionsPerStep[step])
                    general_seq_forumla = self.encoder.encode_general_seq(
                        actionsPerStep[step])

                    # Analysis
                    if(analysis):
                        log.register('Encode seq-form of one step '+ str(step))

                    concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix( 
                        booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                        numVarsPerStep[step], numVarsPerStep[step+1],
                        last_step)

                    # Analysis
                    if(analysis):
                        log.register('Encode seq-prefix of one step '+ str(step))

                    # Assert subformulas in local solver.
                    self.local_solver.reset()

                    for v in concrete_seq_prefix:
                        self.local_solver.add(v)

                    for v in general_seq_forumla:
                        self.local_solver.add(v)

                    # Analysis
                    if(analysis):
                        log.register('Assert subformulas-seq of one step '+ str(step))
                    
                    # Check for satisfiability
                    res = self.local_solver.check()

                elif (self.encoder.version == 2 and sv == 3):

                    #Track assertions
                    last_step = len(actionsPerStep[step])
                    general_seq_forumla = self.encoder.encode_general_seq_trackable(
                        actionsPerStep[step]
                    )
                    
                    # Analysis
                    if(analysis):
                        log.register('Encode seq-form of one step '+ str(step))

                    concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix(
                        booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                        numVarsPerStep[step], numVarsPerStep[step+1],
                        last_step)
                
                    # Analysis
                    if(analysis):
                        log.register('Encode seq-prefix of one step '+ str(step))

                    # Assert subformulas in local solver.
                    self.local_solver.reset()

                    for v in concrete_seq_prefix:
                        self.local_solver.add(v)

                    trackers = []
                    for p, a in general_seq_forumla:
                        constraint = And(a)
                        self.local_solver.add(Implies(p,constraint))
                        trackers.append(p)

                    # Analysis
                    if(analysis):
                        log.register('Assert subformulas-seq of one step '+ str(step))

                    # Check for satisfiability
                    res = self.local_solver.check(trackers)

                elif (self.encoder.version == 2 and sv in {31,32}):

                    if self.solver_log['MAX'] > -1:
                         self.local_solver.pop()
                    last_step = len(actionsPerStep[step])
                    
                    # Encode and assert only the actions needed
                    action_formulas, active_actions = self.encoder.encode_general_seq_increment(
                        actionsPerStep[step], self.solver_log
                    )
                    for a in action_formulas:
                        self.local_solver.add(a)

                    trackers = active_actions.keys()

                    exec_formulas, exec_trackers = self.encoder.encode_exec_increment(
                        actionsPerStep[step], self.solver_log
                    )
                    for e in exec_formulas:
                        self.local_solver.add(e)

                    trackers.extend(exec_trackers)

                    self.local_solver.push()

                    # Encode Frame
                    frame = self.encoder.encodeFrame(0, last_step, actions=actionsPerStep[step])
                    for step_enc in frame.values():
                        self.local_solver.add(step_enc)
                            
                    # Analysis
                    if(analysis):
                        log.register('Encode seq-form of one step '+ str(step))

                    concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix( 
                        booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                        numVarsPerStep[step], numVarsPerStep[step+1],
                        last_step)
                
                    for v in concrete_seq_prefix:
                        self.local_solver.add(v)

                    # Analysis
                    if(analysis):
                        log.register('Encode seq-prefix of one step '+ str(step))

                    # Check for satisfiability
                    res = self.local_solver.check(trackers)

                elif (self.encoder.version == 2 and sv == 4):

                    last_step = len(actionsPerStep[step])
                    general_seq_forumla, trackers = self.encoder.encode_fixed_order_gen_seq(
                        actionsPerStep[step]
                    )
                    
                    # Analysis
                    if(analysis):
                        log.register('Encode seq-form of one step '+ str(step))

                    # Assert subformulas in local solver.
                    self.local_solver.reset()
                    for v in general_seq_forumla:
                        #print(v)
                        self.local_solver.add(v)

                    # Check general satisfiability
                    res = self.local_solver.check(trackers)
                    #print(self.local_solver.unsat_core())

                    # Analysis
                    if(analysis):
                        log.register('Check sat of gen. seq-formula '+ str(step))
                    all = False
                    if res != sat:
                        all = True
                    if (res == sat):
                        concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix( 
                            booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                            numVarsPerStep[step], numVarsPerStep[step+1],
                            last_step
                        )
                    
                        for v in concrete_seq_prefix:
                            #print(v)
                            self.local_solver.add(v)

                        # Analysis
                        if(analysis):
                           log.register('Encode seq-prefix of one step '+ str(step))

                        # Check general satisfiability
                        res = self.local_solver.check(trackers)

                # Analysis
                if(analysis):
                    log.register('Check sat of seq-formula '+ str(step))

                # If unsat, return the involved actions and values of variables
                # for subsequent invariant generation.
                if not (res == sat):
                    
                    if sv == 3:
                        # Basic variant for checking the unsat core
                        core = self.local_solver.unsat_core()

                        # Create the simple invariant only for actions
                        # invloved in the conflict
                        core_names = {str(a) for a in core}
                        #print(core_names)

                        invar = [a for a in actionsPerStep[step] if a.name in core_names]
                        return (False, {'actions': invar}, step)

                    elif sv in {31,32}:
                        # Checking the unsat core using an incremental solver
                        core = self.local_solver.unsat_core()
                        core_names = {active_actions[a] for a in core if a in active_actions}
                        invar = [a for a in actionsPerStep[step] if a.name in core_names]
                        return (False, {'actions': invar}, step)

                    elif sv == 4:
                        # Checking the unsat core for fixed order checks
                        invar = []
                        core = set(self.local_solver.unsat_core())
                        for s in range(len(actionsPerStep[step])):
                            for action in actionsPerStep[step]:
                                if self.encoder.action_variables[s][action.name] in core:
                                    invar.append(action)
                                    break
                        if all:
                            return (False, {'actions': invar}, 'All')
                        return (False, {'actions': invar}, step)

                    # Default invariant
                    return (False, {'actions': actionsPerStep[step]}, step)

                else:
                    # If sat, the model has to be extracted here to extract a plan
                    index = len(self.plan)
                    model = self.local_solver.model()
                    for seq_step in range(len(actionsPerStep[step])):
                        for action in actionsPerStep[step]:
                            if self.encoder.version == 1:
                                if is_true(model[seq_encoder.action_variables[seq_step][action.name]]):
                                    self.plan[index] = action.name
                                    index = index +1
                            elif self.encoder.version == 2:
                                if is_true(model[self.encoder.action_variables[seq_step][action.name]]):
                                    self.plan[index] = action.name
                                    index = index +1
                    
                    # Analysis
                    if(analysis):
                        log.register('Plan extraction '+ str(step))

        return (True, None, None)


class SearchOMT(Search):
    """
    Search class for OMT-based encodings.
    """

    def computeHorizonSchedule(self):
        """
        Computes horizon schedule given upper bound for search.
        Here percentages are fixed.
        """

        schedule = []
        percentages = [10,15,25,35,50,75,100]

        def percentage(percent, whole):
            return (percent * whole) / 100

        for p in percentages:
            schedule.append(percentage(p,self.ub))

        return schedule


    def do_search(self):
        """
        Search scheme for OMT encodings with unit, constant or state-dependent action costs.
        """

        print('Start search OMT')

        # Try different horizons

        horizon_schedule = self.computeHorizonSchedule()

        # Start building formulae

        for horizon in horizon_schedule:
            print('Try horizon {}'.format(horizon))

            # Create OMT solver instance
            self.solver = Optimize()

            # Build planning subformulas
            formula = self.encoder.encode(horizon)

            # Assert subformulas in solver
            for label, sub_formula in formula.items():

                if label == 'objective':
                    # objective function requires different handling
                    # as per Z3 API
                    objective = self.solver.minimize(sub_formula)
                elif label ==  'real_goal':
                    # we don't want to assert goal formula at horizon
                    # see construction described in related paper
                    pass
                else:
                    self.solver.add(sub_formula)

            print('Checking formula')

            res = self.solver.check()

            # If formula is unsat, the problem does not admit solution
            # see Theorem 1 in related paper

            if res == unsat:
                print('Problem not solvable')

            else:
                # Check if model satisfied concrete goal
                model = self.solver.model()
                opt = model.eval(formula['real_goal'])

                # if formula is sat and G_n is satisfied, solution is optimal
                # see Theorem 2 in related paper

                if opt:
                    self.solution =  plan.Plan(model, self.encoder, objective)
                    break

        return self.solution
