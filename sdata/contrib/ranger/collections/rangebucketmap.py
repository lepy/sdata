from bisect import bisect_left
from collections import deque, Hashable
from sdata.contrib.ranger.collections.rangemap import RangeMap
from sdata.contrib.ranger.range.range import Range
from sdata.contrib.ranger.range.cut import Cut

class RangeBucketMap(RangeMap):
    """ Class used to represent a mapping of disjoint ranges to sets of items. Ranges
    do not coalesce. However, if a new Range is added over an existing Range, items
    belonging to the existing Range are retained in that Range
    """

    def __init__(self, range_dict=None):
        """ Instantiates a RangeBucketMap

        Parameters
        ----------
        range_dict : Dictionary of Range -> object
            Dictionary to start off the RangeBucketMap with
        """
        self.recurse_add = False
        super(RangeBucketMap, self).__init__(range_dict)

    def iteritems(self, start=None, end=None):
        """ Iterates over pairs of (Range, value)

        Parameters
        ----------
        start : comparable, optional
            The starting point for iterating, inclusive
        end : comparable, optional
            The ending point for iterating, inclusive

        Returns
        -------
        Generator of (Range intersecting [start,end], value), ordered by start point
        """
        if start is None:
            start = self.lower_cuts[0]
        else:
            start = Cut.below_value(start)
        if end is None:
            end = self.upper_cuts[-1]
        else:
            end = Cut.above_value(end)
        bounding_range = Range(start, end)
        # Get the bounding indices
        ovlapLowerInd = max(bisect_left(self.lower_cuts, start) - 1, 0)
        ovlapUpperInd = bisect_left(self.lower_cuts, end)
        # Create queue of values that need to be generated
        yield_vals = deque()
        # Create dictionary of values to be generated -> indices containing them
        vals_inds_dict = {}
        for i in range(ovlapLowerInd, ovlapUpperInd):
            # Check if anything can be released from the queue
            while len(yield_vals) > 0:
                if vals_inds_dict[yield_vals[0]][-1] < i - 1:
                    # Yield the full range, value. Remove value from queue
                    val = yield_vals.popleft()
                    yield Range(max(self.lower_cuts[vals_inds_dict[val][0]], start),
                                min(self.upper_cuts[vals_inds_dict[val][-1]], end)), val
                    # Remove value from dict
                    del vals_inds_dict[val]
                else:
                    break
            try:
                # Get intersection of the ranges
                intersect = bounding_range.intersection(self.ranges[i])
                if not intersect.is_empty():
                    # If overlapping with this range, put into queue
                    for val in self.items[i]:
                        if val not in vals_inds_dict:
                            yield_vals.append(val)
                            vals_inds_dict[val] = deque()
                        vals_inds_dict[val].append(i)
            except ValueError:
                # Continue if no overlap with this range
                continue
        ## Yield remaining values
        while len(yield_vals) > 0:
            # Yield the full range, value. Remove value from queue
            val = yield_vals.popleft()
            yield Range(max(self.lower_cuts[vals_inds_dict[val][0]], start),
                        min(self.upper_cuts[vals_inds_dict[val][-1]], end)), val
            # Remove value from dict
            del vals_inds_dict[val]

    def get(self, key):
        """ Get the item(s) corresponding to a given key. The key can be a
        Range or a single value that is within a Range

        Parameters
        ----------
        key : comparable
            A single value or Range object

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
            ovlapLowerInd = max(bisect_left(self.lower_cuts, key.lower_cut) - 1, 0)
            ovlapUpperInd = bisect_left(self.lower_cuts, key.upper_cut)
            for i in range(ovlapLowerInd, ovlapUpperInd):
                try:
                    # Get intersection of the ranges
                    intersect = key.intersection(self.ranges[i])
                    if not intersect.is_empty():
                        # If overlapping with this range, put its
                        # item in the return set
                        return_set = return_set.union(self.items[i])
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
            return self.items[lower_ind]

    def put(self, key, val):
        """ Creates a mapping from a Range to a value, adding to
        any existing values over that Range

        Parameters
        ----------
        key : Range object
            A Range to serve as a key
        val : value, hashable
            Some value that the Range should map to

        Raises
        ------
        TypeError
            If the key is not a Range object or value is not hashable
        """
        if not isinstance(key, Range):
            raise TypeError("key is not a Range")
        elif not any((isinstance(val, Hashable), self.recurse_add)):
            raise TypeError("value not hashable")
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
            if not isinstance(val, set):
                self.items.insert(insert_ind, set([val]))
            else:
                self.items.insert(insert_ind, val)
            return
        else:
            # If this range has some overlap with existing ranges
            ovlap_lower_ind = max(bisect_left(self.lower_cuts, key.lower_cut) - 1, 0)
            ovlap_upper_ind = bisect_left(self.lower_cuts, key.upper_cut)
            # Create queue ranges to add
            add_ranges = deque()
            # Create queue of items to add
            add_items = deque()
            # Keep track of next lower cutpoint to add
            next_lower_cut = key.lower_cut
            for i in range(ovlap_lower_ind, ovlap_upper_ind):
                try:
                    # Get intersection of the ranges
                    intersect = key.intersection(self.ranges[i])
                    if not intersect.is_empty():
                        # Add in a Range between the next LowerCut and
                        # the beginning of this intersection if necessary
                        if next_lower_cut < intersect.lower_cut:
                            add_ranges.append(Range(next_lower_cut, intersect.lower_cut))
                            add_items.append(val)
                            next_lower_cut = intersect.lower_cut
                        if intersect == self.ranges[i]:
                            ## If key encompassing existing Range ##
                            # Add item to this range
                            self.items[i].add(val)
                            # Change the next lower cut
                            next_lower_cut = intersect.upper_cut
                        elif self.lower_cuts[i] == intersect.lower_cut:
                            ## If key upper cutpoint enclosed by existing Range ##
                            # Add in the rest of the original Range
                            if self.upper_cuts[i] > intersect.upper_cut:
                                add_ranges.append(Range(intersect.upper_cut,
                                                       self.upper_cuts[i]))
                                add_items.append(set(self.items[i]))
                            # Define original part to be shorter                            
                            self.upper_cuts[i] = intersect.upper_cut
                            self.ranges[i] = Range(self.lower_cuts[i],
                                                   intersect.upper_cut)
                            self.items[i].add(val)
                            # Change the next lower cut
                            next_lower_cut = intersect.upper_cut
                        elif self.upper_cuts[i] == intersect.upper_cut:
                            ## If key lower cutpoint enclosed by existing Range ##
                            # Add in the rest of the original Range
                            if intersect.lower_cut > self.lower_cuts[i]:
                                add_ranges.append(Range(self.lower_cuts[i], intersect.lower_cut))
                                add_items.append(set(self.items[i]))
                            # Define original part to be shorter
                            self.lower_cuts[i] = intersect.lower_cut
                            self.ranges[i] = Range(self.lower_cuts[i],
                                                   intersect.upper_cut)
                            self.items[i].add(val)
                            # Change the next lower cut
                            next_lower_cut = intersect.upper_cut
                        else:
                            # If entire key enclosed by existing Range
                            # Add in lower part of original Range
                            add_ranges.append(Range(self.lower_cuts[i], intersect.lower_cut))
                            add_items.append(set(self.items[i]))
                            # Add in upper part of original Range
                            add_ranges.append(Range(intersect.upper_cut, self.upper_cuts[i]))
                            add_items.append(set(self.items[i]))
                            # Define original part to be middle
                            self.lower_cuts[i] = intersect.lower_cut
                            self.upper_cuts[i] = intersect.upper_cut
                            self.ranges[i] = Range(intersect.lower_cut, intersect.upper_cut)
                            self.items[i].add(val)
                            # Change the next lower cut
                            next_lower_cut = intersect.upper_cut
                except ValueError:
                    # Continue if no overlap with this range
                    continue
            # Put in a last range if necessary
            if next_lower_cut < key.upper_cut:
                add_ranges.append(Range(next_lower_cut, key.upper_cut))
                add_items.append(val)
            # Use recursive call to place the pairs, which now
            # should not overlap with any other ranges
            self.recurse_add = True
            while len(add_ranges) > 0:
                self.put(add_ranges.pop(), add_items.pop())
            self.recurse_add = False

    def remove(self, a_range):
        """ Removes a range and its value(s) from the range set

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
                            add_items.append(set(self.items[i]))
                            add_ranges.append(Range(intersect.upper_cut,
                                                   self.upper_cuts[i]))
                            add_items.append(set(self.items[i]))
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
            self.recurse_add = True
            while len(add_ranges) > 0:
                self.put(add_ranges.pop(), add_items.pop())
            self.recurse_add = False
