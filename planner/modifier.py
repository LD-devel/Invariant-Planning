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

class Modifier():
    """
    Modifier class.
    """

    def do_encode(self):
        """
        Basic encoding.
        """
        raise NotImplementedError

class LinearModifier(Modifier):
    """
    Linear modifier, contains method to implement sequential execution semantics.

    """

    def do_encode(self, variables, bound):
        """!
        Encodes sequential execution semantics (i.e., one action per step).

        @param  variables: Z3 variables.
        @param bound: planning horizon.

        @return c: constraints enforcing sequential execution
        """
        c = []

        for step in range(bound):
            pbc = [(var,1) for var in variables[step].values()]
            c.append(PbLe(pbc,1))

        return c
    
    def do_encode_stepwise(self, variables, steps):
        """!
        Encodes sequential execution semantics (i.e., one action per step).

        @param  variables: Z3 variables.
        @param bound: planning horizon.

        @return c: constraints enforcing sequential execution
        """
        c = {}

        for step in steps:
            pbc = [(var,1) for var in variables[step].values()]
            c[step] = PbLe(pbc,1)

        return c
    
    def do_encode_stepwise_list(self, variables, steps):
        """!
        Encodes sequential execution semantics (i.e., one action per step).

        @param  variables: Z3 variables.
        @param bound: planning horizon.

        @return c: constraints enforcing sequential execution
        """
        c = []

        for step in steps:
            pbc = [(var,1) for var in variables[step].values()]
            c.append(PbLe(pbc,1))

        return c

class ParallelModifier(Modifier):
    """
    Parallel modifier, contains method to implement parallel execution semantics.
    """

    def __init__(self):
        # For analysis purposes - Keep track of number of exclusion-encodings =
        self.ex_enc_cnt = 0

    def do_encode(self, variables, mutexes, bound):
        """!
        Encodes parallel execution semantics (i.e., multiple, mutex, actions per step).

        @param  variables: Z3 variables.
        @param mutexes: action mutexes.
        @param bound: planning horizon.

        @return c: constraints enforcing parallel execution
        """
        c = []

        for step in range(bound):
            for pair in mutexes:
                c.append(Or(Not(variables[step][pair[0].name]),Not(variables[step][pair[1].name])))

        # Not incrementing, because this method is only used for the not-incremental encoding
        self.ex_enc_cnt = bound * len(mutexes)

        return c

    def do_encode_stepwise(self, variables, mutexes, steps):
        """!
        Encodes parallel execution semantics (i.e., multiple, mutex, actions per step).

        @param  variables: Z3 variables.
        @param mutexes: action mutexes.
        @param bound: list of steps.

        @return c: constraints enforcing parallel execution
        """
        c = {}

        for step in steps:
            c[step] = []

            for pair in mutexes:
                c[step].append(Or(Not(variables[step][pair[0].name]),Not(variables[step][pair[1].name])))

        self.ex_enc_cnt += len(steps) * len(mutexes)

        return c

class RelaxedModifier(Modifier):
    """
    Relaxed modifier, contains method to implement relaxed parallel execution semantics.
    """

    def __init__(self):
        # For analysis purposes - Keep track of number of exclusion-encodings =
        self.ex_enc_cnt = 0

    # To be used initially at each new horizon
    # and for refinement during sequentialziability check
    def do_encode(self, a_vars, b_vars, n_vars, mutexes, bound):
        """!
        Encodes learned invariants for each step.

        @param a_vars, b_vars, n_vars,: Z3 variables.
        @param mutexes: invariants.
        @param bound: planning horizon.

        @return c: constraints enforcing relaxed parallel execution
        """
        c = []

        # Encode each invariant
        for invar in mutexes:
            for step in range(bound):
                lits = []
                if (invar.has_key('actions')):
                    for a in invar['actions']:
                        lits.append(Not(a_vars[step][a.name]))
                    self.ex_enc_cnt += 1
                if (invar.has_key('b_vars_0')):
                    for b, val in invar['b_vars_0']:
                        if is_true(val):
                            lits.append(Not(b_vars[step][b]))
                        else:
                            lits.append(b_vars[step][b])
                if (invar.has_key('b_vars_1')):
                    for b, val in invar['b_vars_1']:
                        if is_true(val):
                            lits.append(Not(b_vars[step+1][b]))
                        else:
                            lits.append(b_vars[step+1][b])
                if (invar.has_key('n_vars_0')):
                    for n, val in invar['n_vars_0']:
                        lits.append(Not(n_vars[step][n] == val))
                if (invar.has_key('n_vars_1')):
                    for n, val in invar['n_vars_1']:
                        lits.append(Not(n_vars[step+1][n] == val))
                c.append(Or(lits))

        return c

    def do_encode_stepwise(self, a_vars, b_vars, n_vars, mutexes, steps):
        """!
        Encodes learned invariants for each step.

        @param a_vars, b_vars, n_vars,: Z3 variables.
        @param mutexes: invariants - list of dicts.
        @param bound: planning horizon.

        @return c: constraints enforcing relaxed parallel execution
        """
        c = {}

        # Encode each invariant for each step
        for step in steps:
            c[step] = []

            for invar in mutexes:
                lits = []
                if (invar.has_key('actions')):
                    for a in invar['actions']:
                        lits.append(Not(a_vars[step][a.name]))
                    self.ex_enc_cnt += 1
                if (invar.has_key('b_vars_0')):
                    for b, val in invar['b_vars_0']:
                        if is_true(val):
                            lits.append(Not(b_vars[step][b]))
                        else:
                            lits.append(b_vars[step][b])
                if (invar.has_key('b_vars_1')):
                    for b, val in invar['b_vars_1']:
                        if is_true(val):
                            lits.append(Not(b_vars[step+1][b]))
                        else:
                            lits.append(b_vars[step+1][b])
                if (invar.has_key('n_vars_0')):
                    for n, val in invar['n_vars_0']:
                        lits.append(Not(n_vars[step][n] == val))
                if (invar.has_key('n_vars_1')):
                    for n, val in invar['n_vars_1']:
                        lits.append(Not(n_vars[step+1][n] == val))
                c[step].append(Or(lits))

        return c
