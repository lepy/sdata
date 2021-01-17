Usage examples
==============

store a pandas Dataframe
------------------------
.. uml::

   Alice -> Bob: Hi!
   Alice <- Bob: How are you?

.. uml::
    :scale: 100 %
    :align: center

    database "Testdata-Pool" as testdatapool {

        frame "Mat1" as testdata1
        frame "Mat2" as testdata2

    }

    database "Material-model-Pool" as matmodelpool {

        frame "Mat1_1" as matmodel1_1
        frame "Mat1_2" as matmodel1_2
        frame "Mat2_1" as matmodel2_1

    }

    database "Workflow-Pool" as workflowpool {
        frame "Workflow1" as workflow1
        frame "Workflow2" as workflow2
    }

    database "Run-Pool" as Runpool {
        database "Run1_1" as run1_1
        database "Run1_2" as run1_2
        database "Run2_1" as run2_1
    }

    testdata1 --> run1_1
    testdata1 --> run1_2
    testdata2 --> run2_1

    workflow1 --> run1_1
    workflow2 --> run1_2
    workflow1 --> run2_1

    run1_1 --> matmodel1_1
    run1_2 --> matmodel1_2
    run2_1 --> matmodel2_1

    @enduml

