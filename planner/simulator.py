import utils
import translate.pddl as pddl

from z3 import *

class Simulator():

    def __init__(self, encoder, boolean_fluents, numeric_fluents):

        self.encoder = encoder
        
        # Create variables & initialize them with 0/False
        self.variables = {}

        # Create one model, to evaluate terms containing only constants
        solver = Solver()
        solver.add(True)
        solver.check()
        self.model = solver.model()

        # Create boolean variables for boolean fluents

        # define variables only for predicates in the PDDL domain,
        # do not consider new atoms added by the SAS+ translation
        for fluent in boolean_fluents:
            if isinstance(fluent.predicate,str) and fluent.predicate.startswith('defined!'):
                continue
            elif isinstance(fluent.predicate,str) and fluent.predicate.startswith('new-'):
                continue
            else:
                var_name = utils.varNameFromBFluent(fluent)
                self.variables[var_name] = 0


        # Create arithmetic variables for numeric fluents
        for fluent in numeric_fluents:
            # skip auxiliary fluents
            if not fluent.symbol.startswith('derived!'):
                var_name = utils.varNameFromNFluent(fluent)
                self.variables[var_name] = False

    def simulate(self, actions, init_vars, goal_vars):
        """
        Simulate a set of actions.
        """

        # Set initial values of variables.
        for var_name,val in init_vars:
            self.variables[var_name] = val

        plan = []

        for action in actions:

            # Values of the variables in the next step:
            next_state = {}

            # Action enabled
            enabled = True

            # Check preconditions
            for pre in action.condition:
                if utils.isBoolFluent(pre):
                    var_name = utils.varNameFromBFluent(pre)
                    if pre.negated:
                        if self.variables[var_name]:
                            enabled = False
                    else:
                        if self.variables[var_name]:
                            enabled = False

                elif isinstance(pre, pddl.conditions.FunctionComparison):
                    expr = utils.evaluateFC(self.encoder,pre,self.variables)
                    enabled = is_true(self.model.eval(expr))

                else:
                    raise Exception('Precondition \'{}\' of type \'{}\' not supported'.format(pre,type(pre)))

                if enabled:

                    # Append action to potential plan
                    plan.append(action.name)

                    # Execute add effects
                    for add in action.add_effects:
                        # Check if effect is conditional
                        if len(add[0]) == 0:
                            next_state[utils.varNameFromBFluent(add[1])] = True
                        else:
                            raise Exception(' Action {} contains add effect not supported'.format(action.name))


                    # Execute delete effects
                    for de in action.del_effects:
                        # Check if effect is conditional
                        if len(de[0]) == 0:
                            next_state[utils.varNameFromBFluent(add[1])] = False
                        else:
                            raise Exception(' Action {} contains del effect not supported'.format(action.name))

                    # Execute numeric effects
                    for ne in action.assign_effects:
                        # Check if conditional
                        if len(ne[0]) == 0:
                            ne = ne[1]
                            if isinstance(ne, pddl.f_expression.FunctionAssignment):
                                # Num eff that are instance of this class are defined
                                # by the following PDDL keywords: assign, increase, decrease,
                                # scale-up, scale-down

                                # Numeric effects have fluents on the left and either a const, a fluent
                                # or a complex numeric expression on the right

                                # Handle left side
                                # retrieve variable name
                                assigned_var_name = utils.varNameFromNFluent(ne.fluent)

                                # Handle right side

                                # don't consider variables added by TFD
                                if ne.expression in self.encoder.numeric_fluents and not ne.expression.symbol.startswith('derived!'): 
                                    # right side is a simple fluent
                                    var_name = utils.varNameFromNFluent(ne.expression)
                                    expr = self.variables[var_name]
                                else:
                                    # retrieve axioms corresponding to expression
                                    numeric_axiom = self.encoder.axioms_by_name[ne.expression]
                                    # build SMT expression
                                    expr = utils.evaluate(self.encoder, numeric_axiom, self.variables)


                                if ne.symbol == '=':
                                    next_state[assigned_var_name] = self.model.eval(expr)
                                elif ne.symbol == '+':
                                    next_state[assigned_var_name] = self.model.eval(self.variables[assigned_var_name] + expr)
                                elif ne.symbol == '-':
                                    next_state[assigned_var_name] = self.model.eval(self.variables[assigned_var_name] - expr)
                                elif ne.symbol == '*':
                                    next_state[assigned_var_name] = self.model.eval(self.variables[assigned_var_name] * expr)
                                elif ne.symbol == '/':
                                    next_state[assigned_var_name] = self.model.eval(self.variables[assigned_var_name] / expr)
                                else:
                                    raise Exception('Operator not recognized')
                            else:

                                raise Exception('Numeric effect {} not supported yet'.format(ne))
                        else:
                            raise Exception('Numeric conditional effects not supported yet')
                    
                    for k,v in next_state.items():
                        self.variables[k] = v
                    
                    # Check whether the goal state is reached.
                    # TODO check whether performance is better, if only checked once per step
                    reached = True
                    for var_name,val in goal_vars:
                        if not is_true(self.model.eval(self.variables[var_name] == val)):
                            reached = False
                    
                    # Return the plan, if succeeded.
                    if reached:
                        return (True,plan)
        
        return (False,None)
