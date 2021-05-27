from os import name
from z3 import *
from collections import defaultdict
import translate.pddl as pddl
import utils
from copy import deepcopy
from translate import instantiate
from translate import numeric_axiom_rules
import numpy as np
import loopformula
from planner import modifier



class AgileEncoder():
    """
    Base encoder class. Defines methods to build standard
    state-based encodings -- i.e., Rintanen 09
    """

    def __init__(self, task, modifier, version=1):
        self.task = task
        self.modifier = modifier

        (self.boolean_fluents,
         self.actions,
         self.numeric_fluents,
         self.axioms,
         self.numeric_axioms) = self._ground()

        (self.axioms_by_name,
         self.depends_on,
         self.axioms_by_layer) = self._sort_axioms()

        if self.modifier.__class__.__name__ == "LinearModifier":
            self.mutexes = self._computeSerialMutexes()
        elif self.modifier.__class__.__name__ == "ParallelModifier":
            self.mutexes = self._computeParallelMutexes()
        else:
            self.mutexes = self._computeRelaxedMutexes()
        
        # Initialize variable dicts
        self.boolean_variables = defaultdict(dict)
        self.numeric_variables = defaultdict(dict)
        self.action_variables = defaultdict(dict)

        # Initialize sequentializability-ecoder depending on version
        self.version = version
        if version == 2 :
            self.seq_encoder = deepcopy(self)
            # Actions should not be copied. This allows for set operations.
            self.seq_encoder.actions = self.actions
            self.seq_encoder._init_seq_encoder()

    def _ground(self):
        """
        Grounds action schemas as per TFD parser)
        """

        (relaxed_reachable, boolean_fluents, numeric_fluents, actions,
        durative_actions, axioms, numeric_axioms,
        reachable_action_params) = instantiate.explore(self.task)

        return boolean_fluents, actions, numeric_fluents, axioms, numeric_axioms

    def _sort_axioms(self):
        """!
        Stores numeric axioms sorted according to different criteria.

        Returns 3 dictionaries:

        @return axioms_by_name: numeric axioms sorted by name
        @return depends_on: dependencies between axioms
        @return axioms_by_layer: axioms sorted by layer (see "Using the Context-enhanced Additive Heuristic for Temporal and Numeric Planning.", Eyerich et al.)
        """

        axioms_by_name = {}
        for nax in self.numeric_axioms:
            axioms_by_name[nax.effect] = nax

        depends_on = defaultdict(list)
        for nax in self.numeric_axioms:
            for part in nax.parts:
                depends_on[nax].append(part)

        axioms_by_layer, _,_,_ = numeric_axiom_rules.handle_axioms(self.numeric_axioms)

        return axioms_by_name, depends_on, axioms_by_layer


    def _computeSerialMutexes(self):
        """!
        Computes mutually exclusive actions for serial encodings,
        i.e., all actions are mutually exclusive

        @return mutex: list of tuples defining action mutexes
        """
        # Stores mutexes
        mutexes = []

        for a1 in self.actions:
            for a2 in self.actions:
                # Skip same action
                if not a1.name == a2.name:
                            mutexes.append((a1,a2))

        mutexes = set(tuple(sorted(t)) for t in mutexes)

        return mutexes

    def _computeParallelMutexes(self):
        """!
        Computes mutually exclusive actions:
        Two actions (a1, a2) are mutex if:
            - intersection pre_a1 and eff_a2 (or viceversa) is non-empty
            - intersection between eff_a1+ and eff_a2- (or viceversa) is non-empty
            - intersection between numeric effects is non-empty

        See, e.g., 'A Compilation of the Full PDDL+ Language into SMT'', Cashmore et al.

        @return mutex: list of tuples defining action mutexes
        """
        # Stores mutexes
        mutexes = []

        for a1 in self.actions:
            # Fetch all propositional fluents involved in effects of a1
            add_a1 = set([add[1] for add in a1.add_effects])
            del_a1 = set([de[1] for de in a1.del_effects])
            # fetch all numeric fluents involved in effects of a2
            # need to remove auxiliary fluents added by TFD parser
            num_a1 = set([ne[1].fluent for ne in a1.assign_effects]).union(set([ne[1].expression for ne in a1.assign_effects if not ne[1].expression.symbol.startswith('derived!') ]))

            # Variables in numeric preconditions of a1
            variables_pre = []
            for pre in a1.condition:
                if isinstance(pre,pddl.conditions.FunctionComparison):
                    variables_pre.append(utils.extractVariablesFC(self,pre))

            variables_pre = set([item for sublist in variables_pre for item in sublist])

            for a2 in self.actions:
                # Skip same action
                if not a1.name == a2.name:
                    # Fetch all propositional fluents involved in effects of a2
                    add_a2 = set([add[1] for add in a2.add_effects])
                    del_a2 = set([de[1] for de in a2.del_effects])
                    # fetch all numeric fluents involved in effects of a2
                    # need to remove auxiliary fluents added by TFD parser
                    num_a2 = set([ne[1].fluent for ne in a2.assign_effects]).union(set([ne[1].expression for ne in a2.assign_effects if not ne[1].expression.symbol.startswith('derived!') ]))

                    # Condition 1

                    # for propositional variables
                    if any(el in add_a2 for el in a1.condition):
                            mutexes.append((a1,a2))

                    if any(el in del_a2 for el in a1.condition):
                            mutexes.append((a1,a2))

                    ## for numeric variables

                    variables_eff = []
                    for ne in a2.assign_effects:
                        if isinstance(ne[1],pddl.conditions.FunctionComparison):
                            variables_eff.append(utils.extractVariablesFC(self,ne[1]))

                        else:
                            variables_eff.append(utils.varNameFromNFluent(ne[1].fluent))

                            if ne[1].expression in self.numeric_fluents:
                                variables_eff.append(utils.varNameFromNFluent(ne[1].expression))
                            else:
                                utils.extractVariables(self,self.axioms_by_name[ne[1].expression],variables_eff)

                    variables_eff = set(variables_eff)

                    if variables_pre &  variables_eff:
                            mutexes.append((a1,a2))


                    ## Condition 2
                    if add_a1 & del_a2:
                            mutexes.append((a1,a2))

                    if add_a2 & del_a1:
                            mutexes.append((a1,a2))

                    ## Condition 3
                    if num_a1 & num_a2:
                            mutexes.append((a1,a2))


        mutexes = set(tuple(sorted(t)) for t in mutexes)

        return mutexes

    def _computeRelaxedMutexes(self):
        """!
        Computes mutually exclusive actions, 
        which in the relaxed szenario are currently none.

        @return mutex: an empty list
        """
        # Stores mutexes
        mutexes = []

        return mutexes


    def _init_seq_encoder(self):
        """
        Initializing seq_encoder in version_2.
        """

        # At most each action appears once per parallel step
        last_step = len(self.actions)

        # Define execution semantics
        self.modifier = modifier.LinearModifier()

        # Create all possibly necessary variables
        self.createVariables(last_step)
        
        # Create all possibly necessary action encodings
        self.action_encodings = self.encodeActions(0, last_step)

        # Create all possibly necessary frame-axiom encodings
        #self.frame_encodings = self.encodeFrame(0, last_step)

        # Create all possibly necessary execution-semantic encodings
        #self.execution_encodings = self.encodeExecutionSemantics(0, last_step)


    def createVariables(self,last_step):
        """!
        Creates state and action variables needed in the encoding.
        Variables are stored in dictionaries as follows:

        dict[step][variable_name] = Z3 variable instance

        @param last_step Variables from step 0 until last_step are created.
        """

        # Determine current number of steps and list of steps to be encoded
        next_step = len(self.boolean_variables)
        steps_todo = [i+next_step for i in range(last_step-next_step+1)]

        # Create boolean variables for boolean fluents
        for step in steps_todo:
            # define SMT  variables only for predicates in the PDDL domain,
            # do not consider new atoms added by the SAS+ translation
            for fluent in self.boolean_fluents:
                if isinstance(fluent.predicate,str) and fluent.predicate.startswith('defined!'):
                    continue
                elif isinstance(fluent.predicate,str) and fluent.predicate.startswith('new-'):
                    continue
                else:
                    var_name = utils.varNameFromBFluent(fluent)
                    self.boolean_variables[step][var_name] = Bool('{}_{}'.format(var_name,step))


        # Create arithmetic variables for numeric fluents
        for step in steps_todo:
            for fluent in self.numeric_fluents:
                # skip auxiliary fluents
                if not fluent.symbol.startswith('derived!'):
                    var_name = utils.varNameFromNFluent(fluent)
                    self.numeric_variables[step][var_name] = Real('{}_{}'.format(var_name,step))


        # Create propositional variables for actions
        for step in steps_todo:
            for a in self.actions:
                self.action_variables[step][a.name] = Bool('{}_{}'.format(a.name,step))


    def encodeInitialState(self):
        """!
        Encodes formula defining initial state

        @return initial: Z3 formula asserting initial state
        """

        initial = []

        # Traverse initial facts
        for fact in self.task.init:
            # encode propositional fluents
            if utils.isBoolFluent(fact):
                if not fact.predicate == '=':
                    if fact in self.boolean_fluents:
                        var_name = utils.varNameFromBFluent(fact)
                        initial.append(self.boolean_variables[0][var_name])
            # encode numeric fluents
            elif utils.isNumFluent(fact):
                if fact.fluent in self.numeric_fluents:
                    var_name = utils.varNameFromNFluent(fact.fluent)
                    variable = self.numeric_variables[0][var_name]

                    if fact.symbol == '=':
                        initial.append(variable == fact.expression.value)
                    elif fact.symbol == '<':
                        initial.append(variable < fact.expression.value)
                    elif fact.symbol == '<=':
                        initial.append(variable <= fact.expression.value)
                    elif fact.symbol == '>':
                        initial.append(variable > fact.expression.value)
                    elif fact.symbol == '>=':
                        initial.append(variable >= fact.expression.value)
                    else:
                        raise Exception('Symbol not recognized in initial facts')

                else:
                    # we skip initial facts that do not involve
                    # numeric fluents (after compilation done by TFD)

                    continue

            else:
                raise Exception('Initial condition \'{}\': type \'{}\' not recognized'.format(fact, type(fact)))


        # Close-world assumption: facts not asserted in init formula
        # are assumed to be false

        for variable in self.boolean_variables[0].values():
            if not variable in initial:
                initial.append(Not(variable))

        return initial


    def encodeGoalState(self, goal_state_n):
        """!
        Encodes formula defining goal state

        @return goal: Z3 formula asserting propositional and numeric subgoals
        """

        def _encodePropositionalGoals(goal=None):
            """
            Encodes propositional subgoals.
            """

            propositional_subgoal = []

            # UGLY HACK: we skip atomic propositions that are added
            # to handle numeric axioms by checking names.
            axiom_names = [axiom.name for axiom in self.task.axioms]

            # Doing this as I mmight be calling this method
            # if I find a propositional subgoal in numeric conditions
            # see method below...

            if goal is None:
                goal = self.task.goal

            # Check if goal is just a single atom
            if isinstance(goal, pddl.conditions.Atom):
                if not goal.predicate in axiom_names:
                    if goal in self.boolean_fluents:
                        var_name = utils.varNameFromBFluent(goal)
                        if  goal.negated:
                            propositional_subgoal.append(Not(self.boolean_variables[goal_state_n][var_name]))
                        else:
                            propositional_subgoal.append(self.boolean_variables[goal_state_n][var_name])

            # Check if goal is a conjunction
            elif isinstance(goal,pddl.conditions.Conjunction):
                for fact in goal.parts:
                    var_name = utils.varNameFromBFluent(fact)
                    if  fact.negated:
                        propositional_subgoal.append(Not(self.boolean_variables[goal_state_n][var_name]))
                    else:
                        propositional_subgoal.append(self.boolean_variables[goal_state_n][var_name])

            else:
                raise Exception('Propositional goal condition \'{}\': type \'{}\' not recognized'.format(goal, type(goal)))

            return propositional_subgoal


        def _encodeNumericGoals():
            """
            Encodes numeric subgoals.
            """

            numeric_subgoal = []

            for axiom in self.task.axioms:
                # Check if it's an atomic expression condition
                condition = axiom.condition
                if isinstance(condition, pddl.conditions.FunctionComparison):
                    expression = utils.inorderTraversalFC(self, condition, self.numeric_variables[goal_state_n])
                    numeric_subgoal.append(expression)
                elif isinstance(condition, pddl.conditions.Conjunction):
                    # if instead we have a conjunction
                    for part in condition.parts:
                        ## Apparently boolean subgoal may still end up
                        ## in numeric condition objects...
                        if utils.isBoolFluent(part):
                            propositional_subgoal = _encodePropositionalGoals(part)
                            for sg in propositional_subgoal:
                                numeric_subgoal.append(sg)
                        if isinstance(part,pddl.conditions.FunctionComparison):
                            expression = utils.inorderTraversalFC(self, part, self.numeric_variables[goal_state_n])
                            numeric_subgoal.append(expression)
                else:
                    raise Exception('Numeric goal condition not recognized')
            return numeric_subgoal

        # Build goal formulas
        propositional_subgoal = _encodePropositionalGoals()
        numeric_subgoal = _encodeNumericGoals()
        goal = And(And(propositional_subgoal),And(numeric_subgoal))

        return goal


    def encodeActions(self, first_step, last_step):
        """!
        Encodes universal axioms: each action variable implies its preconditions and effects.

        @param first_step: Encodes actions from step no. first_step.
        @param last_step: Encodes actions til step no. last_step.
        @return actions: dict z3 formulas encoding actions.

        """

        # Initiialize dict for action encoding
        # Format = {action: {step: []}
        action_encodings = {}
        steps_todo = [first_step+i for i in range(last_step-first_step)]

        for action in self.actions:
            action_encodings[action]={}

            for step in steps_todo:
                action_encodings[action][step] = []

                # Encode preconditions
                for pre in action.condition:
                    if utils.isBoolFluent(pre):
                        var_name = utils.varNameFromBFluent(pre)
                        if pre.negated:
                            action_encodings[action][step].append(Implies(self.action_variables[step][action.name],Not(self.boolean_variables[step][var_name])))
                        else:
                            action_encodings[action][step].append(Implies(self.action_variables[step][action.name],self.boolean_variables[step][var_name]))

                    elif isinstance(pre, pddl.conditions.FunctionComparison):
                        expr = utils.inorderTraversalFC(self,pre,self.numeric_variables[step])
                        action_encodings[action][step].append(Implies(self.action_variables[step][action.name],expr))

                    else:
                        raise Exception('Precondition \'{}\' of type \'{}\' not supported'.format(pre,type(pre)))

                # Encode add effects
                for add in action.add_effects:
                    # Check if effect is conditional
                    if len(add[0]) == 0:
                        action_encodings[action][step].append(Implies(self.action_variables[step][action.name],self.boolean_variables[step+1][utils.varNameFromBFluent(add[1])]))
                    else:
                        raise Exception(' Action {} contains add effect not supported'.format(action.name))


                # Encode delete effects
                for de in action.del_effects:
                    # Check if effect is conditional
                    if len(de[0]) == 0:
                        action_encodings[action][step].append(Implies(self.action_variables[step][action.name],Not(self.boolean_variables[step+1][utils.varNameFromBFluent(de[1])])))
                    else:
                        raise Exception(' Action {} contains del effect not supported'.format(action.name))

                # Encode numeric effects
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
                            var_name = utils.varNameFromNFluent(ne.fluent)

                            this_step_variable = self.numeric_variables[step][var_name]
                            next_step_variable = self.numeric_variables[step+1][var_name]

                            # Handle right side

                            if ne.expression in self.numeric_fluents and not ne.expression.symbol.startswith('derived!'): #don't consider variables added by TFD
                                # right side is a simple fluent
                                var_name = utils.varNameFromNFluent(ne.expression)
                                expr = self.numeric_variables[step][var_name]
                            else:
                                # retrieve axioms corresponding to expression
                                numeric_axiom = self.axioms_by_name[ne.expression]
                                # build SMT expression
                                expr = utils.inorderTraversal(self,numeric_axiom, self.numeric_variables[step])


                            if ne.symbol == '=':
                                action_encodings[action][step].append(Implies(self.action_variables[step][action.name], next_step_variable == expr))
                            elif ne.symbol == '+':
                                action_encodings[action][step].append(Implies(self.action_variables[step][action.name], next_step_variable == this_step_variable + expr))
                            elif ne.symbol == '-':
                                action_encodings[action][step].append(Implies(self.action_variables[step][action.name], next_step_variable == this_step_variable - expr))
                            elif ne.symbol == '*':
                                action_encodings[action][step].append(Implies(self.action_variables[step][action.name], next_step_variable == this_step_variable * expr))
                            elif ne.symbol == '/':
                                action_encodings[action][step].append(Implies(self.action_variables[step][action.name], next_step_variable == this_step_variable / expr))
                            else:
                                raise Exception('Operator not recognized')
                        else:

                            raise Exception('Numeric effect {} not supported yet'.format(ne))
                    else:
                        raise Exception('Numeric conditional effects not supported yet')

        return action_encodings


    def encodeFrame(self, first_step, last_step, actions=None):
        """!
        Encode explanatory frame axioms: a predicate retains its value unless
        it is modified by the effects of an action.

        @return frame: list of frame axioms
        """

        if actions is None:
            actions = self.actions

        # Steps to encode:
        steps_todo = [first_step+i for i in range(last_step-first_step)]
        # Format: {step: []}
        frame = {}

        # Create new object and use it as
        # inadmissible value to check if
        # variable exists in dictionary

        sentinel = object()

        for step in steps_todo:
            frame[step] = []

            # Encode frame axioms for boolean fluents
            for fluent in self.boolean_fluents:
                var_name = utils.varNameFromBFluent(fluent)
                fluent_pre = self.boolean_variables[step].get(var_name, sentinel)
                fluent_post = self.boolean_variables[step+1].get(var_name, sentinel)

                # Encode frame axioms only if atoms have SMT variables associated
                if fluent_pre is not sentinel and fluent_post is not sentinel:
                    action_add = []
                    action_del = []

                    for action in actions:
                        add_eff = [add[1] for add in action.add_effects]
                        if fluent in add_eff:
                            action_add.append(self.action_variables[step][action.name])

                        del_eff = [de[1] for de in action.del_effects]
                        if fluent in del_eff:
                            action_del.append(self.action_variables[step][action.name])

                    frame[step].append(Implies(And(Not(fluent_pre),fluent_post),Or(action_add)))
                    frame[step].append(Implies(And(fluent_pre,Not(fluent_post)),Or(action_del)))

            # Encode frame axioms for numeric fluents
            for fluent in self.numeric_fluents:
                fluent_pre = self.numeric_variables[step].get(utils.varNameFromNFluent(fluent), sentinel)
                fluent_post = self.numeric_variables[step+1].get(utils.varNameFromNFluent(fluent), sentinel)

                if fluent_pre is not sentinel and fluent_post is not sentinel:
                    action_num = []

                    for action in actions:
                        num_eff = [ne[1].fluent for ne in action.assign_effects]
                        if fluent in num_eff:
                            action_num.append(self.action_variables[step][action.name])

                    #TODO
                    # Can we write frame axioms for num effects in a more
                    # efficient way?
                    frame[step].append(Or(fluent_post == fluent_pre, Or(action_num)))

        return frame


    def encodeExecutionSemantics(self, first_step, last_step, action_variables = None):
        """!
        Encodes execution semantics as specified by modifier class.

        @return axioms that specify execution semantics.
        """

        if action_variables is None:
            action_variables = self.action_variables
        
        # List of steps
        steps = [first_step+i for i in range(last_step-first_step)]

        if self.modifier.__class__.__name__ == "RelaxedModifier":
            return self.modifier.do_encode_stepwise(action_variables,
                self.boolean_variables, self.numeric_variables,
                self.mutexes, steps)
        try:
            return self.modifier.do_encode_stepwise(action_variables, steps)
        except:
            return self.modifier.do_encode_stepwise(action_variables, self.mutexes, steps)


    def encode_step(self,step):
        """
        Basic method to build bounded encoding.

        """

        raise NotImplementedError

