import json
from typing import Dict, Tuple, List, Union, Optional
import random


class Distribution:
    def __init__(self, name: str, **params):
        self.name = name
        self.params = params
        self.dtype = float

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "params": self.params
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(name=data["name"], **data.get("params", {}))

    def generate_value(self, bounds: Union[Tuple[float, float], List[Union[int, str]]]) -> Union[float, int, str]:
        min_val, max_val = bounds
        if self.name == "uniform":
            return random.uniform(min_val, max_val)
        raise ValueError(f"Unsupported distribution: {self.name}")


class Parameter:
    def __init__(self, name: str, dtype: type, description: Optional[str] = None, fix: bool = False):
        self.name = name
        self.dtype = dtype
        self.description = description or ""
        self.fix = fix

    def _validate_and_cast_value(self, value):
        if not isinstance(value, self.dtype):
            try:
                return self.dtype(value)
            except (ValueError, TypeError):
                import warnings
                warnings.warn(f"Value {value} could not be cast to {self.dtype}. Keeping the original value.")
                return value
        return value

    def to_dict(self) -> Dict:
        return {
            "class_name": self.__class__.__name__,
            "name": self.name,
            # "dtype": self.dtype.__name__,
            "description": self.description,
            "fix": self.fix
        }

    @classmethod
    def get_subclasses(cls):
        class_name = "Parameter"
        all_subclasses = {}
        subclasses = {subclass.__name__: subclass for subclass in cls.__subclasses__()}
        all_subclasses.update(subclasses)
        for subclassname, subcls in subclasses.items():
            subsubclasses = {subclass.__name__: subclass for subclass in subcls.__subclasses__()}
            #            all_subclasses = all_subclasses | subsubclasses
            all_subclasses.update(subsubclasses)

        return all_subclasses

    @classmethod
    def from_dict(cls, data: Dict):
        class_name = data.get("class_name", "Parameter")
        subclasses = cls.get_subclasses()
        if class_name in subclasses:
            return subclasses[class_name].from_dict(data)
        raise ValueError(f"Unknown class_name '{class_name}' in data.")


class Variable(Parameter):
    def __init__(self, name: str, value: Union[bool, float, int, str], dtype: type,
                 bounds: Optional[Tuple[float, float]] = None,
                 distribution: Optional[Distribution] = None,
                 description: Optional[str] = None, fix: bool = False):
        description = description or ""
        super().__init__(name, dtype, description, fix)
        self.bounds = bounds
        self.distribution = distribution or Distribution("uniform")
        self.value = self._validate_and_cast_value(value)

    def sample_value(self) -> Union[bool, float, int, str]:
        if self.fix:
            return self.value
        sampled = self.distribution.generate_value(self.bounds)
        self.value = self._validate_and_cast_value(sampled)
        return self.value

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            "value": self.value,
            "bounds": self.bounds,
            "distribution": self.distribution.to_dict() if self.distribution else None
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        distribution = Distribution.from_dict(data["distribution"]) if data.get("distribution") else None
        return cls(
            name=data["name"],
            value=data["value"],
            bounds=data.get("bounds"),
            distribution=distribution,
            description=data.get("description"),
            fix=data.get("fix", False)
        )

    def sample_values(self, n: int = 1) -> List[Union[bool, float, int, str]]:
        """
        Generate n sampled values based on the defined distribution.
        """
        if self.fix is True:
            return [self.value] * n
        else:
            return [self.dtype(self.distribution.generate_value(self.bounds)) for _ in range(n)]

    def __repr__(self):
        try:
            value_bounds = f"{self.min:.2g},{self.max:.2g}"
        except:
            value_bounds = str(self.bounds)
        return f"({self.name}|{self.value}|[{value_bounds}]|{self.dtype.__name__})"

    def __str__(self):
        return self.__repr__()


