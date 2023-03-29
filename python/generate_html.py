"""
Licensed to the OpenAirInterface (OAI) Software Alliance under one or more
contributor license agreements.  See the NOTICE file distributed with
this work for additional information regarding copyright ownership.
The OpenAirInterface Software Alliance licenses this file to You under
the OAI Public License, Version 1.1  (the "License"); you may not use this file
except in compliance with the License.
You may obtain a copy of the License at

  http://www.openairinterface.org/?page_id=698

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
------------------------------------------------------------------------------
For more information about the OpenAirInterface (OAI) Software Alliance:
  contact@openairinterface.org
---------------------------------------------------------------------
"""

HEADER_TEMPLATE = 'ci-scripts/common/html-templates/file-header.htm'
FOOTER_TEMPLATE = 'ci-scripts/common/html-templates/file-footer.htm'
CHAPT_HEADER_TEMPLATE = 'ci-scripts/common/html-templates/chapter-header.htm'
BUTTON_HEADER_TEMPLATE = 'ci-scripts/common/html-templates/button-header.htm'
BUTTON_FOOTER_TEMPLATE = 'ci-scripts/common/html-templates/button-footer.htm'
IMAGE_TABLE_HEADER_TEMPLATE = 'ci-scripts/common/html-templates/image-table-header.htm'
IMAGE_TABLE_FOOTER_TEMPLATE = 'ci-scripts/common/html-templates/image-table-footer.htm'
IMAGE_TABLE_ROW_TEMPLATE = 'ci-scripts/common/html-templates/image-table-row.htm'
IMAGE_TABLE_SEP_TEMPLATE = 'ci-scripts/common/html-templates/image-table-sep.htm'
COMMAND_TABLE_HEADER_TEMPLATE = 'ci-scripts/common/html-templates/command-table-header.htm'
COMMAND_TABLE_FOOTER_TEMPLATE = 'ci-scripts/common/html-templates/command-table-footer.htm'
COMMAND_TABLE_ROW_TEMPLATE = 'ci-scripts/common/html-templates/command-table-row.htm'
LIST_HEADER_TEMPLATE = 'ci-scripts/common/html-templates/list-header.htm'
LIST_FOOTER_TEMPLATE = 'ci-scripts/common/html-templates/list-footer.htm'
LIST_ROW_TEMPLATE = 'ci-scripts/common/html-templates/list-row.htm'
LIST_SUB_HEADER_TEMPLATE = 'ci-scripts/common/html-templates/list-sub-header.htm'
LIST_SUB_FOOTER_TEMPLATE = 'ci-scripts/common/html-templates/list-sub-footer.htm'
LIST_SUB_ROW_TEMPLATE = 'ci-scripts/common/html-templates/list-sub-row.htm'

import os
import re

def generate_header(args):
    cwd = os.getcwd()
    header = ''
    with open(os.path.join(cwd, HEADER_TEMPLATE), 'r') as temp:
        header = temp.read()
        header = re.sub('JOB_NAME', args.job_name, header)
        header = re.sub('BUILD_ID', args.job_id, header)
        header = re.sub('BUILD_URL', args.job_url, header)
    return header

def generate_footer():
    cwd = os.getcwd()
    footer = ''
    with open(os.path.join(cwd, FOOTER_TEMPLATE), 'r') as temp:
        footer = temp.read()
    return footer

def generate_chapter(name, message, status):
    cwd = os.getcwd()
    header = ''
    with open(os.path.join(cwd, CHAPT_HEADER_TEMPLATE), 'r') as temp:
        header = temp.read()
        header = re.sub('CHAPTER_NAME', name, header)
        if status:
            header = re.sub('ALERT_LEVEL', 'success', header)
        else:
            header = re.sub('ALERT_LEVEL', 'danger', header)
        header = re.sub('MESSAGE', message, header)
    return header

def generate_button_header(name, message):
    cwd = os.getcwd()
    header = ''
    with open(os.path.join(cwd, BUTTON_HEADER_TEMPLATE), 'r') as temp:
        header = temp.read()
        header = re.sub('BUTTON_NAME', name, header)
        header = re.sub('BUTTON_MESSAGE', message, header)
    return header

