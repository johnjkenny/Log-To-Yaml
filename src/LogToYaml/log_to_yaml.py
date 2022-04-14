#!/usr/bin/env python3


__author__ = 'John J Kenny'
__version__ = '1.0.0'


from datetime import datetime
from uuid import uuid4

from PrettifyLogging.prettify_logging import PrettifyLogging
from yaml import dump, safe_load


class LogToYaml(PrettifyLogging):
    def __init__(self, **kwargs: dict):
        super().__init__()
        self.log_data = None
        self.yaml_data = None
        self.record_index = None
        self.level_index = None
        self.yaml_file = None
        self.log_dict = None
        self.name = kwargs['name'] if 'name' in kwargs else 'log-to-yaml.log'
        self.log_file = kwargs['log_file'] if 'log_file' in kwargs else None
        self.seperator = kwargs['seperator'] if 'seperator' in kwargs else '-'
        self.verifier = kwargs['verifier'] if 'verifier' in kwargs else 4
        self.check_list = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.log = self.configure()

    def convert(self):
        if self._load_log_and_yaml_data():
            if self._find_record_and_level_index():
                self._create_log_dict()

    def _load_log_and_yaml_data(self):
        self.log_data = self._try_to_load_log_data()
        if self.log_data is not None:
            self.yaml_data = self._try_to_load_yaml_data()
            if self.yaml_data is not None:
                return True
        return False

    def _try_to_load_log_data(self):
        if isinstance(self.log_file, str):
            try:
                with open(self.log_file, 'r') as file:
                    return file.readlines()
            except Exception:
                self.log.exception('File not found: {}'.format(self.log_file))
        return None

    def _try_to_load_yaml_data(self):
        self.yaml_file = self.log_file.replace('.log', '.yaml')
        try:
            with open(self.yaml_file, 'r') as file:
                return safe_load(file)
        except FileNotFoundError:
            yaml_data = {'dateCreated': datetime.now(), 'last': 0, 'records': {}}
            with open(self.yaml_file, 'w') as file:
                dump(self.yaml_data, file)
            return yaml_data
        except Exception:
            self.log.exception('Failed to open yaml file: {}'.format(self.yaml_file))
        return None

    def _find_record_and_level_index(self):
        self.record_index = self._try_to_find_next_record_index()
        if self.record_index is not None:
            self.level_index = self._try_to_find_log_level_index()
            if self.level_index is not None:
                return True
        return False

    def _try_to_find_next_record_index(self):
        if isinstance(self.yaml_data, dict):
            try:
                record_index = list(self.yaml_data['records'].keys())
                if not record_index:
                    return 1
                return record_index[-1] + 1
            except Exception:
                self.log.exception('Failed to get yaml record index.')
        return None

    def _try_to_find_log_level_index(self):
        for line_data in self.log_data:
            for index, value in enumerate(str(line_data).split(self.seperator)):
                if index == self.verifier and str(value).strip() in self.check_list:
                    return index
        return None

    def _create_log_dict(self):
        self.log_dict = {}
        line_num = 0
        for line_num, line_data in enumerate(self.log_data, 1):
            if self.yaml_data['last'] != 0 and line_num <= self.yaml_data['last']:
                continue
            line_split = str(line_data).split(self.seperator)
            if len(line_split) > self.level_index and str(line_split[self.level_index]).strip() in self.check_list:
                self.log_dict[self.record_index] = self._populate_index_dict(line_split, line_num)
                self._find_log_record_stop_position(len(self.log_data), line_num)
                self._add_log_message_to_log_dict(line_num)
                
                self.record_index += 1
        if self.log_dict != {}:
            self._save_log_dict_as_yaml_file(line_num)

    def _populate_index_dict(self, line_split: list, line_num: int):
        data = str(line_split[self.level_index + 1]).split(':')
        location = data[0].strip().split(',')
        return {
            'position': [line_num, None], 'message': None, 'id': str(uuid4()),
            'name': str(line_split[3]).strip(), 'level': str(line_split[self.level_index]).strip(),
            'timeStamp': '-'.join(line_split[0:3]).replace('[', '').replace(']', '').strip(),
            'location': {
                'file': location[0].replace('(', '').strip(),
                'function': location[1].strip(),
                'lineNumber': int(location[2].replace(')', '').strip())
                }
            }

    def _find_log_record_stop_position(self, log_length: int, line_num: int):
        scan_line = line_num
        while scan_line <= log_length:
            if scan_line < log_length:
                scan_line_data_split = str(self.log_data[scan_line]).split(self.seperator)
                if (len(scan_line_data_split) > self.level_index
                        and str(scan_line_data_split[self.level_index]).strip() in self.check_list):
                    self.log_dict[self.record_index]['position'][1] = scan_line
                    break
            elif scan_line == log_length:
                self.log_dict[self.record_index]['position'][1] = scan_line
                break
            else:
                self.log.error('Failed to find log entry end line for line number: {}. In log: {}'.format(
                    line_num, self.log_file))
            scan_line += 1

    def _add_log_message_to_log_dict(self, line_num: int):
        record_end = self.log_dict[self.record_index]['position'][1]
        if record_end is not None:
            self.log_dict[self.record_index]['message'] = list()
            while line_num <= record_end:
                self.log_dict[self.record_index]['message'].append(self.log_data[line_num - 1].strip())
                line_num += 1
            del self.log_dict[self.record_index]['position']

    def _save_log_dict_as_yaml_file(self, last_line_read: int):
        self.yaml_data['records'].update(self.log_dict)
        self.yaml_data['last'] = last_line_read
        try:
            with open(self.yaml_file, 'w+') as file:
                dump(self.yaml_data, file)
        except Exception:
            self.log.exception('Failed to save log dict as yaml file: {}.'.format(self.yaml_file))


if __name__ == '__main__':
    log_to_yaml = LogToYaml(log_file='test.log')
    log_to_yaml.convert()
