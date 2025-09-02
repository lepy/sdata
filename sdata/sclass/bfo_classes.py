# bfo_classes.py
# This module defines Python classes mirroring the BFO 2020 ontology structure.
# Each class inherits from its parent BFO class and stores its IRI (URL) as an instance variable.
# Docstrings are added based on elucidations and definitions from the BFO documentation.

"""
The Basic Formal Ontology (BFO) is a small, upper level ontology that is designed for use in supporting information
retrieval, analysis and integration in scientific and other domains. BFO is a genuine upper ontology.
Thus it does not contain physical, chemical, biological or other terms which would properly fall within the coverage
domains of the special sciences. BFO is used by more than 550 ontology-driven endeavors throughout the world.
"""

from .lazy_namespace import LazyRegistry

specs = {
    "Entity": "sdata.sclass.bfo_classes:Entity",
    "Continuant": "sdata.sclass.bfo_classes:Continuant",
    "Occurrent": "sdata.sclass.bfo_classes:Occurrent",
    "IndependentContinuant": "sdata.sclass.bfo_classes:IndependentContinuant",
    "GenericallyDependentContinuant": "sdata.sclass.bfo_classes:GenericallyDependentContinuant",
    "SpecificallyDependentContinuant": "sdata.sclass.bfo_classes:SpecificallyDependentContinuant",
    "ImmaterialEntity": "sdata.sclass.bfo_classes:ImmaterialEntity",
    "MaterialEntity": "sdata.sclass.bfo_classes:MaterialEntity",
    "Quality": "sdata.sclass.bfo_classes:Quality",
    "RealizableEntity": "sdata.sclass.bfo_classes:RealizableEntity",
    "RelationalQuality": "sdata.sclass.bfo_classes:RelationalQuality",
    "Role": "sdata.sclass.bfo_classes:Role",
    "Disposition": "sdata.sclass.bfo_classes:Disposition",
    "Function": "sdata.sclass.bfo_classes:Function",
    "Site": "sdata.sclass.bfo_classes:Site",
    "SpatialRegion": "sdata.sclass.bfo_classes:SpatialRegion",
    "ContinuantFiatBoundary": "sdata.sclass.bfo_classes:ContinuantFiatBoundary",
    "FiatPoint": "sdata.sclass.bfo_classes:FiatPoint",
    "FiatSurface": "sdata.sclass.bfo_classes:FiatSurface",
    "FiatLine": "sdata.sclass.bfo_classes:FiatLine",
    "ZeroDimensionalSpatialRegion": "sdata.sclass.bfo_classes:ZeroDimensionalSpatialRegion",
    "OneDimensionalSpatialRegion": "sdata.sclass.bfo_classes:OneDimensionalSpatialRegion",
    "TwoDimensionalSpatialRegion": "sdata.sclass.bfo_classes:TwoDimensionalSpatialRegion",
    "ThreeDimensionalSpatialRegion": "sdata.sclass.bfo_classes:ThreeDimensionalSpatialRegion",
    "FiatObjectPart": "sdata.sclass.bfo_classes:FiatObjectPart",
    "ObjectAggregate": "sdata.sclass.bfo_classes:ObjectAggregate",
    "Object": "sdata.sclass.bfo_classes:Object",
    "Process": "sdata.sclass.bfo_classes:Process",
    "ProcessBoundary": "sdata.sclass.bfo_classes:ProcessBoundary",
    "TemporalRegion": "sdata.sclass.bfo_classes:TemporalRegion",
    "SpatiotemporalRegion": "sdata.sclass.bfo_classes:SpatiotemporalRegion",
    "History": "sdata.sclass.bfo_classes:History",
    "ZeroDimensionalTemporalRegion": "sdata.sclass.bfo_classes:ZeroDimensionalTemporalRegion",
    "TemporalInstant": "sdata.sclass.bfo_classes:TemporalInstant",
    "OneDimensionalTemporalRegion": "sdata.sclass.bfo_classes:OneDimensionalTemporalRegion",
    "TemporalInterval": "sdata.sclass.bfo_classes:TemporalInterval"
}

