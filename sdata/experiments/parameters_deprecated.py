import json
from typing import Dict, Optional, Tuple, List, Union
import random


class Distribution:
    def __init__(self, name: str, **params):
        """
        Unified distribution object to encapsulate name and _parameter.

        :param name: Name of the distribution (e.g., 'normal', 'uniform').
        :param params: Parameters specific to the distribution.
        """
        self.name = name
        self.params = params

    def to_dict(self) -> Dict:
        """Convert the distribution to a dictionary."""
        return {
            "name": self.name,
            "params": self.params
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Create a Distribution instance from a dictionary."""
        return cls(name=data["name"], **data.get("params", {}))

    def generate_value(self, range: Union[Tuple[float, float], List[Union[int, str]]]) -> Union[float, int, str]:
        """
        Generate a value based on the distribution within the specified range.

        :param range: Tuple specifying the minimum and maximum values or a list of discrete options.
        :return: Generated value.
        """
        if isinstance(range, list):
            return random.choice(range)

        min_val, max_val = range

        if self.name == "normal":
            mean = self.params.get("mean", (min_val + max_val) / 2)
            std_dev = self.params.get("std_dev", (max_val - min_val) / 6)
            return max(min(random.gauss(mean, std_dev), max_val), min_val)

        elif self.name == "truncated_gauss":
            mean = self.params.get("mean", (min_val + max_val) / 2)
            std_dev = self.params.get("std_dev", (max_val - min_val) / 6)
            value = random.gauss(mean, std_dev)
            while not (min_val <= value <= max_val):
                value = random.gauss(mean, std_dev)
            return value

        elif self.name == "weibull":
            scale = self.params.get("scale", (max_val - min_val) / 2)
            shape = self.params.get("shape", 1.5)
            return max(min(min_val + random.weibullvariate(scale, shape), max_val), min_val)

        elif self.name == "uniform":
            return random.uniform(min_val, max_val)

        elif self.name == "exponential":
            rate = self.params.get("rate", 1.0)
            return max(min_val, min(random.expovariate(rate), max_val))

        elif self.name == "lognormal":
            mean = self.params.get("mean", (min_val + max_val) / 2)
            sigma = self.params.get("sigma", (max_val - min_val) / 6)
            return max(min_val, min(random.lognormvariate(mean, sigma), max_val))

        elif self.name == "beta":
            alpha = self.params.get("alpha", 2.0)
            beta = self.params.get("beta", 5.0)
            return min_val + (random.betavariate(alpha, beta) * (max_val - min_val))

        elif self.name == "gamma":
            shape = self.params.get("shape", 2.0)
            scale = self.params.get("scale", 1.0)
            return max(min_val, min(random.gammavariate(shape, scale), max_val))

        elif self.name == "cauchy":
            location = self.params.get("location", (min_val + max_val) / 2)
            scale = self.params.get("scale", (max_val - min_val) / 4)
            value = random.uniform(location - scale, location + scale)
            return max(min_val, min(value, max_val))

        else:
            raise ValueError(f"Unsupported distribution: {self.name}")


class Parameter:
    def __init__(self, name: str,
                 value: Union[float, int, str],
                 range: Optional[Union[Tuple[float, float], List[Union[int, str]]]] = None,
                 distribution: Optional[Distribution] = None,
                 type: Optional[str] = None,
                 description: Optional[str] = None,
                 discrete_values: Optional[List[Union[int, str]]] = None,
                 constant: Optional[bool] = False, ):
        """
        Unified class for a parameter.

        :param name: Name of the parameter
        :param value: Value of the parameter
        :param range: Range of the parameter (tuple or list, required for Variables or DiscreteVariables)
        :param distribution: Distribution object for the parameter (optional)
        :param type: Type of the parameter ("Constant", "Variable", or "DiscreteVariable")
        :param description: Description of the parameter (optional)
        :param discrete_values: Discrete values for "DiscreteVariable" type (optional)
        """
        self.name = name
        self.value = value
        self.range = range
        self.distribution = distribution
        self.description = description
        self.discrete_values = discrete_values
        self.constant = constant

        if type:
            self.type = type
        else:
            if range is not None and isinstance(range, list):
                self.type = "DiscreteVariable"
                self.discrete_values = range
                self.range = None
            elif range is not None:
                self.type = "Variable"
            else:
                self.type = "Constant"

        if self.type == "Variable" and not self.distribution:
            self.distribution = Distribution("uniform")

    @property
    def min(self):
        if isinstance(self.range, (list, tuple)):
            return self.range[0]
        raise ValueError("min is only available for continuous ranges")

    @property
    def max(self):
        if isinstance(self.range, (list, tuple)):
            return self.range[1]
        raise ValueError("max is only available for continuous ranges")

    def set_type(self, new_type: str):
        """
        Change the type of the parameter to "Constant", "Variable", or "DiscreteVariable".

        :param new_type: The new type to set ("Constant", "Variable", or "DiscreteVariable").
        """
        if new_type not in ["Constant", "Variable", "DiscreteVariable"]:
            raise ValueError("Type must be 'Constant', 'Variable', or 'DiscreteVariable'")

        self.type = new_type

        if self.type == "Constant":
            self.range = None
            self.distribution = None
            self.discrete_values = None
        elif self.type == "Variable" and not self.distribution:
            self.distribution = Distribution("uniform")
            self.discrete_values = None
        elif self.type == "DiscreteVariable":
            self.range = None

    def to_dict(self) -> Dict:
        """Convert the parameter to a dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "range": self.range,
            "type": self.type,
            "description": self.description,
            "discrete_values": self.discrete_values,
            "distribution": self.distribution.to_dict() if self.distribution else None
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Create a Parameter instance from a dictionary."""
        distribution = None
        if data.get("distribution"):
            distribution = Distribution.from_dict(data["distribution"])
        return cls(
            name=data["name"],
            value=data["value"],
            range=data.get("range"),
            distribution=distribution,
            type=data.get("type"),
            description=data.get("description"),
            discrete_values=data.get("discrete_values")
        )

    def to_json(self) -> str:
        """Serialize the parameter to a JSON string."""
        return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def from_json(cls, json_str: str):
        """Create a Parameter instance from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def sample_value(self) -> Union[float, int, str]:
        """
        Sample and update the value based on the defined distribution.
        """
        if self.type == "Constant":
            return self.value
        elif self.type == "DiscreteVariable":
            self.value = random.choice(self.discrete_values)
            return self.value
        self.value = self.distribution.generate_value(self.range)
        return self.value

    def sample_values(self, n: int) -> List[Union[float, int, str]]:
        """
        Generate n sampled values based on the defined distribution.
        """
        if self.type == "Constant":
            return [self.value] * n
        elif self.type == "DiscreteVariable":
            return [random.choice(self.discrete_values) for _ in range(n)]
        return [self.distribution.generate_value(self.range) for _ in range(n)]

    def __repr__(self):
        try:
            value_range = f"{self.min:.2g},{self.max:.2g}"
        except:
            if self.discrete_values and len(self.discrete_values) > 4:
                value_range = self.discrete_values[:4] + ["..."]
            elif self.discrete_values:
                value_range = self.discrete_values
            else:
                value_range = "None"
        return f"({self.name}|{self.value}|[{value_range}]|{self.type})"

    def __str__(self):
        return self.__repr__()


class ParameterSet:
    def __init__(self, name=None):
        """
        ParameterSet class to hold multiple _parameter in a dictionary.
        """
        self.name = name or "N.N."
        self._parameter = {}

    @property
    def parameters(self):
        return self._parameter

    def update(self, parameter_list):
        """

        """
        for parameter in parameter_list:
            self._parameter[parameter.name] = parameter

    def __getitem__(self, name):
        return self.get(name)

    def __contains__(self, item):
        return item in self._parameter.keys()

    def pop(self, pname):
        try:
            return self._parameter.pop(pname)
        except KeyError as exp:
            return None

    def __iter__(self):
        for x in self._parameter.values():
            yield x

    def items(self):
        """
        Provide a dict-like items view for parameters.

        :return: Items view of parameters.
        """
        return self._parameter.items()

    def keys(self):
        """
        Provide a dict-like keys view for parameters.

        :return: Keys view of parameters.
        """
        return self._parameter.keys()

    def values(self):
        """
        Provide a dict-like values view for parameters.

        :return: Values view of parameters.
        """
        return self._parameter.values()

    def get(self, name, default=None):
        if self._parameter.get(name) is not None:
            return self._parameter.get(name)
        else:
            return default
    def set(self, parameter: Parameter):
        """
        Add a parameter to the set.

        :param parameter: A Parameter object to add.
        """
        self._parameter[parameter.name] = parameter

    def add_parameters(self, parameter_list: List):
        """
        Add a parameter to the set.

        :param parameter: A Parameter object to add.
        """
        for parameter in parameter_list:
            self._parameter[parameter.name] = parameter

    def to_dict(self) -> Dict[str, Dict]:
        """
        Convert the entire parameter set to a dictionary.

        :return: A dictionary of parameter dictionaries.
        """
        d = {"name": self.name}
        d["parameter"] = {pname: param.to_dict() for pname, param in self._parameter.items()}
        return d

    @classmethod
    def from_dict(cls, data: Dict):
        """
        Create a ParameterSet instance from a dictionary.

        :param data: A dictionary containing parameter set data.
        :return: A ParameterSet instance.
        """
        instance = cls(name=data.get("name", "N.N."))
        parameters = data.get("parameter", {})
        for pname, param_data in parameters.items():
            parameter = Parameter.from_dict(param_data)  # Assuming Parameter has a from_dict method
            instance.set(parameter)
        return instance

    def to_json(self) -> str:
        """
        Convert the ParameterSet to a JSON string.

        :return: JSON string representation of the ParameterSet.
        """
        import json
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        """
        Create a ParameterSet instance from a JSON string.

        :param json_str: JSON string containing parameter set data.
        :return: A ParameterSet instance.
        """
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)

    def print(self):
        for pname in sorted(self._parameter.keys()):
            print(self._parameter[pname])

    def __repr__(self):
        return f"ParameterSet({self.name}|{list(self._parameter.keys())})"

    def __str__(self):
        return self.__repr__()


if __name__ == '__main__':
    # Example usage
    param_constant = Parameter(name="constant_param", value=10.0, description="This is a constant parameter.")
    param_variable = Parameter(name="variable_param", value=5.0, range=(0.0, 10.0),
                               description="This is a variable parameter.")
    param_discrete = Parameter(name="discrete_param", value="a", range=["a", "b", "c"],
                               description="This is a discrete parameter.")

    print(param_constant.to_json())
    print(param_variable.to_json())
    print(param_discrete.to_json())

    print(param_variable.sample_values(5))
    print(param_discrete.sample_values(5))
