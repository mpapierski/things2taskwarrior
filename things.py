import json
import sqlite3
import os
import sys
import subprocess
from functools import lru_cache
from datetime import datetime
import xml.etree.ElementTree as ET

def parse_date(value):
    if value is None:
        return None
    try:
        return datetime.utcfromtimestamp(value)
    except TypeError:
        print('Invalid date {!r}'.format(value), file=sys.stderr)
        raise


class TaskWarriorEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y%m%dT%H%M%SZ')
            # return obj.strftime('%Y%m%dT%H%M%sZ')
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def parse_notes(notes):
    root = ET.fromstring(notes)
    assert root.tag == 'note'
    return root.text


def is_task(task):
    return task['type'] == 0


def is_trashed(task):
    return task['trashed'] == 1

def is_postponed(task):
    return task['start'] == 2

def is_open(task):
    return task['status'] == 0

def is_someday(task):
    return not is_trashed(task) and is_task(task) and is_postponed(task) and is_open(task)


@lru_cache()
def get_someday():
    stdout = subprocess.check_output(['task', 'calc', 'someday'])
    lines = stdout.splitlines()
    return lines[0].decode('utf-8')


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]

    return d


def connect():
    default_path = os.path.expanduser('~/Library/Containers/com.culturedcode.ThingsMac/Data/Library/Application Support/Cultured Code/Things/Things.sqlite3')
    path = os.getenv('THINGS_DB', default_path)
    db = sqlite3.connect(path)
    db.row_factory = dict_factory
    return db


def main():
    db = connect()
    cur = db.cursor()
    cur.execute('SELECT * FROM TMTask')
    tasks = {}
    for task in cur.fetchall():
        assert task['uuid'] not in task
        uuid = task['uuid']
        del task['uuid']

        for date_col in ['creationDate', 'userModificationDate', 'startDate', 'stopDate', 'dueDate']:
            task[date_col] = parse_date(task[date_col])

        # Normalize

        if task['creationDate'] and task['startDate']:
                entry = task['creationDate']
                start = task['startDate']
                if entry > start:
                    if start.date() == entry.date():
                        task['startDate'] = entry
                        print('Normalize "{!r}" entry={} start={}'.format(task['title'], entry, start), file=sys.stderr)
        task['tags'] = []
        tasks[uuid] = task

    # Get all tags
    cur.execute('SELECT * FROM TMTag')
    tags = {}
    for tag in cur.fetchall():
        assert tag['uuid'] not in tags
        tags[tag['uuid']] = tag['title']

    # List all tags
    # for key, value in tags.items():
    #     print(key, value)

    # Match tags to tasks
    cur.execute('SELECT * FROM TMTaskTag')
    for tag in cur.fetchall():
        tasks[tag['tasks']]['tags'].append(tag['tags'])

    # Parse "priority"    
    for uuid, task in tasks.items():
        if 'CC-Things-Tag-High' in task['tags']:
            task['priority'] = 'H'
            task['tags'].remove('CC-Things-Tag-High')
        if 'CC-Things-Tag-Medium' in task['tags']:
            task['priority'] = 'M'
            task['tags'].remove('CC-Things-Tag-Medium')
        if 'CC-Things-Tag-Low' in task['tags']:
            task['priority'] = 'L'
            task['tags'].remove('CC-Things-Tag-Low')

    # statuses = {
    #     0:"pending",
    #     0:"deleted",
    #     0:"completed",
    #     0:"waiting",
    #     0:"recurring"
    # }
    values = []
    for uuid, task in tasks.items():
        if task['type'] == 0:
            new_task = {}
            if task['trashed']:
                new_task['status'] = 'deleted'
            elif task['status'] == 0:
                assert not task['trashed']
                new_task['status'] = 'pending'
            elif task['status'] == 1:
                assert not task['trashed']
                pass # ?
            elif task['status'] == 2:
                assert not task['trashed']
                new_task['status'] = 'waiting'
                new_task['wait'] = get_someday()
            elif task['status'] == 3:
                assert not task['trashed']
                new_task['status'] = 'completed'

            assert new_task['status'] is not None
            

            new_task.update({
                'uuid': uuid.lower(),
                'entry': task['creationDate'],
                'description': task['title'],  
                # 'entry': 
            })

            if task['project'] is not None:
                new_task['project'] = tasks[task['project']]['title']


            if task['userModificationDate']:
                new_task['modified'] = task['userModificationDate']
            if task['startDate']:
                new_task['start'] = task['startDate']
            if task['stopDate']:
                new_task['stop'] = task['stopDate']
            if task['dueDate']:
                new_task['due'] = task['dueDate']

            if 'priority' in task:
                new_task['priority'] = task['priority']

            # new_task['tags'] = []
            # for tag in task['tags']:
            #     new_task['tags'].append(tags[task['tags']['uuid']])
            if task['tags']:
                new_task['tags'] = [tags[tag] for tag in task['tags']]



            if not new_task['description']:
                # Cannot add empty task
                continue

            if task['notes'] is not None:
                annotation_entry = new_task['modified'] or new_task['entry']
                assert annotation_entry is not None
                description = parse_notes(task['notes'])
                if description is not None:
                    
                    new_task['annotations'] = [
                        {
                            'entry': annotation_entry,
                            'description': description
                        }
                    ]

            print(json.dumps(new_task, cls=TaskWarriorEncoder))

if __name__ == '__main__':
    main()
