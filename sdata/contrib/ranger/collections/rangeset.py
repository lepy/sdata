from bisect import bisect_left
from collections import deque
from sdata.contrib.ranger.range.range import Range


class RangeSet(object):
    """ Class used to represent a set of non-overlapping ranges of the
    same type. If a range is added that is connected to another range
    already in the set, those ranges are merged. Otherwise, it is added as
    a new range in the set
    """

    def __init__(self, ranges=None):
        """ Instantiates the RangeSet

        Parameters
        ----------
        ranges : List of Range objects
            Ranges to add to the Set
        """
        ## Holds lower and upper cut points of ranges
        self.lower_cuts = []
        self.upper_cuts = []
        ## Holds the range objects in the set
        self.ranges = []
        if ranges is not None:
            for aRange in ranges:
                self.add(aRange)

    def __repr__(self):
        if len(self) < 6:
            return "RangeSet(%s)" % ", ".join(map(str, self.ranges))
        else:
            return "RangeSet(%s, ..., %s)" % (", ".join(map(str, self.ranges[:2])),
                                              ", ".join(map(str, self.ranges[-2:])))

    def __len__(self):
        return len(self.ranges)

    def __iter__(self):
        return iter(self.ranges)

    def __eq__(self, other):
        if not isinstance(other, RangeSet):
            return False
        elif len(self) != len(other):
            return False
        else:
            for r1, r2 in zip(self.ranges, other.ranges):
                if r1 != r2: return False
            return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def add(self, a_range):
        """ Adds a range to the range set. If this range is not connected
        to any current ranges, it will place the new range on its own. If
        there is a connection, any connected ranges will be merged into a single
        range

        Parameters
        ----------
        a_range : A Range object
            The Range to add to the RangeSet

        Raises
        ------
        ValueError
            If adding range of type not compatible with previously
            added ranges
        TypeError:
            If not adding a Range
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
        # Get the insertion point (where the lower bound should go), should
        # this range be added on its own
        lower_ind = bisect_left(self.lower_cuts, a_range.lower_cut)
        if len(self) == 0:
            # Add on its own if there is nothing in the list
            self.ranges.append(a_range)
            self.lower_cuts.append(a_range.lower_cut)
            self.upper_cuts.append(a_range.upper_cut)
        elif len(self) == lower_ind:
            if not a_range.is_connected(self.ranges[max(lower_ind - 1, 0)]):
                # Add on its own if not connected to previous and last
                self.ranges.insert(lower_ind, a_range)
                self.lower_cuts.insert(lower_ind, a_range.lower_cut)
                self.upper_cuts.insert(lower_ind, a_range.upper_cut)
            else:
                # If connected with the range below, replace with new range
                new_lower_cut = min(a_range.lower_cut,
                                    self.lower_cuts[max(lower_ind - 1, 0)])
                new_upper_cut = max(a_range.upper_cut,
                                    self.upper_cuts[max(lower_ind - 1, 0)])
                new_range = Range(new_lower_cut, new_upper_cut)
                self.ranges[-1] = new_range
                self.lower_cuts[-1] = new_lower_cut
                self.upper_cuts[-1] = new_upper_cut
        elif not any((a_range.is_connected(self.ranges[max(lower_ind - 1, 0)]),
                      a_range.is_connected(self.ranges[lower_ind]))):
            # Add on its own if not connected
            self.ranges.insert(lower_ind, a_range)
            self.lower_cuts.insert(lower_ind, a_range.lower_cut)
            self.upper_cuts.insert(lower_ind, a_range.upper_cut)
        elif a_range.is_connected(self.ranges[max(lower_ind - 1, 0)]):
            # If connected with range below
            new_lower_cut = min(self.lower_cuts[max(lower_ind - 1, 0)],
                                a_range.lower_cut)
            new_upper_cut = max(a_range.upper_cut,
                                self.upper_cuts[max(lower_ind - 1, 0)])
            remove_count = 1
            if len(self) == (lower_ind):
                # If hitting the last range, take the maximum uppercut
                new_upper_cut = max(new_upper_cut, self.upper_cuts[max(lower_ind - 1, 0)])
            else:
                # If not hitting the last range, go find the upper cut
                for i in range(max(1, lower_ind), len(self)):
                    if a_range.is_connected(self.ranges[i]):
                        new_upper_cut = max(new_upper_cut, self.upper_cuts[i])
                        remove_count += 1
                    else:
                        break
            # Make the new range
            new_range = Range(new_lower_cut, new_upper_cut)
            # Get rid of all overlapping ranges
            for i in range(remove_count):
                self.ranges.pop(max(lower_ind - 1, 0))
                self.lower_cuts.pop(max(lower_ind - 1, 0))
                self.upper_cuts.pop(max(lower_ind - 1, 0))
            # Add the new range
            self.ranges.insert(max(lower_ind - 1, 0), new_range)
            self.lower_cuts.insert(max(lower_ind - 1, 0), new_range.lower_cut)
            self.upper_cuts.insert(max(lower_ind - 1, 0), new_range.upper_cut)
        elif a_range.is_connected(self.ranges[lower_ind]):
            # If connected with the range above
            new_lower_cut = min(a_range.lower_cut, self.lower_cuts[lower_ind])
            new_upper_cut = max(a_range.upper_cut, self.upper_cuts[lower_ind])
            remove_count = 0
            if len(self) == (lower_ind + 1):
                # If hitting the last range, you're done
                remove_count += 1
            else:
                # Go find the upper cut
                for i in range(lower_ind, len(self)):
                    if a_range.is_connected(self.ranges[i]):
                        new_upper_cut = max(new_upper_cut, self.upper_cuts[i])
                        remove_count += 1
                    else:
                        break
            # Make the new range
            new_range = Range(new_lower_cut, new_upper_cut)
            # Remove the overlapping ranges
            for i in range(remove_count):
                self.ranges.pop(lower_ind)
                self.lower_cuts.pop(lower_ind)
                self.upper_cuts.pop(lower_ind)
            # Add the new range
            self.ranges.insert(lower_ind, new_range)
            self.lower_cuts.insert(lower_ind, new_range.lower_cut)
            self.upper_cuts.insert(lower_ind, new_range.upper_cut)

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
            lower_ind = max(bisect_left(self.lower_cuts, val.lower_cut), 0)
            if lower_ind >= len(self.lower_cuts):
                return self.ranges[lower_ind - 1].encloses(val)
            elif val.lower_cut != self.lower_cuts[lower_ind]:
                return self.ranges[lower_ind - 1].encloses(val)
            else:
                return self.ranges[lower_ind].encloses(val)
        else:
            lower_ind = max(bisect_left(self.lower_cuts, val) - 1, 0)
            return self.ranges[lower_ind].contains(val)

    def difference(self, otherSet):
        """ Creates a new RangeSet in which all elements in another RangeSet
        are taken out of this RangeSet

        Parameters
        ----------
        otherSet : RangeSet object
            The RangeSet used for this difference

        Raises
        ------
        TypeError
            If the object passed in is not a RangeSet
        ValueError
            If the value type of the ranges in the other set not compatible
            with the range's values

        Returns
        -------
        RangeSet consisting of the difference of the two sets
        """
        if not isinstance(otherSet, RangeSet):
            raise TypeError("other_set is not a RangeSet")
        new_set = RangeSet()
        for add_range in self.ranges:
            if otherSet.overlaps(add_range):
                # Determine where overlap occurs
                other_lower_ind = max(bisect_left(otherSet.lower_cuts,
                                                  add_range.lower_cut) - 1, 0)
                other_upper_ind = bisect_left(otherSet.lower_cuts,
                                              add_range.upper_cut)
                new_lower_cut = add_range.lower_cut
                new_upper_cut = add_range.upper_cut
                add = True
                for i in range(other_lower_ind, other_upper_ind):
                    try:
                        # Get the intersection of the ranges
                        intersect = add_range.intersection(otherSet.ranges[i])
                        if not intersect.is_empty():
                            if add_range == intersect:
                                add = False
                                break
                            elif add_range.lower_cut == intersect.lower_cut:
                                # If equal on the left cutpoint, subtract out left
                                # part
                                new_lower_cut = intersect.upper_cut
                                add_range = Range(new_lower_cut, new_upper_cut)
                            elif add_range.upper_cut == intersect.upper_cut:
                                # If equal on right cutpoint, subtract out right
                                # part
                                new_upper_cut = intersect.lower_cut
                                add_range = Range(add_range.lower_cut, new_upper_cut)
                            else:
                                # If in the middle, split into two parts and
                                # add the lower one immediately
                                new_set.add(Range(new_lower_cut,
                                                  intersect.lower_cut))
                                new_lower_cut = intersect.upper_cut
                                new_upper_cut = add_range.upper_cut
                                add_range = Range(new_lower_cut, new_upper_cut)
                    except ValueError:
                        continue
                if add:
                    new_set.add(Range(new_lower_cut, new_upper_cut))
            else:
                new_set.add(add_range)
        return new_set

    def intersection(self, other_set):
        """ Creates a new RangeSet that is the intersection of this and
        another RangeSet

        Parameters
        ----------
        other_set : RangeSet object
            The RangeSet used for this intersection

        Raises
        ------
        TypeError
            If the object passed in is not a RangeSet
        ValueError
            If the value type of the ranges in the other set not compatible
            with the range's values

        Returns
        -------
        RangeSet consisting of the intersection of the two sets
        """
        if not isinstance(other_set, RangeSet):
            raise TypeError("other_set is not a RangeSet")
        new_set = RangeSet()
        for addRange in self.ranges:
            if other_set.overlaps(addRange):
                # Determine where overlap occurs
                other_lower_ind = max(bisect_left(other_set.lower_cuts,
                                                  addRange.lower_cut) - 1, 0)
                other_upper_ind = bisect_left(other_set.lower_cuts,
                                              addRange.upper_cut)
                for i in range(other_lower_ind, other_upper_ind):
                    # Get the intersection of the ranges
                    try:
                        intersect = addRange.intersection(other_set.ranges[i])
                        # Add intersection if there is any overlap
                        if not intersect.is_empty():
                            new_set.add(intersect)
                    except ValueError:
                        continue
        return new_set

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

    def remove(self, a_range):
        """ Removes a range from the range set. 

        Parameters
        ----------
        a_range : A Range object
            The Range to remove from the RangeSet

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
                               self.ranges[0].lower_cut.the_type) or issubclass(self.ranges[0].lower_cut.the_type,
                                                                                a_range.lower_cut.the_type)):
                raise ValueError("Range not compatible with previously added ranges")
        # Check if the range actually overlaps with this set
        if not self.overlaps(a_range):
            return
        else:
            # There's some overlap, so deal with that
            # Determine where overlap occurs
            ovlap_lower_ind = max(bisect_left(self.lower_cuts, a_range.lower_cut) - 1, 0)
            ovlap_upper_ind = bisect_left(self.lower_cuts, a_range.upper_cut)
            # Create queue of indices marked for removal
            remove_ranges = deque()
            # Create queue of ranges to add
            add_ranges = deque()
            for i in range(ovlap_lower_ind, ovlap_upper_ind):
                try:
                    # Get intersection of the ranges
                    intersect = a_range.intersection(self.ranges[i])
                    if not intersect.is_empty():
                        if intersect == self.ranges[i]:
                            # Mark range for removal
                            remove_ranges.append(i)
                        elif self.lower_cuts[i] == intersect.lower_cut:
                            # If equal on the left cutpoint, subtract out left
                            # part
                            self.lower_cuts[i] = intersect.upper_cut
                            self.ranges[i] = Range(intersect.upper_cut, self.upper_cuts[i])
                        elif self.upper_cuts[i] == intersect.upper_cut:
                            # If equal on right cutpoint, subtract out right
                            # part
                            self.upper_cuts[i] = intersect.lower_cut
                            self.ranges[i] = Range(self.lower_cuts[i], intersect.lower_cut)
                        else:
                            # If in the middle, split into two parts, putting both into
                            # add queue and placing the old range index into the removal
                            # queue
                            add_ranges.append(Range(self.lower_cuts[i], intersect.lower_cut))
                            add_ranges.append(Range(intersect.upper_cut, self.upper_cuts[i]))
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
            # Add any ranges that need to be added
            while len(add_ranges) > 0:
                self.add(add_ranges.pop())

    def union(self, other_set):
        """ Creates a new RangeSet that is the union of this set and
        another RangeSet object

        Parameters
        ----------
        other_set : RangeSet object
            The RangeSet used for the union

        Raises
        ------
        TypeError
            If the object passed in is not a RangeSet
        ValueError
            If the value type of the set not compatible with the ranges

        Returns
        -------
        RangeSet consisting of union of two sets
        """
        if not isinstance(other_set, RangeSet):
            raise TypeError("other_set is not a RangeSet")
        return RangeSet(set(self.ranges + other_set.ranges))

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
