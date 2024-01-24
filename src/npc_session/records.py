from __future__ import annotations

import datetime
import re
import typing
from typing import Any, ClassVar, Protocol, TypeVar

from typing_extensions import Self

import npc_session.parsing as parsing


@typing.runtime_checkable
class SupportsID(Protocol):
    @property
    def id(self) -> int | str:
        ...


T = TypeVar("T", int, str)


class MetadataRecord:
    """A base class for definitions of unique metadata records
    (unique amongst that type of metadata, not necessarily globally).

    Intended use is for looking-up and referring to metadata components
    in databases, regardless of the backend.

    Each implementation should:
    - accept a variety of input formats
    - parse, normalize, then validate input
    - give a single consistent representation (`id`)
    - store `id` as an int or str, "immutable" after init

    Instances are effectively the same as their stored `id` attribute, but with extra
    properties, including magic methods for str, equality, hashing and ordering:

    >>> a = MetadataRecord(1)
    >>> a
    1
    >>> str(a)
    '1'
    >>> a == 1 and a == '1'
    True
    >>> isinstance(a, (int, str))
    False
    >>> b = MetadataRecord(1)
    >>> c = MetadataRecord(2)
    >>> a == b
    True
    >>> a == c
    False
    >>> sorted([c, b])
    [1, 2]
    >>> a == MetadataRecord(a)
    True
    >>> MetadataRecord(1).id = 2
    Traceback (most recent call last):
    ...
    AttributeError: MetadataRecord.id is read-only
    """

    valid_id_regex: ClassVar[str] = r"[a-zA-Z0-9-_: ]+"

    def __init__(self, value: int | str) -> None:
        self.id = value

    @classmethod
    def parse_id(cls, value: Any) -> int | str:
        """Pre-validation. Handle any parsing or casting to get to the stored type."""
        if isinstance(value, (SupportsID,)):
            value = value.id
        return value

    @classmethod
    def validate_id(cls, value: Any) -> None:  # pragma: no cover
        """Post-parsing. Raise ValueError if not a valid value for this type of metadata record."""
        if isinstance(value, int):
            if value < 0:
                raise ValueError(
                    f"{cls.__name__}.id must be non-negative, not {value!r}"
                )
        if isinstance(value, str):
            if not re.match(cls.valid_id_regex, value):
                raise ValueError(
                    f"{cls.__name__}.id must match {cls.valid_id_regex}, not {value!r}"
                )

    @property
    def id(self) -> int | str:
        """A unique identifier for the object.
        Read-only, and type at assignment is preserved.
        """
        return self._id

    @id.setter
    def id(self, value: int | str) -> None:
        """A unique identifier for the object.
        Write-once, then read-only. Type at assignment is preserved.
        """
        if hasattr(self, "_id"):
            raise AttributeError(f"{self.__class__.__name__}.id is read-only")
        value = self.parse_id(value)
        self.validate_id(value)
        self._id = value

    def __repr__(self) -> str:
        return repr(self.id)

    def __str__(self) -> str:
        return str(self.id)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: Any) -> bool:
        try:
            # allow comparison of obj with str or int, via obj.id
            return str(self) == str(other)
        except TypeError:  # pragma: no cover
            return NotImplemented

    def __lt__(self, other: Any) -> bool:
        try:
            return str(self) < str(other)
        except TypeError:  # pragma: no cover
            return NotImplemented


class StrRecord(MetadataRecord, str):
    id: str

    def __new__(cls, content) -> Self:
        return super().__new__(cls, cls.parse_id(content))


class IntRecord(MetadataRecord, int):
    id: int

    def __new__(cls, content) -> Self:
        return super().__new__(cls, cls.parse_id(content))


class ProjectRecord(StrRecord):
    """To uniquely define a project we need:
    - `id`: a descriptive string or acronym

    >>> project = ProjectRecord('DR')
    >>> project
    'DR'
    >>> project == 'DR'
    True
    >>> isinstance(project, str)
    True
    """

    valid_id_regex = r"[a-zA-Z0-9-_.]+"


