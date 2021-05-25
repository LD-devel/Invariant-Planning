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

    def do_linear_search(self, analysis = False):
        """
        Linear search scheme for SMT encodings with unit action costs.
        Optimal plan is obtained by simple ramp-up strategy
        """

        # Time log for analysis
        self.last_time = time.time()
        self.time_log = []

        # Defines initial horizon for ramp-up SMT search

        self.horizon = 1

        print('Start linear search SMT')

        # Build formula until a plan is found or upper bound is reached

        while not self.found and self.horizon < self.ub:
            # Create SMT solver instance
            self.solver = Solver()

            # Build planning subformulas
            formula =  self.encoder.encode(self.horizon)

            # Analysis
            self.time_log.append(('Formula encoding at horizon: '+ str(self.horizon),time.time()-self.last_time))
            self.last_time = time.time()

            # Assert subformulas in solver
            for k,v in formula.items():
                self.solver.add(v)

            # Check for satisfiability
            res = self.solver.check()

            # Analysis
            self.time_log.append(('Sat-check at horizon: '+ str(self.horizon),time.time()-self.last_time))
            self.last_time = time.time()

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

            return (self.found, self.horizon, self.solution, self.time_log)

        # Extract plan from model
        model = self.solver.model()
        self.solution = plan.Plan(model, self.encoder)
        
        return self.solution

    def do_linear_incremental_search(self, analysis = False):
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
            self.time_log.append(('Formula encoding at horizon: '+ str(self.horizon),time.time()-self.last_time))
            self.last_time = time.time()

            # Check for satisfiability
            res = self.solver.check()

            # Analysis
            self.time_log.append(('Sat-check at horizon: '+ str(self.horizon),time.time()-self.last_time))
            self.last_time = time.time()

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

            return (self.found, self.horizon, self.solution, self.time_log)

        # Extract plan from model
        model = self.solver.model()
        self.solution = plan.Plan(model, self.encoder)
        
        return self.solution

    def do_relaxed_search(self, analysis = False):
        """
        Invariant guided search scheme.
        """

        # Time log for analysis
        self.last_time = time.time()
        self.time_log = []

        # Defines initial horizon for ramp-up search
        self.horizon = 1

        # Create SMT solver instance
        self.solver = Solver()

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
            self.time_log.append(('Initial formula encoding at horizon: '+ str(self.horizon),time.time()-self.last_time))
            self.last_time = time.time()

            # Check for satisfiability
            res = self.solver.check()

            # Analysis
            self.time_log.append(('Inital Sat-check at horizon: '+ str(self.horizon),time.time()-self.last_time))
            self.last_time = time.time()

            while res == sat and not self.found:
                #check sequentialziability
                seq , invariant = self.check_sequentializability()

                if(seq):
                    print('Plan fully sequentializable')
                    self.found = True
                    
                else:
                    # Discard the generated plan
                    self.plan = {}

                    # Add constraint for future horizons
                    self.encoder.mutexes.append(invariant)

                    # Encode invariant
                    encoded_invars = self.encoder.modifier.do_encode(
                        self.encoder.action_variables,
                        self.encoder.boolean_variables,
                        self.encoder.numeric_variables,
                        [invariant], self.encoder.horizon)
                    
                    # Analysis
                    self.time_log.append(('Invariant-encoding',time.time()-self.last_time))
                    self.last_time = time.time()

                    # Remove the goal encoding
                    self.solver.pop()

                    # self.solver.add the encoded invariant
                    for v in encoded_invars:
                        self.solver.add(v)
                    self.solver.push()

                    # Add the goal befor sat-check and remove it afterwards
                    self.solver.add(goal)
                    res = self.solver.check()

                    # Analysis
                    self.time_log.append(('Refined sat-check',time.time()-self.last_time))
                    self.last_time = time.time()
                
            if not self.found:
                
                # Remove the goal encoding
                self.solver.pop()

                # Increment horizon until we find a solution
                self.horizon = self.horizon + 1
        
        # Return useful metrics for testsuit
        if(analysis):
            if(self.found):
                # Extract plan from model
                model = self.solver.model()
                self.solution = plan.Plan(None, None, None, self.plan)

            return (self.found, self.horizon, self.solution, self.time_log)

        if self.found:
            # Create plan object from found plan
            self.solution = plan.Plan(None, None, None, self.plan)
            return self.solution
        else:
            print('No plan found within upper bound.')
            sys.exit()

    def check_sequentializability(self):

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
        self.time_log.append(('Extract model at horizon '+ str(self.horizon),time.time()-self.last_time))
        self.last_time = time.time()

        for step in range(self.encoder.horizon):
            # Generate forumla expressing sequentializability
            # for each step
            seq_encoder, general_seq_forumla = self.encoder.encode_general_seq(
                actionsPerStep[step])
            
            local_solver = Solver()

            for v in general_seq_forumla:
                local_solver.add(v)

            concrete_seq_prefix = self.encoder.encode_concrete_seq_prefix(
                seq_encoder, 
                booleanVarsPerStep[step], booleanVarsPerStep[step+1],
                numVarsPerStep[step], numVarsPerStep[step+1])
            
            # Analysis
            self.time_log.append(('Encode seq of one step '+ str(step),time.time()-self.last_time))
            self.last_time = time.time()

            for k,v in concrete_seq_prefix.items():
                local_solver.add(v)

            # Check for satisfiability
            res = local_solver.check()

            # Analysis
            self.time_log.append(('Check sat of seq-formula '+ str(step),time.time()-self.last_time))
            self.last_time = time.time()

            # If unsat, return the involved actions and values of variables
            # for subsequent invariant generation.
            if not (res == sat):
                return (False, {'actions': actionsPerStep[step]})
            else:
                # If sat, the model has to be extracted here to extract a plan
                index = len(self.plan)
                model = local_solver.model()
                for seq_step in range(len(actionsPerStep[step])):
                    for action in actionsPerStep[step]:
                        if is_true(model[seq_encoder.action_variables[seq_step][action.name]]):
                            self.plan[index] = action.name
                            index = index +1
                # Analysis
                self.time_log.append(('Plan extraction '+ str(step),time.time()-self.last_time))
                self.last_time = time.time()

        return (True, None)


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