# 1) Registry für dieses Package anlegen
_registry = LazyRegistry(__name__)

# 2) Anfangs-Exports (kann leer sein)
_registry.register_many(specs)
# 3) An Package binden (aktiviert __getattr__/__dir__)
_registry.attach()

class Entity:
    """Elucidation: Entity is the most basic category in BFO, encompassing both continuants and occurrents.
    It is a primitive term and cannot be defined non-circularly; instead, it is elucidated as anything that exists,
    has existed, or will exist. Supplemented by axioms that all other classes are subclasses of entity."""

    def __init__(self, **kwargs):
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000001"

    def __str__(self):
        return f"<bfo:{self.__class__.__name__}>"

    def __repr__(self):
        return f"<bfo:{self.__class__.__name__}>"

class Continuant(Entity):
    """Elucidation: A continuant is an entity that persists, endures, or continues to exist through time while
    maintaining its identity. Examples include objects, qualities, and functions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000002"

class Occurrent(Entity):
    """Elucidation: An occurrent is an entity that unfolds or develops through time.
    Examples include processes, events, and temporal regions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000003"

class IndependentContinuant(Continuant):
    """Elucidation: An independent continuant is a continuant that is a bearer of quality
    and realizable entity qualities, in which other entities inhere and which itself cannot inhere in anything.
    Examples include material entities and sites."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000004"

class GenericallyDependentContinuant(Continuant):
    """Elucidation: A generically dependent continuant is a continuant that is dependent on one or other independent
    continuant bearers. For any particular bearer, the dependent continuant is dependent on that bearer only.
    Examples include digital files or information artifacts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000031"

class SpecificallyDependentContinuant(Continuant):
    """Elucidation: A specifically dependent continuant is a continuant that inheres in or is borne by other entities.
    Every instance of A requires some specific instance of B which must always be the same. Examples include qualities
    and roles."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000020"

class ImmaterialEntity(IndependentContinuant):
    """Elucidation: An immaterial entity is an independent continuant that has no material parts.
    Examples include sites, spatial regions, and fiat boundaries."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000141"

class MaterialEntity(IndependentContinuant):
    """Elucidation: A material entity is an independent continuant that has some portion of matter as proper
    or improper part. Examples include objects and object aggregates."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000040"

class Quality(SpecificallyDependentContinuant):
    """Elucidation: A quality is a specifically dependent continuant that is exhibited if it inheres in an entity
    or entities (internal quality) or if it is borne by an entity or entities (relational quality).
    Examples include colors, shapes, or temperatures."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000019"

class RealizableEntity(SpecificallyDependentContinuant):
    """Elucidation: A realizable entity is a specifically dependent continuant that inheres in some independent
    continuant which is not a spatial region and is of a type instances of which are realized in processes.
    Examples include roles, dispositions, and functions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000017"

class RelationalQuality(Quality):
    """Elucidation: A relational quality is a quality which specifically depends on two or more entities.
    Attributes elucidating relationships among entities, like a parental connection."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000145"

class Role(RealizableEntity):
    """Elucidation: A role is a realizable entity that exists because there is some single bearer that is in
    some natural or conventional context considered to play the role. Examples include student role or patient role."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000023"

class Disposition(RealizableEntity):
    """Elucidation: A disposition is a realizable entity that essentially causes a specific process or transformation
    in the object in which it inheres, under specific circumstances. Examples include fragility or infectivity."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000016"

class Function(Disposition):
    """Elucidation: A function is a disposition that exists in virtue of the bearer's physical make-up and this
    physical make-up is something the bearer possesses because it came into being, either through evolution or
    through intentional design, in order to realize processes of a specific sort. Examples include the function of a heart or a hammer."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000034"

class Site(ImmaterialEntity):
    """Elucidation: A site is an immaterial entity that is a three-dimensional hole or cavity that contains some
    material entity. Examples include the lumen of the gastrointestinal tract."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000029"

