from sdata.base import sdata_factory, Base

from typing import List, Dict, Any, Type


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
        self.metadata.add(
            self.SDATA_BFO_CLASS, "sdata.sclass:GenericallyDependentContinuant", dtype="str",
            description="sdata bfo class name", required=True
        )

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
        self.metadata.add(
            self.SDATA_BFO_CLASS, "sdata.sclass:Prozess", dtype="str",
            description="sdata bfo class name", required=True
        )
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

class CompositeProcess(ProcessNode):
    def __init__(self, name: str, processes: List[Type[ProcessNode]], inputs: Dict[str, ProcessData] = None, **kwargs: Any):
        super().__init__(name=name, inputs=inputs, **kwargs)
        self.process_classes = processes  # Store class types
        self.input_classes: Dict[str, Type[ProcessData]] = {}
        self.output_classes: Dict[str, Type[ProcessData]] = {}
        self._compute_aggregated_io()
        self.required_inputs = list(self.input_classes.values())
        self.required_outputs = list(self.output_classes.values())

    def _compute_aggregated_io(self):
        all_inputs = set()
        all_outputs = set()
        internal_connections = set()

        for proc_type in self.process_classes:
            for inp in proc_type.input_classes.keys():
                all_inputs.add(inp)
            for out in proc_type.output_classes.keys():
                all_outputs.add(out)

        for i, proc_type in enumerate(self.process_classes):
            for out in proc_type.output_classes.keys():
                for next_proc_type in self.process_classes[i+1:]:
                    if out in next_proc_type.input_classes:
                        internal_connections.add(out)

        external_inputs = all_inputs - internal_connections
        external_outputs = all_outputs - all_inputs

        for inp in external_inputs:
            for proc_type in self.process_classes:
                if inp in proc_type.input_classes:
                    self.input_classes[inp] = proc_type.input_classes[inp]
                    break

        for out in external_outputs:
            for proc_type in self.process_classes:
                if out in proc_type.output_classes:
                    self.output_classes[out] = proc_type.output_classes[out]
                    break

        # self.computation = " + ".join([p.computation for p in self.process_classes])

    # def execute(self) -> Dict[str, ProcessData]:
    #     if not self.validate_inputs():
    #         raise ValueError("Inputs not valid")
    #     intermediate = self.inputs.copy()
    #     for proc_type in self.process_classes:
    #         proc = proc_type(inputs={k: intermediate[k] for k in proc_type.input_classes if k in intermediate})
    #         proc_output = proc.execute()
    #         intermediate.update(proc_output)
    #     self.outputs = {k: intermediate[k] for k in self.output_classes}
    #     return self.outputs

def create_process_class(
    process_name: str,
    input_classes: Dict[str, Type[ProcessData]],
    output_classes: Dict[str, Type[ProcessData]],
) -> Type[ProcessNode]:
    """
    Factory function to generically create a subclass of ProcessNode.

    :param process_name: Name of the new process class (e.g., 'Process_1').
    :param input_classes: Dict mapping input names to ProcessData subclasses.
    :param output_classes: Dict mapping output names to ProcessData subclasses.
    :return: A new subclass of ProcessNode.
    """
    class_dict = {
        'input_classes': input_classes,
        'output_classes': output_classes,
        'required_inputs': list(input_classes.values()),
        'required_outputs': list(output_classes.values()),
    }

    return type(process_name, (ProcessNode,), class_dict)


# Beispiel: Spezifische Subklassen
class SpecificInput(ProcessData):
    def __init__(self, **kwargs):
        kwargs['default_attributes'] = [{"name": "a", "value": None, "dtype": float, "unit": "-",
                                         "description": "my a value", "label": "$a$", "required": True},
                                        {"name": "b", "value": None, "dtype": int,  "unit": "MPa",
                                         "description": "my b value", "label": "$b$", "required": True},
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
