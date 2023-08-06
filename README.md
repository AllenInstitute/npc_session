# npc_session
**n**euro**p**ixels **c**loud **session**

Interfaces for working with behavior and epyhys sessions from the
Mindscope Neuropixels team, in the cloud.

## quickstart

```bash
pip install npc_session
```

Parse a normalized IDs from a path or string:
```python
>>> from npc_session import Session;

>>> s = Session('//allen/programs/mindscope/workgroups/templeton/TTOC/2022-07-26_14-09-36_366122')
>>> s
SessionRecord('366122_2022-07-26')
>>> s.subject
SubjectRecord(366122)
>>> s.date
DateRecord('2022-07-26')
>>> s.date.year
2022

```