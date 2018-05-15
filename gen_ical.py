import asyncio
from collections import namedtuple, OrderedDict
from datetime import datetime
import logging
import re

import aiohttp
from aiohttp.resolver import AsyncResolver
from dateutil.parser import parse
from html2text import html2text
import pendulum
import pytz
from pyquery import PyQuery as pq
from recurrent import RecurringEvent
from ruamel.yaml import YAML
import vobject

logger = logging.getLogger('gen_ical')

Event = namedtuple(
    'Event',
    'title location start end '
    'speaker description last_modified recurrence '
    'event_id link'
)
# Make fields optional
Event.__new__.__defaults__ = (None,) * len(Event._fields)
CST = pytz.timezone('America/Chicago')


async def parse_event_id(session, url):
    r = await session.get(url)
    d = pq(await r.text())
    a_doms = d('#calendar_list li > h1 a')
    # print(dir(a_doms[0]))
    return [
        re.search(r'\?EvID=(\d+)', a.attrib['href']).group(1)
        for a in a_doms
    ]


async def retrieve_all_event_ids(event_list_urls, conn):
    loop = asyncio.get_event_loop()
    event_ids = []
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [loop.create_task(parse_event_id(session, url)) for url in event_list_urls]
        for f in asyncio.as_completed(tasks):
            await f
        for t in tasks:
            event_ids.extend(t.result())
    return event_ids


async def fetch_event(session, event_id):
    r = await session.get(
        f'http://dbbs.wustl.edu/Lists/Events/DispForm.aspx?ID={event_id}'
    )
    d = pq(await r.text())
    table = OrderedDict()
    for tr in d('.ms-formtable tr'):
        k, v, *_ = [pq(elem).text() for elem in pq(tr)('td')]
        table[k] = v
    title = table['Title']
    desc = table['Comments'].rstrip()
    if desc:
        desc = html2text(desc).rstrip()
    recurrence = table['Recurrence']
    start, end = [
        CST.localize(parse(time_str, dayfirst=False, ignoretz=True))
        for time_str in (table['Start Time'], table['End Time'])
    ]
    location = table['Location']
    speaker_info = []
    for speaker_order in ['', '2nd ', '3rd ', '4th ']:
        s_col = f'{speaker_order}Speaker/Honorific'
        s_aff_col = f'{speaker_order}Speaker Affiliation'
        if table[s_col]:
            if table[s_aff_col]:
                speaker_entry = f'{table[s_col]}, {table[s_aff_col]}'
            else:
                speaker_entry = table[s_col]
            speaker_info.append(speaker_entry)
    speaker = '\n'.join(speaker_info)
    last_modified = parse(
        re.match(
            r'^Last modified at (.*) by ', d('#onetidinfoblock2').text()
        ).group(1)
    )
    link = (
        'http://dbbs.wustl.edu/Resources/Pages/calendar_event.aspx?'
        f'EvID={event_id}'
    )
    return Event(
        title, location, start, end, speaker, desc,
        last_modified, recurrence, event_id, link
    )


async def fetch_all_events(event_ids, conn):
    loop = asyncio.get_event_loop()
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [
            loop.create_task(fetch_event(session, event_id))
            for event_id in event_ids
        ]
        for f in asyncio.as_completed(tasks):
            await f
        return [t.result() for t in tasks]


def add_custom_events(acceptable_months):
    events = []
    # Read event info from YAML file
    with open('custom_events/genetics_research_talk.yaml') as f:
        yaml = YAML()
        raw_events = yaml.load(f)
    for eid, raw_event in enumerate(raw_events, 1):
        for key in ['start', 'end', 'last_modified']:
            raw_event[key] = CST.localize(parse(raw_event[key], dayfirst=False))
        e = Event()._replace(**raw_event)
        e = e._replace(event_id=f'{e.start.date()} custom event {eid}')
        events.append(e)

    # Filter events with
    filtered_events = []
    for e in events:
        if (e.start.year, e.start.month) in [
                (mo.year, mo.month) for mo in acceptable_months
        ]:
            filtered_events.append(e)
    return filtered_events


def main(now=None, month_shifts=(-1, 0, 1, 2)):
    """
    Calculating which months of the calendar to parse and generate their
    event list URLs.

    Note:
    Only by parsing month event list can retrieve all the events, rather than
    by RSS feed since RSS only contains the latest 100 created events.
    """
    if now is None:
        now = pendulum.now('America/Chicago')

    months = [
        now.add(months=offset) for offset in [-1, 0, 1, 2]
    ]
    month_reprs = [
        mo.format('MMM[%2C][%20]YYYY', locale='en')
        for mo in months
    ]
    event_list_urls = [
        f'http://dbbs.wustl.edu/Pages/Print-Events.aspx?dt={month_repr}'
        for month_repr in month_reprs
    ]

    # Set up aiohttp and asyncio
    loop = asyncio.get_event_loop()
    resolver = AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])

    logger.info(
        'Retreieving events from the following months: {:s}'
        .format(', '.join(month_reprs))
    )
    conn = aiohttp.TCPConnector(limit=5, resolver=resolver)
    event_ids = loop.run_until_complete(retrieve_all_event_ids(event_list_urls, conn))

    logger.info(f'Getting total {len(event_ids)} events')
    conn = aiohttp.TCPConnector(limit=5, resolver=resolver)
    event_infos = loop.run_until_complete(fetch_all_events(event_ids, conn))

    logger.info(f'Loading custom events')
    custom_events = add_custom_events(months)
    event_infos.extend(custom_events)
    logger.info(f'Getting total {len(custom_events)} events')

    logger.info('Writing out events as iCalendar format...')
    cal = vobject.iCalendar()
    cal.add('TZID').value = 'America/Chicago'

    for e in event_infos:
        event = cal.add('vevent')
        event.add('summary').value = e.title
        # Compose the event detail
        event_description = []
        if e.speaker:
            event_description.append(f'Speakers:\n{e.speaker}')
        if e.description:
            event_description.append(f'Description:\n{e.description}')
        event_description.append(f'Link: {e.link}')
        event.add('description').value = '\n\n'.join(event_description)

        event.add('location').value = e.location
        event.add('dtstart').value = e.start
        if e.recurrence:
            rre = RecurringEvent(now_date=e.start)
            rre.parse(e.recurrence)
            rre.until = e.end
            event.add('rrule').value = rre.get_RFC_rrule()[len('RRULE:'):]
            event.add('dtend').value = CST.localize(
                datetime.combine(e.start.date(), e.end.time())
            )
        else:
            event.add('dtend').value = e.end
        event.add('dtstamp').value = e.last_modified
        if e.event_id:
            event.add('uid').value = f'{e.event_id}@events.dbbs.wustl'

    with open('output/DBBS.ics', 'w', encoding='utf8') as f:
        f.write(cal.serialize())


if __name__ == '__main__':
    # setup console logging
    console = logging.StreamHandler()
    all_loggers = logging.getLogger()
    all_loggers.setLevel(logging.INFO)
    all_loggers.addHandler(console)
    log_fmt = '[%(asctime)s][%(levelname)-7s][%(name)-8s] %(message)s'
    log_formatter = logging.Formatter(
        log_fmt,
        '%Y-%m-%d %H:%M:%S'
    )
    console.setFormatter(log_formatter)

    main()
