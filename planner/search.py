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
from planner import encoder
import utils
import numpy as np


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

    def do_linear_search(self):
        """
        Linear search scheme for SMT encodings with unit action costs.

        Optimal plan is obtained by simple ramp-up strategy
        """

        # Defines initial horizon for ramp-up SMT search

        self.horizon = 1

        print('Start linear search SMT')

        # Build formula until a plan is found or upper bound is reached

        while not self.found and self.horizon < self.ub:
            # Create SMT solver instance
            self.solver = Solver()

            # Build planning subformulas
            formula =  self.encoder.encode(self.horizon)

            # Assert subformulas in solver
            for k,v in formula.items():
                self.solver.add(v)

            # Check for satisfiability
            res = self.solver.check()

            if res == sat:
                self.found = True
            else:
                # Increment horizon until we find a solution
                self.horizon = self.horizon + 1

        # Extract plan from model
        model = self.solver.model()
        self.solution = plan.Plan(model, self.encoder)

        return self.solution

    def do_relaxed_search(self):
        """
        Linear, invariant guided search scheme.
        """

        # Defines initial horizon for ramp-up search

        self.horizon = 1

        print('Start linear, invariant guided search.')

        # Build formula until a plan is found or upper bound is reached

        while not self.found and self.horizon < self.ub:
            # Create SMT solver instance
            self.solver = Solver()

            # Build planning subformulas
            formula =  self.encoder.encode(self.horizon)
            #print('The formula:')
            #print(formula)

            # Assert subformulas in solver
            for k,v in formula.items():
                self.solver.add(v)

            # Check for satisfiability
            res = self.solver.check()

            #TODO this does nothing so far
            while res == sat and not self.found:
                #check sequentialziability
                seq , invariants = self.check_sequentializability()
                if(seq):
                    self.found = True
                    #possibly the plan hast to be extraced here
                else:
                    #make some refinement and add constraint
                    pass
                res = self.solver.check()
                
            if not self.found:
                # Increment horizon until we find a solution
                self.horizon = self.horizon + 1

        # Extract plan from model
        model = self.solver.model()
        self.solution = plan.Plan(model, self.encoder)

        return self.solution

    def check_sequentializability(self):
        seq = True
        invariants = []

        # Extract parallel plan steps from the model
        actionsPerStep = []
        statevarsPerStep = []

        model = self.solver.model()
        for step in range(self.encoder.horizon):
            actionsPerStep.append([])
            statevarsPerStep.append([])
            for action in self.encoder.actions:
                if is_true(model[self.encoder.action_variables[step][action.name]]):
                    actionsPerStep[step].append(action.name)

            for key, var in self.encoder.boolean_variables[step].iteritems():
                var_val = model[self.encoder.boolean_variables[step][key]]
                statevarsPerStep[step].append((var, var_val))

            for key, var in self.encoder.numeric_variables[step].iteritems():
                var_val = model[self.encoder.numeric_variables[step][key]]
                statevarsPerStep[step].append((var, var_val))

        print('Actions:')
        print(actionsPerStep)
        print('States:')
        print(statevarsPerStep)

        for i in range(self.encoder.horizon):
            # Generate forumla eepressing sequentializability
            # For each step
            pass

        return (seq, invariants)


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
