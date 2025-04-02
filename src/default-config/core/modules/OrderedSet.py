
# Standard typing imports for aps
import collections.abc as _a
import abc as _abc
import typing as _ty
import types as _ts

T = _ty.TypeVar('T')

# Docs generated with Github Copilot


class OrderedSet(_ty.Generic[T]):
    def __init__(self, iterable: _ty.Iterable = None) -> None:
        """
        OrderedSet is a hybrid of list and set. It maintains the order of elements like a list and ensures that each
        element is unique like a set. It is implemented using a list and a set. The list maintains the order of elements
        and the set ensures that each element is unique. The list is used to maintain the order of elements and the set is
        used to check if an element is already present in the OrderedSet."""
        self._items: list[T] = []
        self._seen: set[T] = set()
        if iterable:
            for item in iterable:
                self.add(item)

    def add(self, item: T) -> None:
        """
        Adds an item to the OrderedSet if it is not already present in the OrderedSet.
        :param item: The item to be added to the OrderedSet.
        :return: None
        """
        if item not in self._seen:
            self._items.append(item)
            self._seen.add(item)

    def discard(self, item: T) -> None:
        """
        Removes an item from the OrderedSet if it is present in the OrderedSet.
        :param item: The item to be removed from the OrderedSet.
        :return: None
        """
        if item in self._seen:
            self._items.remove(item)
            self._seen.remove(item)

    def remove(self, item: T) -> None:
        """
        Removes an item from the OrderedSet if it is present in the OrderedSet. If the item is not present in the
        OrderedSet, a KeyError is raised.
        :param item: The item to be removed from the OrderedSet.
        :return: None
        """
        if item not in self._seen:
            raise KeyError(f"{item} not in OrderedSet")
        self.discard(item)

    def clear(self) -> None:
        """
        Removes all items from the OrderedSet.
        :return: None
        """
        self._items.clear()
        self._seen.clear()

    def get_index(self, item: T) -> int:
        """
        Returns the index of an item in the OrderedSet.
        :param item: The item whose index is to be returned.
        :return: The index of the item in the OrderedSet.
        """
        return self._items.index(item)

    def get_by_index(self, index: int) -> T:
        """
        Returns the item at a given index in the OrderedSet.
        :param index: The index of the item to be returned.
        :return: The item at the given index in the OrderedSet.
        """
        return self._items[index]

    def to_list(self) -> list[T]:
        """
        Returns the items in the OrderedSet as a list.
        :return: The items in the OrderedSet as a list.
        """
        return self._items

    def to_set(self) -> set[T]:
        """
        Returns the items in the OrderedSet as a set.
        :return: The items in the OrderedSet as a set.
        """
        return self._seen

    @staticmethod
    def from_list(lst: _ty.List[T]) -> 'OrderedSet':
        return OrderedSet(lst)

    @staticmethod
    def from_set(st: _ty.Set[T]) -> 'OrderedSet':
        return OrderedSet(st)

    def __len__(self):
        """
        Returns the number of items in the OrderedSet.
        :return: The number of items in the OrderedSet.
        """
        return len(self._items)

    def __iter__(self):
        """
        Returns an iterator over the items in the OrderedSet.
        :return: An iterator over the items in the OrderedSet.
        """
        return iter(self._items)

    def __contains__(self, item: T):
        """
        Returns True if an item is present in the OrderedSet, False otherwise.
        :param item: The item to be checked for presence in the OrderedSet.
        :return: True if the item is present in the OrderedSet, False otherwise.
        """
        return item in self._seen

    def __repr__(self):
        """
        Returns a string representation of the OrderedSet.
        :return: A string representation of the OrderedSet.
        """
        return f"OrderedSet({self._items})"

    def __eq__(self, other):
        """
        Returns True if the OrderedSet is equal to another OrderedSet, False otherwise.
        :param other: The other OrderedSet to be compared with.
        :return: True if the OrderedSet is equal to the other OrderedSet, False otherwise.
        """
        if isinstance(other, OrderedSet):
            return self._items == other._items
        return False

    def __or__(self, other):
        """
        Returns the union of the OrderedSet with another OrderedSet or set.
        :param other: The other OrderedSet or set to be unioned with.
        :return: The union of the OrderedSet with the other OrderedSet or set.
        """
        if not isinstance(other, (OrderedSet, set)):
            return NotImplemented
        return OrderedSet(self._items + [item for item in other if item not in self])

    def __and__(self, other):
        """
        Returns the intersection of the OrderedSet with another OrderedSet or set.
        :param other: The other OrderedSet or set to be intersected with.
        :return: The intersection of the OrderedSet with the other OrderedSet or set.
        """
        if not isinstance(other, (OrderedSet, set)):
            return NotImplemented
        return OrderedSet(item for item in self if item in other)

    def __sub__(self, other):
        """
        Returns the difference of the OrderedSet with another OrderedSet or set.
        :param other: The other OrderedSet or set to be differenced with.
        :return: The difference of the OrderedSet with the other OrderedSet or set.
        """
        if not isinstance(other, (OrderedSet, set)):
            return NotImplemented
        return OrderedSet(item for item in self if item not in other)

