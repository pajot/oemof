"""
The solph-package contains funtionalities for creating and solving an
optimizaton problem. The problem is created from oemof base classes.
Solph depends on pyomo.

"""
import pyomo.environ as pyomo
from pyomo.core.plugins.transform.relax_integrality import RelaxIntegrality
import oemof.network as on
from oemof.solph import constraints as cblocks
import logging


###############################################################################
#
# Classes
#
###############################################################################

class Flow:

    def __init__(self, *args, **kwargs):
        """
        """
        # TODO: Check if we can inherit form pyomo.core.base.var _VarData
        # then we need to create the var object with
        # pyomo.core.base.IndexedVarWithDomain before any Flow is created.
        # E.g. create the variable in the energy system and populate with
        # information afterwards when creating objects.

        # TODO: Create checks and default values for kwargs.
        # Problem: Where do we get the information for timesteps
        # Idea: pass energysystem-object to flow??? -> not very nice!

        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.actual_value = kwargs.get('actual_value')
        self.nominal_value = kwargs.get('nominal_value')
        self.variable_costs =  kwargs.get('variable_costs')
        self.fixed_costs = kwargs.get('fixed_costs')
        self.summed = kwargs.get('summed')
        self.fixed = kwargs.get('fixed', False)


# TODO: create solph sepcific energysystem subclassed from core energy system
class EnergySystem:

    def __init__(self, *args, **kwargs):
        """
        """
        super().__init__( *args, **kwargs)
        #self.flow_var = IndexedVarWithDomain()

Bus = on.Bus


class Investment:
    """
    """
    def __init__(self, maximum=float('+inf')):
        self.maximum = maximum

class ConversionFactor:
    """
    """
    def __init__(self, value, flows):
        self.value = value
        self.flows = flows

class Sink(on.Sink):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Source(on.Source):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



class LinearTransformer(on.Transformer):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversion_factors = kwargs.get('conversion_factors')



class Storage(on.Transformer):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        overwrite_attribute_warning = (
            '{0} for storage flows will be overwritten.')
        self.nominal_capacity = kwargs.get('nominal_capacity')
        self.nominal_input_capacity_ratio = kwargs.get(
            'nominal_input_capacity_ratio', 0.2)
        # ToDo use warning module von python
        for flow in self.inputs.values():
            if flow.nominal_value is not None:
                logging.warning(overwrite_attribute_warning.format(
                    'nominal output'))
            flow.nominal_value = (self.nominal_input_capacity_ratio *
                self.nominal_capacity)
        self.nominal_output_capacity_ratio = kwargs.get(
            'nominal_input_capacity_ratio', 0.2)
        for flow in self.output.values():
            if flow.nominal_value is not None:
                logging.warning(overwrite_attribute_warning.format(
                    'nominal input'))
            flow.nominal_value = (self.nominal_output_capacity_ratio *
                self.nominal_capacity)
        self.initial_capacity = kwargs.get('initial_capacity', 0)
        self.capacity_loss = kwargs.get('capacity_loss', 0)
        self.inflow_conversion_factor = kwargs.get(
            'inflow_conversion_factor', 1)
        self.outflow_conversion_factor = kwargs.get(
            'outflow_conversion_factor', 1)


###############################################################################
#
# Solph Optimization Models
#
###############################################################################

# TODO: Create Investment model
class ExpansionModel(pyomo.ConcreteModel):
    """ Creates Pyomo model of the energy system.

    Parameters
    ----------
    es : object of Solph - EnergySystem Class

    """
    def __init__(self, es):
        super().__init__()

        self.es = es
        # TODO: Set timeincrement for energy system object
        self.time_increment = 1
        self.periods = 1

        # edges dictionary with tuples as keys and non investment flows as values
        self.non_investment_flows = {
                (str(source), str(target)): source.outputs[target]
                for source in es.nodes
                for target in source.outputs
                if not getattr(source.outputs[target], "investment", False) }


        # pyomo Set for all non - investement flow as tuples
        self.NON_INVESTMET_FLOWS = pyomo.Set(
            initialize=self.non_investment_flows.keys(), ordered=True)


        # edges dictionary with tuples as keys and investment flows as values
        self.investment_flows = {
                (str(source), str(target)): source.outputs[target]
                for source in es.nodes
                for target in source.outputs
                if getattr(source.outputs[target], "investment", False) }


        # pyomo Set for all non - investement flow as tuples
        self.NON_INVESTMENT_FLOWS = pyomo.Set(
            initialize=self.non_investment_flows.keys, ordered=True)

        self.INVESTMENT_FLOWS = pyomo.Set(
            initialize=self.investment_flows.keys(), ordered=True)

        # pyomo set for timesteps of optimization problem
        self.TIMESTEPS = pyomo.Set(initialize=range(len(es.time_idx)),
                                   ordered=True)

        # pyomo set for periods of optimization
        self.PERIOS = pyomo.Set(initialize=range(len(self.periods)))

        # pyomo set for all flows in the energy system graph
        self.FLOWS =  self.NON_INVESTMENT_FLOWS | self.INVESTMENT_FLOWS

        # non-negative pyomo variable for all existing flows in energysystem
        self.flow = pyomo.Var(self.FLOWS, self.TIMESTEPS, self.PERIODS,
                              within=pyomo.NonNegativeReals)

        for (o, i) in self.FLOWS:
            for p in self.PERIOS:
                for t in self.TIMESTEPS:
                    # upper bound of flow variable
                    self.flow[o, i, p, t].set_lb(self.flows[o, i].max[p, t] *
                                                 self.flows[o, i].nominal_value[p])
                    # lower bound of flow variable
                    self.flow[o, i, p, t].set_ub(self.flows[o, i].min[p, t] *
                                              self.flows[o, i].nominal_value)
                    # pre - optimizide value of flow
                    self.flow[o, i, p, t].value = self.flows[o, i].actual_value[p, t]

                    # fix variable if flow is fixed
                    if self.flows[o, i].fix:
                         self.flow[o, i, t].fix()

        # create variables with bounds for investment components
        def _investment_bounds(self, o, i, p):
            return (0, self.flows[o, i].investment.maximum[p])


        if self.investment_flows:
              self.investment = pyomo.Var(self.INVESTMENT_FLOWS, self.PERIODS,
                                          bounds=_investment_bounds,
                                          within=pyomo.NonNegativeReals)