class SpatialRegion(ImmaterialEntity):
    """Elucidation: A spatial region is an immaterial entity that is a continuous part of space.
    Examples include volumes, areas, lines, or points in space."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000006"

class ContinuantFiatBoundary(ImmaterialEntity):
    """Elucidation: A continuant fiat boundary is an immaterial entity that is of zero, one or two dimensions and
    does not include a spatial region as part. Examples include fiat points, lines, and surfaces."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000140"

class FiatPoint(ContinuantFiatBoundary):
    """Elucidation: A fiat point is a zero-dimensional continuant fiat boundary.
    Examples include the North Pole or arbitrary points on a map."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000142"

class FiatSurface(ContinuantFiatBoundary):
    """Elucidation: A fiat surface is a two-dimensional continuant fiat boundary.
    Examples include political borders or surfaces defined by convention."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000147"

class FiatLine(ContinuantFiatBoundary):
    """Elucidation: A fiat line is a one-dimensional continuant fiat boundary.
    Examples include lines on a map or borders."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000148"

class ZeroDimensionalSpatialRegion(SpatialRegion):
    """Elucidation: A zero-dimensional spatial region is a point in space."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000018"

class OneDimensionalSpatialRegion(SpatialRegion):
    """Elucidation: A one-dimensional spatial region is a line or a curve in space."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000026"

class TwoDimensionalSpatialRegion(SpatialRegion):
    """Elucidation: A two-dimensional spatial region is a surface or an area in space."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000009"

class ThreeDimensionalSpatialRegion(SpatialRegion):
    """Elucidation: A three-dimensional spatial region is a volume in space."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000028"

class FiatObjectPart(MaterialEntity):
    """Elucidation: A fiat object part is a material entity that is a proper part of some larger object, but is not
    demarcated from the remainder of this object by a physical discontinuity.
    Examples include hemispheres of the brain."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000024"

class ObjectAggregate(MaterialEntity):
    """Elucidation: An object aggregate is a material entity that is a mereological sum of separate objects.
    Examples include populations or heaps."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000038"

class Object(MaterialEntity):
    """Elucidation: An object is a material entity that is spatially extended, maximally self-connected and
    self-contained (the parts are not separated by any kind of discontinuity) and possesses some endurance or stability.
    Examples include apples, planets, or humans."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000030"

class Process(Occurrent):
    """Elucidation: A process is an occurrent that has temporal proper parts and for some time t, p depends_on some
    material entity at t. Examples include running or digestion."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000015"

class ProcessBoundary(Occurrent):
    """Elucidation: A process boundary is an occurrent that is the instantaneous temporal boundary of a process.
    Markers denoting the commencement or termination of processes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000035"

class TemporalRegion(Occurrent):
    """Elucidation: A temporal region is an occurrent that is a continuous part of time. Linear time segments
    encompassing occurrences."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000008"

class SpatiotemporalRegion(Occurrent):
    """Elucidation: A spatiotemporal region is an occurrent that is a continuous part of spacetime. Examples include
    the region occupied by a process."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000005"

class History(Process):
    """Elucidation: A history is a process that is the totality of processes taking place in the spatiotemporal region
    occupied by a material entity or the fiat object part aggregate of such regions. Documented sequences of events
    across a temporal expanse."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000182"

class ZeroDimensionalTemporalRegion(TemporalRegion):
    """Elucidation: A zero-dimensional temporal region is an instantaneous temporal boundary; a point in time."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000007"

class TemporalInstant(ZeroDimensionalTemporalRegion):
    """Elucidation: A temporal instant is a zero-dimensional temporal region that is instantaneous."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000037"

class OneDimensionalTemporalRegion(TemporalRegion):
    """Elucidation: A one-dimensional temporal region is a temporal interval with positive duration."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000011"

class TemporalInterval(OneDimensionalTemporalRegion):
    """Elucidation: A temporal interval is a one-dimensional temporal region that is extended."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.iri = "http://purl.obolibrary.org/obo/BFO_0000168"

if __name__ == '__main__':

    history = History()
    print(history)

    print(History)