class SubjectRecord(IntRecord):
    """To uniquely define a subject we need:
    - `id`: labtracks MID

    >>> subject = SubjectRecord('366122')
    >>> subject = SubjectRecord(366122)
    >>> subject
    366122
    >>> subject == 366122 and subject == '366122'
    True
    >>> isinstance(subject, int)
    True
    >>> hash(subject) == hash(366122)
    True
    """

    valid_id_regex = parsing.VALID_SUBJECT

    @classmethod
    def parse_id(cls, value: int | str) -> int:
        return int(super().parse_id(int(str(value))))


class ProbeRecord(StrRecord):
    """Probe records stored as A-F

    >>> ProbeRecord('A')
    'A'
    >>> ProbeRecord('A').name
    'probeA'
    >>> ProbeRecord('testB Probe A2 sessionC')
    'A'
    >>> ProbeRecord('366122_2021-06-01_10:12:03_3')
    Traceback (most recent call last):
    ...
    ValueError: ProbeRecord requires a string containing `probe` followed by a letter A-F, not '366122_2021-06-01_10:12:03_3'
    >>> 'A' == ProbeRecord('probeA')
    True
    >>> 'probeA' == ProbeRecord('probeA')
    False
    >>> 'A' in {ProbeRecord('probeA')}
    True
    >>> ProbeRecord('probeA') in {'A'}
    True
    """

    valid_id_regex: ClassVar[str] = parsing.VALID_PROBE_LETTER

    @classmethod
    def parse_id(cls, value: str) -> str:
        letter = parsing.extract_probe_letter(str(value))
        if letter is None:
            raise ValueError(
                f"{cls.__name__} requires a string containing `probe` followed by a letter A-F, or a single capital A-F alone, not {value!r}"
            )
        return letter

    @property
    def name(self) -> str:
        return f"probe{self.id}"


class DateRecord(StrRecord):
    """Date records are stored in isoformat with hyphen seperators.

    >>> DateRecord('2022-04-25')
    '2022-04-25'
    >>> DateRecord('20220425')
    '2022-04-25'
    >>> date = DateRecord('20220425')
    >>> datetime.date.fromisoformat(str(date))
    datetime.date(2022, 4, 25)

    Components of date are also made available:
    >>> date.year, date.month, date.day
    (2022, 4, 25)
    """

    valid_id_regex: ClassVar[str] = parsing.VALID_DATE
    """A valid date this century, format YYYY-MM-DD."""

    @property
    def dt(self) -> datetime.date:
        return datetime.date.fromisoformat(self.id)

    @classmethod
    def parse_id(cls, value: int | str | datetime.datetime) -> str:
        date = parsing.extract_isoformat_date(str(value))
        if date is None:
            raise ValueError(
                f"{cls.__name__} requires a date YYYY-MM-DD with optional separators, not {value!r}"
            )
        return str(super().parse_id(date))

    @classmethod
    def validate_id(cls, value: str) -> None:
        """
        >>> DateRecord.validate_id('2002-04-25')
        Traceback (most recent call last):
        ...
        ValueError: Invalid year: 2002
        """
        super().validate_id(value)
        dt = datetime.date.fromisoformat(value.split(" ")[0].split("T")[0])
        # split so this same method can be used for datetime subclass
        if not 2015 < dt.year <= datetime.datetime.now().year:
            raise ValueError(f"Invalid year: {dt.year}")

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("month", "year", "day", "resolution"):
            return self.dt.__getattribute__(__name)
        return super().__getattribute__(__name)


class DatetimeRecord(DateRecord):
    """Datetime records are stored in isoformat with a resolution of seconds,
    and space separator between date/time, hyphen between date components, colon
    between time components.

    >>> dt = DatetimeRecord('2022-04-25 15:02:37')
    >>> dt = DatetimeRecord('366122_20220425_150237_2')
    >>> dt
    '2022-04-25 15:02:37'
    >>> str(dt)
    '2022-04-25 15:02:37'
    >>> dt.dt
    datetime.datetime(2022, 4, 25, 15, 2, 37)

    Components of datetime are also made available:
    >>> dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
    (2022, 4, 25, 15, 2, 37)
    """

    valid_id_regex: ClassVar[str] = parsing.VALID_DATETIME
    """A valid datetime this century, format YYYY-MM-DD HH:MM:SS"""

    @property
    def dt(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self.id)

    @classmethod
    def parse_id(cls, value: int | str | datetime.datetime) -> str:
        date = super().parse_id(value)
        time = parsing.extract_isoformat_time(str(value))
        return f"{date} {time}"

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("hour", "minute", "second", "resolution"):
            return self.dt.__getattribute__(__name)
        return super().__getattribute__(__name)