def generate_button_footer():
    cwd = os.getcwd()
    footer = ''
    with open(os.path.join(cwd, BUTTON_FOOTER_TEMPLATE), 'r') as temp:
        footer = temp.read()
    return footer

def generate_image_table_header():
    cwd = os.getcwd()
    header = ''
    with open(os.path.join(cwd, IMAGE_TABLE_HEADER_TEMPLATE), 'r') as temp:
        header = temp.read()
    return header

def generate_image_table_footer():
    cwd = os.getcwd()
    footer = ''
    with open(os.path.join(cwd, IMAGE_TABLE_FOOTER_TEMPLATE), 'r') as temp:
        footer = temp.read()
    return footer

def generate_image_table_row(name, tag, ocTag, creationDate, size):
    cwd = os.getcwd()
    row = ''
    with open(os.path.join(cwd, IMAGE_TABLE_ROW_TEMPLATE), 'r') as temp:
        row = temp.read()
        row = re.sub('CONTAINER_NAME', name, row)
        row = re.sub('IMAGE_TAG', tag, row)
        row = re.sub('OC_TAG', ocTag, row)
        row = re.sub('CREATION_DATE', creationDate, row)
        row = re.sub('IMAGE_SIZE', size, row)
    return row

def generate_image_table_separator():
    cwd = os.getcwd()
    row = ''
    with open(os.path.join(cwd, IMAGE_TABLE_SEP_TEMPLATE), 'r') as temp:
        row = temp.read()
    return row

def generate_command_table_header():
    cwd = os.getcwd()
    header = ''
    with open(os.path.join(cwd, COMMAND_TABLE_HEADER_TEMPLATE), 'r') as temp:
        header = temp.read()
    return header

def generate_command_table_footer():
    cwd = os.getcwd()
    footer = ''
    with open(os.path.join(cwd, COMMAND_TABLE_FOOTER_TEMPLATE), 'r') as temp:
        footer = temp.read()
    return footer

def generate_command_table_row(command, status):
    cwd = os.getcwd()
    row = ''
    with open(os.path.join(cwd, COMMAND_TABLE_ROW_TEMPLATE), 'r') as temp:
        row = temp.read()
        row = re.sub('COMMAND', command, row)
        if status:
            row = re.sub('STATUS', 'PASS', row)
            row = re.sub('COLOR', 'lightgreen', row)
        else:
            row = re.sub('STATUS', 'FAIL', row)
            row = re.sub('COLOR', 'lightcoral', row)
    return row

def generate_list_header():
    cwd = os.getcwd()
    header = ''
    with open(os.path.join(cwd, LIST_HEADER_TEMPLATE), 'r') as temp:
        header = temp.read()
    return header

def generate_list_footer():
    cwd = os.getcwd()
    footer = ''
    with open(os.path.join(cwd, LIST_FOOTER_TEMPLATE), 'r') as temp:
        footer = temp.read()
    return footer

def generate_list_row(message, iconName):
    cwd = os.getcwd()
    row = ''
    with open(os.path.join(cwd, LIST_ROW_TEMPLATE), 'r') as temp:
        row = temp.read()
        row = re.sub('ROW_MESSAGE', message, row)
        row = re.sub('ICON_NAME', iconName, row)
    return row

def generate_list_sub_header():
    cwd = os.getcwd()
    header = ''
    with open(os.path.join(cwd, LIST_SUB_HEADER_TEMPLATE), 'r') as temp:
        header = temp.read()
    return header

def generate_list_sub_footer():
    cwd = os.getcwd()
    footer = ''
    with open(os.path.join(cwd, LIST_SUB_FOOTER_TEMPLATE), 'r') as temp:
        footer = temp.read()
    return footer

# bagdeColor can be 'primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark'
def generate_list_sub_row(message, nbInBadge, bagdeColor):
    cwd = os.getcwd()
    row = ''
    with open(os.path.join(cwd, LIST_SUB_ROW_TEMPLATE), 'r') as temp:
        row = temp.read()
        row = re.sub('ROW_MESSAGE', message, row)
        row = re.sub('NUMBER', nbInBadge, row)
        row = re.sub('LEVEL', bagdeColor, row)
    return row
