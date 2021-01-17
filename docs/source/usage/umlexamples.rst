Usage examples
==============

store a pandas Dataframe
------------------------

.. uml::

    @startuml
    skinparam roundCorner 15
    actor actor
    agent agent
    artifact artifact
    boundary boundary
    card card
    circle circle
    cloud cloud
    collections collections
    component component
    control control
    database database
    entity entity
    file file
    folder folder
    frame frame
    interface interface
    label label
    node node
    package package
    queue queue
    rectangle rectangle
    stack stack
    storage storage
    usecase usecase
    @enduml


.. uml::

    @startuml
    artifact artifact {
    }
    card card {
    }
    cloud cloud {
    }
    component component {
    }
    database database {
    }
    file file {
    }
    folder folder {
    }
    frame frame {
    }
    node node {
    }
    package package {
    }
    queue queue {
    }
    rectangle rectangle {
    }
    stack stack {
    }
    storage storage {
    }
    @enduml


.. uml::

    @startuml
    actor actor
    actor/ "actor/"
    agent agent
    artifact artifact
    boundary boundary
    card card
    circle circle
    cloud cloud
    collections collections
    component component
    control control
    database database
    entity entity
    file file
    folder folder
    frame frame
    interface interface
    label label
    node node
    package package
    queue queue
    rectangle rectangle
    stack stack
    storage storage
    usecase usecase
    usecase/ "usecase/"
    @enduml

.. uml::

    @startlatex
    \sum_{i=0}^{n-1} (a_i + b_i^2)
    @endlatex


.. uml::

    @startwbs
    * Business Process Modelling WBS
    ** Launch the project
    *** Complete Stakeholder Research
    *** Initial Implementation Plan
    ** Design phase
    *** Model of AsIs Processes Completed
    **** Model of AsIs Processes Completed1
    **** Model of AsIs Processes Completed2
    *** Measure AsIs performance metrics
    *** Identify Quick Wins
    ** Complete innovate phase
    @endwbs


.. uml::

    @startsalt
    {
    {T
     + World
     ++ America
     +++ Canada
     +++ USA
     ++++ New York
     ++++ Boston
     +++ Mexico
     ++ Europe
     +++ Italy
     +++ Germany
     ++++ Berlin
     ++ Africa
    }
    }
    @endsalt

.. uml::

    @startuml
    Entity01 }|..|| Entity02
    Entity03 }o..o| Entity04
    Entity05 ||--o{ Entity06
    Entity07 |o--|| Entity08
    @enduml


.. uml::

    @startuml

    ' hide the spot
    hide circle

    ' avoid problems with angled crows feet
    skinparam linetype ortho

    entity "Entity01" as e01 {
      *e1_id : number <<generated>>
      --
      *name : text
      description : text
    }

    entity "Entity02" as e02 {
      *e2_id : number <<generated>>
      --
      *e1_id : number <<FK>>
      other_details : text
    }

    entity "Entity03" as e03 {
      *e3_id : number <<generated>>
      --
      e1_id : number <<FK>>
      other_details : text
    }

    e01 ||..o{ e02
    e01 |o..o{ e03
    @enduml

.. uml::

    @startmindmap
    * Debian
    ** Ubuntu
    *** Linux Mint
    *** Kubuntu
    *** Lubuntu
    *** KDE Neon
    ** LMDE
    ** SolydXK
    ** SteamOS
    ** Raspbian with a very long name
    *** <s>Raspmbc</s> => OSMC
    *** <s>Raspyfi</s> => Volumio
    @endmindmap

.. uml::

    @startjson
    [1, 2, 3]
    @endjson
    @enduml

.. uml::

    @startjson
    {
    "null": null,
    "true": true,
    "false": false,
    "JSON_Number": [-1, -1.1, "<color:green>TBC"],
    "JSON_String": "a\nb\rc\td <color:green>TBC...",
    "JSON_Object": {
      "{}": {},
      "k_int": 123,
      "k_str": "abc",
      "k_obj": {"k": "v"}
    },
    "JSON_Array" : [
      [],
      [true, false],
      [-1, 1],
      ["a", "b", "c"],
      ["mix", null, true, 1, {"k": "v"}]
    ]
    }
    @endjson

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