class TimeRecord(StrRecord):
    """Time records are stored in isoformat with a resolution of seconds.

    >>> TimeRecord('15:02:37')
    '15:02:37'
    >>> TimeRecord('15:02:37.123') == TimeRecord(150237)
    True
    >>> TimeRecord('25:02:37')
    Traceback (most recent call last):
    ...
    ValueError: Invalid time: 25:02:37
    """

    valid_id_regex: ClassVar[str] = parsing.VALID_TIME
    """A valid time, format HH:MM:SS"""

    @property
    def dt(self) -> datetime.time:
        return datetime.time.fromisoformat(self.id)

    @classmethod
    def parse_id(cls, value: int | str | datetime.datetime) -> str:
        time = parsing.extract_isoformat_time(str(value))
        if time is None:
            raise ValueError(
                f"{cls.__name__} requires a time HH:MM:SS with optional separators, not {value!r}"
            )
        return time

    @classmethod
    def validate_id(cls, value: str) -> None:
        """
        >>> TimeRecord.validate_id('15:02:37')
        >>> TimeRecord.validate_id('15:02:37.123456')
        >>> TimeRecord.validate_id('25:02:37.123456')
        Traceback (most recent call last):
        ...
        ValueError: Invalid time: 25:02:37.123
        """
        try:
            datetime.time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Invalid time: {value}") from exc

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("hour", "minute", "second", "resolution"):
            return self.dt.__getattribute__(__name)
        return super().__getattribute__(__name)


