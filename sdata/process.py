from sdata.base import sdata_factory, Base

from typing import List, Dict, Any


class ProcessData(Base):
    PROCESS_DATATYPE = 'ProcessData'

    def __init__(self, **kwargs):
        # self.default_attributes = []
        # if "default_attributes" in kwargs:
        #     self.default_attributes.extend(kwargs.get("default_attributes"))
        super().__init__(**kwargs)
        # self.set_default_attributes()
        attributes = kwargs.get('attributes', [])
        self.set_attributes(attributes)

    def set_attributes(self, attributes: List[Any]):
        for attribute in attributes:
            self.metadata.add(**attribute)

    def is_complete(self) -> bool:
        for attr in self.metadata.values():
            if attr.required is True and attr.value is None:
                return False
        return True


class ProcessNode(Base):
    """
    Basisklasse für Prozessknoten. Definiert Inputs/Outputs und prüft Vollständigkeit.
    """
    required_inputs: List[type] = []  # Erforderliche Input-Klassen (Subklassen überschreiben)
    required_outputs: List[type] = []  # Erforderliche Output-Klassen (Subklassen überschreiben)

    PROCESS_DATATYPE = 'ProcessNode'

    def __init__(self, name: str = "ProcessNode", inputs: Dict[str, ProcessData] = None, **kwargs: Any):
        super().__init__(name=name, **kwargs)
        self.inputs: Dict[str, ProcessData] = inputs or {}
        self.outputs: Dict[str, ProcessData] = {}

    def validate_inputs(self) -> bool:
        """
        Prüft, ob alle erforderlichen Inputs vorhanden und vollständig sind.
        """
        for req_input in self.required_inputs:
            found = False
            for inp_key, inp in self.inputs.items():
                if isinstance(inp, req_input):
                    if not inp.is_complete():
                        raise ValueError(f"Input '{inp_key}' ({inp.name}) ist nicht vollständig.")
                    found = True
                    break
            if not found:
                raise ValueError(f"Fehlender erforderlicher Input: {req_input.__name__}")
        return True


# Beispiel: Spezifische Subklassen
class SpecificInput(ProcessData):
    def __init__(self, **kwargs):
        kwargs['default_attributes'] = [{"name": "a", "value": None, "dtype": float, "label": "an a", "required": True},
                                        {"name": "b", "value": None, "dtype": int, "label": "an b", "required": True},
                                        ]

        super().__init__(**kwargs)


class SpecificOutput(ProcessData):
    pass


class SpecificProcessNode(ProcessNode):
    required_inputs = [SpecificInput]  # Definiert benötigte Inputs
    required_outputs = [SpecificOutput]  # Definiert erzeugte Outputs

    def run(self) -> Dict[str, ProcessData]:
        self.validate_inputs()  # Validation vor Run

        input1 = self.inputs.get("input1")

        a = input1.md.get("a").value
        b = input1.md.get("b").value

        output = SpecificOutput(name="Output1")

        # Berechnung
        output.md.add("c", a + b)

        self.outputs["output1"] = output

        return self.outputs


if __name__ == '__main__':
    input_a = SpecificInput(name="input", attributes=[{"name": "a", "value": 1.2},
                                                      {"name": "b", "value": 3}])

    # Gültiger Knoten
    node = SpecificProcessNode(
        name="MyNode",
        inputs={"input1": input_a}
    )
    try:
        node.validate_inputs()  # Erfolgreich
        outputs = node.run()  # Erzeugt Outputs
        print("Valid node ran successfully.")
        print(node.outputs['output1'].udf)
    except ValueError as e:
        print(f"Valid node error: {e}")
