class Cut(object):
    """
    Class used to represent a cutpoint in a range, such that any range can
    be represented by 2 Cuts
    """

    def __init__(self, the_type, above_all=False, below_all=False, point=None,
                 below=False):
        """ Instantiates a cut point

        Parameters
        ----------
        the_type : type
            Specify the most inclusive type that can be used for comparison
        above_all : boolean
            Specifies that cut point is above all possible values
            within the domain
        below_all : boolean
            Specifies that cut point is below all possible values
            within the domain
        point : instance of the domain
            A specific point in the domain where the cut should
            occur
        below : boolean
            If true, cut point is infinitesimally below specified point.
            Otherwise, is infinitesimally above specified point 
            
        Raises
        ------
        ValueError
            If input is invalid
        """
        self.the_type = the_type
        self.above_all = False
        self.below_all = False
        self.point = None
        self.below = False
        # Validate input
        if point is None:
            if not any((above_all, below_all)):
                raise ValueError("Must specify a type of cut point")
            elif all((above_all, below_all)):
                raise ValueError("Cannot be both above_all and below_all")
            else:
                # Correct input
                self.above_all = above_all
                self.below_all = below_all
        else:
            if any((above_all, below_all)):
                raise ValueError("Cannot be both point and above/below all")
            elif not isinstance(point, the_type):
                raise ValueError("Point must be instance of the_type")
            else:
                self.point = point
                self.below = below

    def _validate_query_pt(self, pt):
        if not isinstance(pt, self.the_type):
            raise ValueError("Type is not compatible with cutpoint type")
        return True

    def __hash__(self):
        if self.below_all:
            return hash(self.the_type) * 31 - hash(None)
        elif self.above_all:
            return hash(self.the_type) * 31 + hash(None)
        elif self.below:
            return hash(self.the_type) * 31 - hash(self.point)
        else:
            return hash(self.the_type) * 31 + hash(self.point)

    def __repr__(self):
        if self.below_all:
            return "Cut(Below all %s)" % str(self.the_type)
        elif self.above_all:
            return "Cut(Above all %s)" % str(self.the_type)
        elif self.below:
            return "Cut(Below %s)" % str(self.point)
        else:
            return "Cut(Above %s)" % str(self.point)

    def __cmp__(self, other):
        if self == other:
            return 0
        elif self < other:
            return -1
        elif self > other:
            return 1

    def __eq__(self, other):
        """ Returns whether Cuts are at EXACT same place """
        if not isinstance(other, Cut):
            return False
        elif self.above_all:
            return other.above_all
        elif self.below_all:
            return other.below_all
        elif (self.point is not None) and (other.point is not None):
            return ((self.point == other.point) and (self.below == other.below))
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        """ Returns whether cutpoint is less than a specified value """
        if isinstance(other, Cut):
            if self.below_all:
                return True
            elif self.above_all:
                return False
            elif other.below_all:
                return False
            elif other.above_all:
                return True
            else:
                if self.point < other.point:
                    return True
                elif self.point == other.point and self.below and \
                        not other.below:
                    return True
                else:
                    return False
        else:
            return self.is_less_than(other)

    def __gt__(self, other):
        """ Returns whether cutpoint is greater than a specified value """
        if isinstance(other, Cut):
            if self.below_all:
                return False
            elif self.above_all:
                return True
            elif other.below_all:
                return True
            elif other.above_all:
                return False
            else:
                if self.point > other.point:
                    return True
                elif self.point == other.point and not self.below and \
                        other.below:
                    return True
                else:
                    return False
        else:
            return self.is_greater_than(other)

    def __ge__(self, other):
        return (self.__eq__(other) or self.__gt__(other))

    def __le__(self, other):
        return (self.__eq__(other) or self.__lt__(other))

    def is_less_than(self, val):
        """ Returns whether the cutpoint is less than a specified value

        Parameters
        ----------
        val : Comparable, of compatible type
            The value to compare the cutpoint to

        Raises
        ------
        ValueError
            If the value type not compatible with cutpoint type

        Returns
        -------
        True if the cutpoint is strictly less than the specified value
        """
        self._validate_query_pt(val)
        if self.below_all:
            return True
        elif self.above_all:
            return False
        elif self.point < val:
            return True
        elif self.point == val and self.below:
            return True
        else:
            return False

    def is_greater_than(self, val):
        """ Returns whether the cutpoint is greater than a specified value

        Parameters
        ----------
        val : Comparable, of compatible type
            The value to compare the cutpoint to

        Raises
        ------
        ValueError
            If the value type not compatible with cutpoint type

        Returns
        -------
        True if the cutpoint is strictly greater than the specified value
        """
        self._validate_query_pt(val)
        if self.above_all:
            return True
        elif self.below_all:
            return False
        elif self.point > val:
            return True
        elif self.point == val and not self.below:
            return True
        else:
            return False

    @staticmethod
    def below_value(val, the_type=None):
        """ Create a cut point, where everything below some value is
        included

        Parameters
        ----------
        val : value in the domain
            Cut point, where everything below value is included
        the_type : type
            Most inclusive type that can be used for comparison. If
            None, then the type of the value is used
        Returns
        -------
        The cut object
        """
        if the_type is None:
            return Cut(type(val), point=val, below=True)
        else:
            return Cut(the_type, point=val, below=True)

    @staticmethod
    def below_all(the_type):
        """ Create a cut point outside the lower end of the domain

        Parameters
        ----------
        the_type : type
            Most inclusive type that can be used for comparison.
         
        Returns
        -------
        The cut object
        """
        return Cut(the_type, below_all=True)

    @staticmethod
    def above_value(val, the_type=None):
        """ Create a cut point, where everything above some value is
        included

        Parameters
        ----------
        val : value in the domain
            Cut point, where everything above value is included
        the_type : type
            Most inclusive type that can be used for comparison. If
            None, then the type of the value is used
         
        Returns
        -------
        The cut object
        """
        if the_type is None:
            return Cut(type(val), point=val, below=False)
        else:
            return Cut(the_type, point=val, below=False)

    @staticmethod
    def above_all(the_type):
        """ Create a cut point outside the upper end of the domain

        Parameters
        ----------
        the_type : type
            Most inclusive type that can be used for comparison
        
        Returns
        -------
        The cut object
        """
        return Cut(the_type, above_all=True)
