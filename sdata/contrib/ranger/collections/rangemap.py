from bisect import bisect_left
from sdata.contrib.ranger.range.range import Range
from collections import deque


class RangeMap(object):
    """ Class used to represent a mapping of disjoint ranges to some objects.
    Ranges do not coalesce. If a new Range is added over an existing Range,
    it overwrites the overlapping part of the existing Range
    """

    def __init__(self, range_dict=None):
        """ Instantiates a RangeMap
        
        Parameters
        ----------
        range_dict : Dictionary of Range -> object
            Dictionary to start off the RangeMap with. Note that this will
            not be traversed in any particular order, so it may result in
            unexpected behavior if instantiated with any overlapping ranges
        """
        # Holds lower and upper cut points of ranges
        self.lower_cuts = []
        self.upper_cuts = []
        # Holds the actual range objects that are the keys
        self.ranges = []
        # Holds items mapping to each range
        self.items = []
        if range_dict is not None:
            for range_key, val in range_dict.iteritems():
                self.put(range_key, val)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.put(key, value)

    def __delitem__(self, key):
        self.remove(key)

    def __iter__(self):
        return iter(self.ranges)

    def __eq__(self, other):
        if not isinstance(other, RangeMap):
            return False
        elif len(self) != len(other):
            return False
        for k1, v1, k2, v2 in zip(self.ranges, self.items,
                                  other.ranges, other.items):
            if (k1 != k2 or v1 != v2):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self.ranges)

    def __repr__(self):
        if len(self) < 5:
            return_str = "{%s}" % ", ".join([
                "%s : %s" % (k, v) for k, v in zip(self.ranges, self.items)
            ])
        else:
            return_str = "{%s, ..., %s}" % (", ".join([
                "%s : %s" % (k, v) for k, v in zip(self.ranges[:2], self.items[:2])
            ]), ", ".join([
                "%s : %s" % (k, v) for k, v in zip(self.ranges[-2:], self.items[-2:])
            ])
            )
        return return_str

    def __missing__(self, key):
        raise KeyError(str(key))

    def contains(self, val):
        """ Returns true if any of the ranges fully enclose the given
        value, which can be a single value or a Range object

        Parameters
        ----------
        val : A single value or a Range object

        Raises
        ------
        ValueError
            If the value type not compatible with the ranges
        
        Returns
        -------
        true if any of the ranges fully enclose the given value
        """
        if len(self) == 0: return False
        # Get the index+1 of the highest lower cut <= to the value or its
        # lower cutpoint and check if the value contained
        if isinstance(val, Range):
            lower_ind = max(bisect_left(self.lower_cuts, val.lower_cut) - 1, 0)
            return self.ranges[lower_ind].encloses(val)
        else:
            lower_ind = max(bisect_left(self.lower_cuts, val) - 1, 0)
            return self.ranges[lower_ind].contains(val)

    def get(self, key):
        """ Get the item(s) corresponding to a given key. The key can be a
        Range or a single value that is within a Range

        Parameters
        ----------
        key : A single value or Range object

        Raises
        ------
        KeyError
            If there is no overlap with the key
        ValueError
            If the key type not compatible with the ranges
        
        Returns
        -------
        A set containing all overlapping items
        """
        if not self.overlaps(key):
            self.__missing__(key)
        elif isinstance(key, Range):
            # If this is a single value
            return_set = set()
            # Get the bounding indices
            ovlap_lower_ind = max(bisect_left(self.lower_cuts, key.lower_cut) - 1, 0)
            ovlap_upper_ind = bisect_left(self.lower_cuts, key.upper_cut)
            for i in range(ovlap_lower_ind, ovlap_upper_ind):
                try:
                    # Get intersection of the ranges
                    intersect = key.intersection(self.ranges[i])
                    if not intersect.is_empty():
                        # If overlapping with this range, put its
                        # item in the return set
                        return_set.add(self.items[i])
                except ValueError:
                    # Continue if no overlap with this range
                    continue
            # Return the set of items
            return return_set
        else:
            # If this is a single value
            # Get the index of the range containing the value
            lower_ind = max(bisect_left(self.lower_cuts, key) - 1, 0)
            # Return the item at that value
            return set([self.items[lower_ind]])

    def overlaps(self, val):
        """ Returns true if any of the ranges at least partially overlap
        the given value, which can be a single value or a Range object

        Parameters
        ----------
        val : A single value or a Range object

        Raises:
        -------
        ValueError
            If the value type not compatible with the ranges

        Returns
        -------
        true if any of the ranges fully enclose the given value
        """
        if len(self) == 0: return False
        # Get the index+1 of the highest lower cut <= to the value or its
        # lower cutpoint and check if the value overlaps
        if isinstance(val, Range):
            lower_ind = bisect_left(self.lower_cuts, val.lower_cut) - 1
            upper_ind = bisect_left(self.lower_cuts, val.upper_cut)
            for i in range(lower_ind, upper_ind):
                if val.is_connected(self.ranges[i]):
                    if not self.ranges[i].intersection(val).is_empty():
                        return True
            return False
        else:
            lower_ind = bisect_left(self.lower_cuts, val) - 1
            return self.ranges[lower_ind].contains(val)

    def put(self, key, val):
        """ Creates a mapping from a Range to a value. Note that if the
        key Range overlaps any existing ranges, it will replace those
        Range(s) over the intersection

        Parameters
        ----------
        key : Range object
            A Range to serve as a key
        val : value
            Some value that the Range should map to

        Raises
        ------
        TypeError
            If the key is not a Range object
        """
        if not isinstance(key, Range):
            raise TypeError("key is not a Range")
        elif key.is_empty():
            # Skip if this is an empty range
            return
        # Figure out where to the key/value
        if not self.overlaps(key):
            # If this range is completely on its own, just insert
            insert_ind = bisect_left(self.lower_cuts, key.lower_cut)
            self.ranges.insert(insert_ind, key)
            self.lower_cuts.insert(insert_ind, key.lower_cut)
            self.upper_cuts.insert(insert_ind, key.upper_cut)
            self.items.insert(insert_ind, val)
            return
        else:
            # If this range has some overlap with existing ranges
            ovlap_lower_ind = max(bisect_left(self.lower_cuts, key.lower_cut) - 1, 0)
            ovlap_upper_ind = bisect_left(self.lower_cuts, key.upper_cut)
            # Create queue or indices marked for removal
            remove_ranges = deque()
            # Create queue ranges to add
            add_ranges = deque()
            # Create queue of items to add
            add_items = deque()
            for i in range(ovlap_lower_ind, ovlap_upper_ind):
                try:
                    # Get intersection of the ranges
                    intersect = key.intersection(self.ranges[i])
                    if not intersect.is_empty():
                        if intersect == self.ranges[i]:
                            # Mark range for removal
                            remove_ranges.append(i)
                        elif self.lower_cuts[i] == intersect.lower_cut:
                            # If equal on left cutpoint, subtract out left
                            # part
                            self.lower_cuts[i] = intersect.upper_cut
                            self.ranges[i] = Range(intersect.upper_cut,
                                                   self.upper_cuts[i])
                        elif self.upper_cuts[i] == intersect.upper_cut:
                            # If equal on right cutpoint, subtract out
                            # right part
                            self.upper_cuts[i] = intersect.lower_cut
                            self.ranges[i] = Range(self.lower_cuts[i],
                                                   intersect.lower_cut)
                        else:
                            # If in the middle, split into two parts, putting
                            # both in add queue and placing the old range index
                            # in the remove queue
                            add_ranges.append(Range(self.lower_cuts[i],
                                                    intersect.lower_cut))
                            add_ranges.append(Range(intersect.upper_cut,
                                                    self.upper_cuts[i]))
                            add_items.append(self.items[i])
                            add_items.append(self.items[i])
                            remove_ranges.append(i)
                except ValueError:
                    # Continue if no overlap with this range
                    continue
            # Remove any ranges that are marked for removal
            while len(remove_ranges) > 0:
                remove_ind = remove_ranges.pop()
                self.ranges.pop(remove_ind)
                self.lower_cuts.pop(remove_ind)
                self.upper_cuts.pop(remove_ind)
                self.items.pop(remove_ind)
            add_items.append(val)
            add_ranges.append(key)
            # Use recursive call to place the pairs, which now
            # should not overlap with any other ranges
            while len(add_ranges) > 0:
                self.put(add_ranges.pop(), add_items.pop())

    def remove(self, a_range):
        """ Removes a range and its value from the range set

        Parameters
        ----------
        a_range : A Range object
            The Range to remove

        Raises
        ------
        ValueError
            If removing range of type not compatible with previously
            added ranges
        TypeError
            If not a Range
        """
        if not isinstance(a_range, Range):
            raise TypeError("a_range is not a Range")
        elif a_range.is_empty():
            # Skip if this is an empty range
            return
        # Check for compatibility of types if necessary
        if len(self) > 0:
            if not (issubclass(a_range.lower_cut.the_type,
                               self.ranges[0].lower_cut.the_type) or \
                    issubclass(self.ranges[0].lower_cut.the_type,
                               a_range.lower_cut.the_type)):
                raise ValueError("Range not compatible with previously added ranges")
        # Check if the range actually overlaps with the key set
        if not self.overlaps(a_range):
            return
        else:
            # There's some overlap, so deal with that
            # Determine where overlap occurs
            ovlap_lower_ind = max(bisect_left(self.lower_cuts,
                                              a_range.lower_cut) - 1, 0)
            ovlap_upper_ind = bisect_left(self.lower_cuts, a_range.upper_cut)
            # Create queue of indices marked for removal
            remove_ranges = deque()
            # Create queue of ranges to add
            add_ranges = deque()
            # Create queue of items to add with the add_ranges
            add_items = deque()
            for i in range(ovlap_lower_ind, ovlap_upper_ind):
                try:
                    # Get intersection of the ranges
                    intersect = a_range.intersection(self.ranges[i])
                    if not intersect.is_empty():
                        if intersect == self.ranges[i]:
                            # Mark range for removal
                            remove_ranges.append(i)
                        elif self.lower_cuts[i] == intersect.lower_cut:
                            # If equal on the left cutpoint, subtract
                            # out left part
                            self.lower_cuts[i] = intersect.upper_cut
                            self.ranges[i] = Range(intersect.upper_cut,
                                                   self.upper_cuts[i])
                        elif self.upper_cuts[i] == intersect.upper_cut:
                            # If equal on right cutpoint, subtract out
                            # right part
                            self.upper_cuts[i] = intersect.lower_cut
                            self.ranges[i] = Range(self.lower_cuts[i],
                                                   intersect.lower_cut)
                        else:
                            # If in the middle, split into two parts, putting
                            # both in add queue and placing the old range index
                            # into the remove queue
                            add_ranges.append(Range(self.lower_cuts[i],
                                                    intersect.lower_cut))
                            add_items.append(self.items[i])
                            add_ranges.append(Range(intersect.upper_cut,
                                                    self.upper_cuts[i]))
                            add_items.append(self.items[i])
                            remove_ranges.append(i)
                except ValueError:
                    # Continue if no overlap with this range
                    continue
            # Remove any ranges that are marked for removal
            while len(remove_ranges) > 0:
                remove_ind = remove_ranges.pop()
                self.ranges.pop(remove_ind)
                self.lower_cuts.pop(remove_ind)
                self.upper_cuts.pop(remove_ind)
                self.items.pop(remove_ind)
            # Add any pairs that need to be added
            while len(add_ranges) > 0:
                self.put(add_ranges.pop(), add_items.pop())

    def which_overlaps(self, val):
        """ Returns which of the Ranges overlap with a single value or
        Range object

        Parameters
        ----------
        val : A single value or a Range object

        Raises:
        -------
        ValueError
            If the value type not compatible with the ranges

        Returns
        -------
        set of ranges overlapping with the value
        """
        if len(self) == 0: return False
        # Get the index+1 of the highest lower cut <= to the value or its
        # lower cutpoint and check if the value overlaps. If it does, add
        # to set
        overlap_set = set()
        if isinstance(val, Range):
            lower_ind = bisect_left(self.lower_cuts, val.lower_cut) - 1
            upper_ind = bisect_left(self.lower_cuts, val.upper_cut)
            for i in range(lower_ind, upper_ind):
                if val.is_connected(self.ranges[i]):
                    if not self.ranges[i].intersection(val).is_empty():
                        overlap_set.add(self.ranges[i])
            return overlap_set
        else:
            lower_ind = bisect_left(self.lower_cuts, val) - 1
            if self.ranges[lower_ind].contains(val):
                overlap_set.add(self.ranges[lower_ind])
            return overlap_set
