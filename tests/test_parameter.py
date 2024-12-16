import pytest
from sdata.parameter import (
    Distribution,
    VariableInt,
    VariableFloat,
    VariableStr,
    DiscreteVariableInt,
    DiscreteVariableFloat,
    DiscreteVariableStr,
    DiscreteVariableBool,
    ParameterSet
)


# Tests für die Distribution-Klasse
def test_distribution_serialization():
    dist = Distribution(name="uniform", param1=1, param2=2)
    dist_dict = dist.to_dict()
    assert dist_dict["name"] == "uniform"
    assert dist_dict["params"]["param1"] == 1

    new_dist = Distribution.from_dict(dist_dict)
    assert new_dist.name == "uniform"
    assert new_dist.params["param1"] == 1


def test_distribution_generate_value():
    dist = Distribution(name="uniform")
    value = dist.generate_value((0, 10))
    assert 0 <= value <= 10


# Tests für die VariableInt-Klasse
def test_variable_int_sampling():
    dist = Distribution(name="uniform")
    var = VariableInt(name="test_int", value=5, bounds=(1, 10), distribution=dist)
    sampled_value = var.sample_value()
    assert 1 <= sampled_value <= 10


def test_variable_int_serialization():
    dist = Distribution(name="uniform")
    var = VariableInt(name="test_int", value=5, bounds=(1, 10), distribution=dist)
    var_dict = var.to_dict()
    assert var_dict["name"] == "test_int"
    assert var_dict["bounds"] == (1, 10)

    new_var = VariableInt.from_dict(var_dict)
    assert new_var.name == "test_int"
    assert new_var.value == 5


# Tests für die VariableFloat-Klasse
def test_variable_float_sampling():
    dist = Distribution(name="uniform")
    var = VariableFloat(name="test_float", value=2.5, bounds=(0.1, 10.5), distribution=dist)
    sampled_value = var.sample_value()
    assert 0.1 <= sampled_value <= 10.5


# Tests für die VariableStr-Klasse
def test_variable_str_sampling():
    var = VariableStr(name="test_str", value="example", bounds=("a", "z"))
    assert var.sample_values(3) == ["example", "example", "example"]


# Tests für die DiscreteVariableInt-Klasse
def test_discrete_variable_int():
    var = DiscreteVariableInt(name="test_discrete_int", value=5, discrete_values=[1, 3, 5, 7])
    sampled_value = var.sample_value()
    assert sampled_value in [1, 3, 5, 7]


# Tests für die DiscreteVariableFloat-Klasse
def test_discrete_variable_float():
    var = DiscreteVariableFloat(name="test_discrete_float", value=2.5, discrete_values=[1.1, 2.2, 3.3])
    sampled_value = var.sample_value()
    assert sampled_value in [1.1, 2.2, 3.3]


# Tests für die DiscreteVariableStr-Klasse
def test_discrete_variable_str():
    var = DiscreteVariableStr(name="test_discrete_str", value="b", discrete_values=["a", "b", "c"])
    sampled_value = var.sample_value()
    assert sampled_value in ["a", "b", "c"]


# Tests für die DiscreteVariableBool-Klasse
def test_discrete_variable_bool():
    var = DiscreteVariableBool(name="test_discrete_bool", value=True)
    sampled_value = var.sample_value()
    assert sampled_value in [True, False]


# Tests für die ParameterSet-Klasse
def test_parameter_set_add_and_get():
    param_set = ParameterSet(name="test_set")
    var1 = VariableInt(name="var1", value=5, bounds=(0, 10))
    var2 = VariableFloat(name="var2", value=2.5, bounds=(1.0, 3.0))

    param_set.add_parameters([var1, var2])
    assert "var1" in param_set
    assert "var2" in param_set

    retrieved_var = param_set["var1"]
    assert retrieved_var.value == 5


def test_parameter_set_serialization():
    param_set = ParameterSet(name="test_set")
    var = VariableInt(name="var", value=10, bounds=(0, 100))
    param_set.set(var)

    json_data = param_set.to_json()
    new_param_set = ParameterSet.from_json(json_data)

    assert "var" in new_param_set
    assert new_param_set["var"].value == 10