class OperationalModel(pyomo.ConcreteModel):
    """
    All pyomo sets () are UPPERCASE and exclusivey hold strings as indices and
    values. Sets
    """
    def __init__(self, es):
        super().__init__()

        # name of the optimization model
        self.name = 'OperationalModel'

        # TODO : move time-increment to energy system class
        # specified time_increment (time-step width)
        self.time_increment = 2

        self.es = es
        # TODO: Move code below somewhere to grouping in energysystem class (@gnn)
        # remove None key from dictionary to avoid errors
        self.es.groups = {k: v for k, v in self.es.groups.items()
                          if k is not None}

        self.flows = {(str(source), str(target)): source.outputs[target]
                      for source in es.nodes
                      for target in source.outputs}

        # set with all components
        self.COMPONENTS = pyomo.Set(initialize=[str(n)
                                                for n in self.es.nodes])

        # indexed index set for inputs of components (components as indices)
        self.INPUTS = pyomo.Set(self.COMPONENTS, initialize={
            str(c): [str(i) for i in c.inputs.keys()]
                     for c in self.es.nodes if not isinstance(c, on.Source)
            }
        )

        # indexed index set for outputs of components (components as indices)
        self.OUTPUTS = pyomo.Set(self.COMPONENTS, initialize={
            str(c): [str(o) for o in c.outputs.keys()]
                     for c in self.es.nodes if not isinstance(c, on.Sink)
            }
        )


        # pyomo set for timesteps of optimization problem
        self.TIMESTEPS = pyomo.Set(initialize=range(len(es.time_idx)),
                                   ordered=True)

        # pyomo set for all flows in the energy system graph
        self.FLOWS = pyomo.Set(initialize=self.flows.keys(),
                               ordered=True, dimen=2)

        # non-negative pyomo variable for all existing flows in energysystem
        self.flow = pyomo.Var(self.FLOWS, self.TIMESTEPS,
                              within=pyomo.NonNegativeReals)

        # loop over all flows and timesteps to set flow bound / values
        for (o, i) in self.FLOWS:
            for t in self.TIMESTEPS:

                # pre - optimizide value of flow
                self.flow[o, i, t].value = self.flows[o, i].actual_value[t]

                # fix variable if flow is fixed
                if self.flows[o, i].fixed:
                     self.flow[o, i, t].fix()
                     # TODO: Move this if clause somewhere more usefull
                     # just as reminder
                     if self.flow[o, i, t].value  is None:
                         raise ValueError('Can not set fixed value without ' +
                                          'numeric value for actual value')

                # upper bound of flow variable
                if self.flows[o, i].nominal_value is not None:
                    self.flow[o, i, t].setub(self.flows[o, i].max[t] *
                                             self.flows[o, i].nominal_value)
                    # lower bound of flow variable
                    self.flow[o, i, t].setlb(self.flows[o, i].min[t] *
                                             self.flows[o, i].nominal_value)

        # loop over all
        for group in self.es.groups:
            if callable(group):
                # create instance for block
                block = group()
                # add block to model
                self.add_component(str(group), block)
                # create constraints etc. related with block for all nodes
                # in the group
                block._create(nodes=self.es.groups[group])

        # This is for integer problems, migth be usefull but can be moved somewhere else
        # Ignore this!!!
        def relax_problem(self):
            """ Relaxes integer variables to reals of optimization model self
            """
            relaxer = RelaxIntegrality()
            relaxer._apply_to(self)

            return self

###############################################################################
#
# Solph grouping functions
#
###############################################################################
# TODO: Make investment grouping work with (node does not hold 'investment' but the flows do)
def investment_grouping(node):
    if hasattr(node, "investment"):
        return Investment

def constraint_grouping(node):
    if isinstance(node, on.Bus) and 'el' in str(node):
        return cblocks.BusBalance
    #elif isinstance(node, on.Transformer):
    #    return cblocks.LinearRelation



###############################################################################
#
# Examples
#
###############################################################################

if __name__ == "__main__":
    from oemof.core import energy_system as oces

    es = oces.EnergySystem(groupings=[constraint_grouping], time_idx=[1,2,3])


    bel = Bus(label="el")
    bcoal = Bus(label="coalbus")

    so = Source(label="coalsource",
                outputs={bcoal: Flow(max=[None, None, None],
                                     actual_value=[None, None, None],
                                     nominal_value=None)})

    si = Sink(label="sink", inputs={bel: Flow(min=[0, 0, 0],
                                              max=[0.1, 0.2, 0.9],
                                              nominal_value=10, fixed=True,
                                              actual_value=[1, 2, 3])})

    trsf = LinearTransformer(label='trsf', inputs={
                                         bcoal:Flow(min=[0, 0, 0],
                                                    max=[1, 1, 1],
                                                    nominal_value=None,
                                                    actual_value=[None, None, None])},
                             outputs={bel:Flow(min=[0, 0, 0],
                                               max=[1, 1, 1],
                                               nominal_value=10,
                                               actual_value=[None, None, None])})

    om = OperationalModel(es)
    om.objective = pyomo.Objective(expr=1)
    #om.write('problem.lp')



