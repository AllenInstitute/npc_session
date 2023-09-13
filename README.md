# npc_session

**n**euro**p**ixels **c**loud **session**

Basic tools for parsing subject, session, date and time associated with data from the
Mindscope Neuropixels team, in the cloud.

[![PyPI](https://img.shields.io/pypi/v/npc-session.svg?label=PyPI&color=blue)](https://pypi.org/project/npc-session/)
[![Python version](https://img.shields.io/pypi/pyversions/npc-session)](https://pypi.org/project/npc-session/)

[![Coverage](https://img.shields.io/codecov/c/github/alleninstitute/npc_session?logo=codecov)](https://app.codecov.io/github/AllenInstitute/npc_session)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/alleninstitute/npc_session/publish.yml?label=CI/CD&logo=github)](https://github.com/alleninstitute/npc_session/actions/workflows/publish.yml)
[![GitHub issues](https://img.shields.io/github/issues/alleninstitute/npc_session?logo=github)](https://github.com/alleninstitute/npc_session/issues)


## quickstart

```bash
pip install npc_session
```

Parse a normalized ID from a path or string:
```python
>>> from npc_session import SessionRecord;

>>> s = SessionRecord('//allen/programs/mindscope/workgroups/templeton/TTOC/2022-07-26_14-09-36_366122')
>>> s
'366122_2022-07-26'
>>> s.subject
366122
>>> s.date
'2022-07-26'
>>> s.date.year
2022

```