class SessionRecord(StrRecord):
    """To uniquely define a subject we need:
    - `id`: a multipart underscore-separated str corresponding to:

        <subject_id>_<date>_<idx [optional]>

        where:
        - `date` is in format YYYY-MM-DD, with optional separators (hyphen, slash)
        - `idx` corresponds to the index of the session on that date for that
        subject
        - `idx` must be appended as the last component, separated by an underscore
        - if the last component is missing, it is implicitly assumed to be the only
        session on the date for that subject
        - `idx` currently isn't needed, but is included for future-proofing
        - varname `idx` is used to avoid conflicts with `index` methods in
        possible base classes

    Record provides:
    - normalized id
    - subject record
    - date record
    - idx (0 if not specified)

    We can extract these components from typical session identifiers, such as
    folder names, regardless of component order:
    >>> a = SessionRecord('DRPilot_366122_20220425')
    >>> b = SessionRecord('0123456789_366122_20220425')
    >>> c = SessionRecord('366122_2022-04-25')
    >>> d = SessionRecord('2022-04-25_12:00:00_366122')
    >>> a
    '366122_2022-04-25'
    >>> a == b == c == d
    True

    Components are also available for use:
    >>> a.subject, a.date, a.idx
    (366122, '2022-04-25', 0)
    >>> a.date.year, a.date.month, a.date.day
    (2022, 4, 25)

    Missing index is synonymous with idx=0. The default behavior
    is to hide a null index, since they're not currently used:
    >>> SessionRecord('366122_2022-04-25').idx
    0
    >>> SessionRecord('366122_2022-04-25_1').idx
    1

    `idx`, like other properties, is read-only.
    Use `with_idx` to create a new instance:
    >>> a = SessionRecord('366122_2022-04-25_1')
    >>> a.with_idx(2)
    '366122_2022-04-25_2'
    >>> a is not a.with_idx(2)
    True

    Subject and date are validated on init:
    - subject must be a recent or near-future labtracks MID:
    >>> SessionRecord('1_2022-04-25')
    Traceback (most recent call last):
    ...
    ValueError: SessionRecord.id must be in format <subject_id>_<date>_<idx [optional]>

    - date must be a valid recent or near-future date:
    >>> SessionRecord('366122_2022-13-25')
    Traceback (most recent call last):
    ...
    ValueError: SessionRecord.id must be in format <subject_id>_<date>_<idx
    [optional]>

    Comparisons are based on the session's normalized id:
    >>> assert SessionRecord('366122_2022-04-25_0') == '366122_2022-04-25'
    >>> assert SessionRecord('366122_2022-04-25') == '366122_2022-04-25_0'
    >>> a = {SessionRecord('366122_2022-04-25_0')}

    Validator can also be used to check if a string is a valid session id:
    >>> SessionRecord.validate_id('366122_2022-04-25_0') == None
    True
    >>> SessionRecord.validate_id('366122_2022-99-25_0') == None
    Traceback (most recent call last):
    ...
    ValueError: SessionRecord.id must match SessionRecord.valid_id_regex

    >>> a = SessionRecord('DRPilot_366122_20220425')
    >>> assert a[:] in a.id, f"slicing should access {a.id[:]=} , not the original value passed to init {a[:]=}"

    # hashes match string with idx
    >>> assert '366122_2022-04-25_0' in {SessionRecord('366122_2022-04-25')}
    """

    id: str

    valid_id_regex: ClassVar = parsing.VALID_SESSION_ID

    display_null_idx = False
    """Whether to show `_0` when a session index is 0.
    False as long as each subject has only one session per day."""

    @classmethod
    def parse_id(cls, value: Any) -> str:
        value = parsing.extract_session_id(str(value), include_null_index=True)
        split = value.split("_")
        if len(split) < 3:
            value = f"{value}_0"
        return str(super().parse_id(value))

    @property
    def subject(self) -> SubjectRecord:
        return SubjectRecord(self.id.split("_")[0])

    @property
    def date(self) -> DateRecord:
        return DateRecord(self.id.split("_")[1])

    @property
    def idx(self) -> int:
        return int(self.id.split("_")[-1])

    def __str__(self) -> str:
        if self.idx == 0 and not self.display_null_idx:
            return "_".join(self.id.split("_")[:2])
        return self.id

    def __repr__(self) -> str:
        return repr(str(self))

    def with_idx(self, idx: int) -> SessionRecord:
        """Return a new instance with specified idx.

        >>> SessionRecord('366122_2022-04-25_0').with_idx(1)
        '366122_2022-04-25_1'
        >>> SessionRecord('366122_2022-04-25').with_idx(1)
        '366122_2022-04-25_1'

        If `idx` is unchanged, self is returned:
        >>> SessionRecord('366122_2022-04-25').with_idx(0)
        '366122_2022-04-25'
        >>> SessionRecord('366122_2022-04-25_1').with_idx(1) # no change
        '366122_2022-04-25_1'
        """
        if idx == self.idx:
            return self
        return SessionRecord(f"{self.subject}_{self.date}_{idx or self.idx}")

    def __eq__(self, other: Any) -> bool:
        """
        >>> assert SessionRecord('366122_2022-04-25') == SessionRecord('366122_2022-04-25')
        >>> assert SessionRecord('366122_2022-04-25_0') == SessionRecord('366122_2022-04-25')
        >>> assert SessionRecord('366122_2022-04-25_1') == SessionRecord('366122_2022-04-25_1')

        >>> assert SessionRecord('366122_2022-04-25_0') != '366122_2022-04-25_1'

        Missing index is the same as _0:
        >>> assert SessionRecord('366122_2022-04-25_0') == '366122_2022-04-25'

        Comparison possible with stringable types:
        >>> assert SessionRecord('366122_2022-04-25') == MetadataRecord('366122_2022-04-25')

        False for comparison with non-stringable types:
        >>> assert SessionRecord('366122_2022-04-25') != 366122

        >>> assert SessionRecord('366122_2022-04-25_0')  == '366122_2022-04-25'
        >>> assert SessionRecord('366122_2022-04-25_0') == '366122_2022-04-25_12:00:00'
        >>> assert SessionRecord('366122_2022-04-25_0') == '2022-04-25_12:00:00_366122'
        >>> assert SessionRecord('366122_2022-04-25_0') != '366122_2022-04-25_12:00:00_1'
        """
        if not isinstance(other, self.__class__):
            try:
                return self == SessionRecord(str(other))
            except (ValueError, TypeError):
                return False
        return super().__eq__(other)

    def __hash__(self) -> int:
        """
        >>> assert SessionRecord('366122_2022-04-25') in {SessionRecord('366122_2022-04-25')}
        >>> assert '366122_2022-04-25_0' in {SessionRecord('366122_2022-04-25')}
        >>> assert SessionRecord('366122_2022-04-25') in {'366122_2022-04-25_0'}
        """
        return hash(self.id)


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