class DiscreteVariable(Parameter):
    def __init__(self, name: str, value: Union[bool, float, int, str], dtype: type,
                 discrete_values: List[Union[bool, int, str]],
                 description: Optional[str] = None, fix: bool = False):
        description = description or ""
        super().__init__(name, dtype, description, fix)
        self.discrete_values = [self._validate_and_cast_value(v) for v in discrete_values]
        self.value = self._validate_and_cast_value(value)

    def sample_value(self) -> Union[bool, float, int, str]:
        if self.fix:
            return self.value
        self.value = random.choice(self.discrete_values)
        return self.value

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            "value": self.value,
            "discrete_values": self.discrete_values
        })
        return data

    def __repr__(self):
        try:
            if self.discrete_values and len(self.discrete_values) > 4:
                value_bounds = self.discrete_values[:4] + ["..."]
            elif self.discrete_values:
                value_bounds = self.discrete_values
            else:
                value_bounds = "None"
        except:
            value_bounds = "!"
        return f"({self.name}|{self.value}|[{value_bounds}]|{self.dtype.__name__})"

    def __str__(self):
        return self.__repr__()

    def sample_values(self, n: int = 1) -> List[Union[bool, float, int, str]]:
        """
        Generate n sampled values based on the defined distribution.
        """
        if self.fix is True:
            return [self.value] * n
        else:
            return [random.choice(self.discrete_values) for _ in range(n)]


# Specialized Variable Classes
class VariableInt(Variable):
    dtype = int

    def __init__(self, name: str, value: int, bounds: Optional[Tuple[int, int]] = None,
                 distribution: Optional[Distribution] = None, description: Optional[str] = None, fix: bool = False):
        super().__init__(name, value, int, bounds, distribution, description, fix)

    @property
    def min(self):
        if isinstance(self.bounds, (list, tuple)):
            return self.dtype(self.bounds[0])
        raise ValueError("min is only available for continuous boundss")

    @property
    def max(self):
        if isinstance(self.bounds, (list, tuple)):
            return self.dtype(self.bounds[1])
        raise ValueError("max is only available for continuous boundss")


class VariableFloat(Variable):
    dtype = float

    def __init__(self, name: str, value: float, bounds: Optional[Tuple[float, float]] = None,
                 distribution: Optional[Distribution] = None, description: Optional[str] = None, fix: bool = False):
        if bounds is None:
            bounds = [self.dtype(value), self.dtype(value)]
        super().__init__(name, value, float, bounds, distribution, description, fix)

    @property
    def min(self):
        if isinstance(self.bounds, (list, tuple)):
            return self.bounds[0]
        raise ValueError("min is only available for continuous boundss")

    @property
    def max(self):
        if isinstance(self.bounds, (list, tuple)):
            return self.bounds[1]
        raise ValueError("ma"
                         "x is only available for continuous boundss")


class VariableStr(Variable):
    dtype = str

    def __init__(self, name: str, value: str, bounds: Optional[Tuple[str, str]] = None,
                 distribution: Optional[Distribution] = None, description: Optional[str] = None, fix: bool = False):
        super().__init__(name, value, str, bounds, distribution, description, fix)

    def sample_values(self, n: int = 1) -> List[Union[bool, float, int, str]]:
        """
        Generate n sampled values based on the defined distribution.
        """
        return [self.value] * n


# Specialized DiscreteVariable Classes
class DiscreteVariableInt(DiscreteVariable):
    dtype = int

    def __init__(self, name: str, value: int, discrete_values: List[int],
                 description: Optional[str] = None, fix: bool = False):
        super().__init__(name, value, int, discrete_values, description, fix)


class DiscreteVariableFloat(DiscreteVariable):
    dtype = float

    def __init__(self, name: str, value: float, discrete_values: List[float],
                 description: Optional[str] = None, fix: bool = False):
        super().__init__(name, value, float, discrete_values, description, fix)


class DiscreteVariableStr(DiscreteVariable):
    dtype = str

    def __init__(self, name: str, value: str, discrete_values: List[str],
                 description: Optional[str] = None, fix: bool = False):
        super().__init__(name, value, str, discrete_values, description, fix)


class DiscreteVariableBool(DiscreteVariable):
    dtype = bool

    def __init__(self, name: str, value: bool, discrete_values: Optional[List[bool]] = None,
                 description: Optional[str] = None, fix: bool = False):
        discrete_values = [True, False]
        super().__init__(name, value, bool, discrete_values, description, fix)


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
        data = json.loads(json_str)
        return cls.from_dict(data)

    def print(self):
        for pname in sorted(self._parameter.keys()):
            print(self._parameter[pname])

    def __repr__(self):
        return f"ParameterSet({self.name}|{list(self._parameter.keys())})"

    def __str__(self):
        return self.__repr__()