class AgileEncoderSMT(AgileEncoder):
    """
    Class that defines method to build SMT encoding.
    """

    def encode_step(self,step):
        """!
        Builds SMT encoding.

        @param step: step that will be encoded.
        @return formula: dictionary containing subformulas.
        """

        # initialize horizon for backwardscompabtility with plan.py
        self.horizon = step+1

        # Create variables

        self.createVariables(step+1)

        # Start encoding formula

        formula = []

        # Encode universal axioms

        actions = self.encodeActions(step, step+1)
        for _,action_steps in actions.items():
            for _,encoding in action_steps.items():
                formula.append(encoding)
 
        # Encode explanatory frame axioms
               
        frame = self.encodeFrame(step, step+1)
        for _,encoding in frame.items():
            formula.append(encoding)

        # Encode execution semantics (lin/par/rel)

        execution = self.encodeExecutionSemantics(step, step+1)
        for _,encoding in execution.items():
            formula.append(encoding)

        return formula

    def encode_concrete_seq_prefix(self, seq_encoder, init_bool_vars, 
        goal_bool_vars, init_num_vars, goal_num_vars):
        """
        Method for encoding a formula representing the "concrete" sequentializability.
        """

        formula = defaultdict(list)
        # Encode initial state axioms
        initial = []

        # Encode values of numerical variables
        for var_name, val in init_num_vars:
            initial.append(seq_encoder.numeric_variables[0][var_name] == val)

        # Encode values of propositional variables
        for var_name, val in init_bool_vars:
            if is_true(val):
                initial.append(seq_encoder.boolean_variables[0][var_name])
            else:
                initial.append(Not(seq_encoder.boolean_variables[0][var_name]))

        # Encode goal state axioms
        goal = []

        # Encode values of numerical variables
        for var_name, val in goal_num_vars:
            goal.append(seq_encoder.numeric_variables[seq_encoder.horizon][var_name] == val)

        # Encode values of propositional variables
        for var_name, val in goal_bool_vars:
            if is_true(val):
                goal.append(seq_encoder.boolean_variables[seq_encoder.horizon][var_name])
            else:
                goal.append(Not(seq_encoder.boolean_variables[seq_encoder.horizon][var_name]))
       
        # Add both to formula
        formula['initial'] = initial
        formula['goal'] = goal

        return formula

    def encode_general_seq(self, actions):
        """
        Encoding sequentializability of a set of actions, 
        without specifying any state.
        """

        # Start encoding formula
        formula = []

        if self.version == 1:
            # Create a deep copy of self
            # This should save some computation
            # as the 'context' of the problem can largely be reused
            seq_encoder = deepcopy(self)

            # Alter horizon to number of actions
            # Change the set of actions to the subset
            seq_encoder.horizon = len(actions)
            last_step = len(actions)

            seq_encoder.actions = actions
            seq_encoder.modifier = modifier.LinearModifier()
            #TODO check whether this does something relevant
            seq_encoder.mutexes = []

            # Create variables
            seq_encoder.createVariables(last_step)

            # Encode universal axioms
            actions = seq_encoder.encodeActions(0, last_step)
            for _,action_steps in actions.items():
                for _,encoding in action_steps.items():
                    formula.append(encoding)

            # Encode explanatory frame axioms
            frame = seq_encoder.encodeFrame(0, last_step)
            for _,encoding in frame.items():
                formula.append(encoding)

            # Encode linear execution semantics
            execution = seq_encoder.encodeExecutionSemantics(0, last_step)
            for _,encoding in execution.items():
                formula.append(encoding)

            return seq_encoder, formula
        
        elif self.version == 2:

            last_step = len(actions)

            # Needed for concrete-sequential. prefix
            self.seq_encoder.horizon = len(actions)

            # Append execution semantics formula
            for action in actions:
                for step in range(last_step):
                    formula.append(self.seq_encoder.action_encodings[action][step])
            
            # Create new frame-axtiom encodings
            frame = self.seq_encoder.encodeFrame(0, last_step, actions=actions)
            for _,enc in frame.items():
                formula.append(enc)
            
            #TODO improve this
            # Extract only necessary action variables
            action_variables = defaultdict(dict)
            for step in range(last_step):
                for action in actions:
                    action_variables[step][action.name] = self.seq_encoder.action_variables[step][action.name]

            # Encode execution semantic
            execution = self.seq_encoder.encodeExecutionSemantics(0, last_step, action_variables=action_variables)
            for _,encoding in execution.items():
                formula.append(encoding)

            return self.seq_encoder, formula