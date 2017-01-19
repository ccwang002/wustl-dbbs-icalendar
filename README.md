# WUSTL DBBS Calendar in iCalendar format

The script `gen_ical.py` parses the official WUSTL DBBS event calendar and generate a subscribable calendar file in the RFC standard format (RFC 5545 iCalendar) and generate an iCalendar at `output/DBBS.ics`. 

```
python gen_ical.py
```

See [it runs in action](https://blog.liang2.tw/wustl-dbbs-icalendar/) which embeds an daily updated Google calendar.


## Dependencies

- Python version: 3.6+
- Async web scrapping:
    - aiodns
    - aiohttp
- Web parsing:
    - lxml
    - beautifulsoup4
    - html5lib
    - pyquery
- Datetime handling:
    - pytz
    - pendulum
- iCalendar generation:
    - vobject
    - [recurrent (py3k compat fork)](https://github.com/eyesee1/recurrent)
- Misc:
    - tqdm
    - ghp-import 
    - [Fabric3 (Fabric py3k compat fork)](https://github.com/mathiasertl/fabric)

