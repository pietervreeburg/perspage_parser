# Checkscript for ESE profile pages
# Pieter Vreeburg, 24-8-2018

# imports
import os # from std. library, os interactions
import sys # from std. library, interpretor interactions
import datetime # from std.library, time functions
from time import sleep # from std. library, sleep script (do not overload the server)
import string # from std. library, string functions
import json # from std. library, import / export JSON
import re # from std. library, regular expressions
import urlparse # from std. library, url functions
import requests # for HTTP requests
import bs4 # HTML parsing

# dirs
main_dir = sys.path[0]
input_dir = 'input'
output_dir = 'output'

# prod URLs
base_url = 'https://www.eur.nl'
lang_url = 'en'
listview_url = 'people?s=&page='

# accept URLS
# base_url = 'https://cms-accept-single.eur.nl'
# lang_url = ''
# listview_url = 'people?s=&f%5B0%5D=researcher_profiles_organisation%3A14&page='

# load settings from file
with(open(os.path.join(main_dir, 'checkscript_profile_pages_EUR_config.json'))) as config_f:
    config = json.load(config_f)
school_name = config.get('school_name')
input_file = config.get('input_file')

# check dirs / settings
if not os.path.isdir(os.path.join(main_dir, output_dir)):
    os.mkdir(os.path.join(main_dir, output_dir))

if not os.path.isdir(os.path.join(main_dir, input_dir)):
    os.mkdir(os.path.join(main_dir, input_dir))

# check if input file exists
if not os.path.isfile(os.path.join(main_dir, input_dir, input_file)):
    sys.exit('No input file, check script configuration')

# check for valid school_name
school_url = '{}/{}/{}/{}'.format(base_url, lang_url, school_name, listview_url)

if requests.get(school_url).status_code == 404:
    sys.exit('No listview found for {}, check script configuration'.format(school_name))

# functions
def write_report(data, report_name, school_out = school_name):
    data = sorted(data)
    with open(os.path.join(main_dir, output_dir, '{}_{}_{}.txt'.format(report_name, school_out, datetime.date.today())), 'w') as f_out:
        for item in data:
            line = item + '\n'
            f_out.write(line)

def write_json_file(dict, file_name, school_out = school_name):
    outfile = open(os.path.join(main_dir, output_dir, '{}_{}_{}.json'.format(file_name, school_out, datetime.date.today())), 'w')
    json.dump(dict, outfile, indent = 4)

detail_page_url_list = []
listview_page_num = 0
# build profile_datastore dictionary
# use listview to get detail_page_url_list
while True:
    print 'Processing listview page:', listview_page_num
    request_url = '{}/{}/{}/{}{}'.format(base_url, lang_url, school_name, listview_url, listview_page_num)
    listview_page = requests.get(request_url).text
    sleep(1)
    listview_page_soup = bs4.BeautifulSoup(listview_page, 'lxml')
    check_overview_list = listview_page_soup.find('ul', class_ = 'overview__list')
    if not check_overview_list:
        print 'Processing listview pages: Done'
        break
    overview_items = listview_page_soup.find_all('li', class_ = 'overview__item')
    for overview_item in overview_items:
        name_link = overview_item.find('a')
        detail_page_url = name_link['href']
        detail_page_url_list.append(detail_page_url)
    listview_page_num += 1

    # break # debug

# use detail_page_url_list to build profile_datastore
# TO_DO: has_irregular_staff, get from func
profile_datastore = {}
missing_detail_page = []
for detail_page_url in detail_page_url_list:
    print 'Processing detail page:', detail_page_url.split('/')[-1]
    detail_page_full_url = '{}{}'.format(base_url, detail_page_url)
    detail_page = requests.get(detail_page_full_url).text
    sleep(1)
    detail_page_soup = bs4.BeautifulSoup(detail_page, 'lxml')
    # missing_detail_page
    info_block = detail_page_soup.find('div', class_ = 'person__info-block l-column-left')
    if not info_block:
        missing_detail_page.append(detail_page_full_url)
        continue
    # info-block, contains: photo, full title, func, room, tel, e-mail
    email = info_block.find('a').string
    profile_datastore[email] = {'name' : None,
                                'func' : None,
                                'full_title' : None,
                                'photo_url' : None,
                                'detail_page_url' : detail_page_full_url,
                                'cv_url' : None,
                                'linked_in_url' : None,
                                'room_nr': None,
                                'tel_nr' : None,
                                'story' : None,
                                'num_key_pub': None}
    # photo
    photo_url = info_block.find('img')['src']
    if photo_url:
        profile_datastore[email]['photo_url'] = photo_url
    # full_title
    full_title = info_block.find('h2', class_ = 'person__fulltitle')
    if full_title:
        full_title = full_title.string
        profile_datastore[email]['full_title'] = full_title
    # func
    func = info_block.find('span', class_ = 'person-position__item')
    if func:
        func = func.string
        profile_datastore[email]['func'] = func
    # room number
    room_nr_str = info_block.find('dt', string = 'Room')
    if room_nr_str:
        room_nr = room_nr_str.find_next_sibling('dd').string
        if room_nr != '-':
            profile_datastore[email]['room_nr'] = room_nr
    # tel number
    tel_nr_str = info_block.find('dt', string = 'Telephone')
    if tel_nr_str:
        tel_nr = tel_nr_str.find_next_sibling('dd').string
        profile_datastore[email]['tel_nr'] = tel_nr
    # name
    name = detail_page_soup.find('span', class_ = 'person__fullname')
    if name:
        name = name.string
        profile_datastore[email]['name'] = name.encode('utf-8')
    # story
    story_div = detail_page_soup.find('div', class_ = 'fold-out__extra-text js-accordion-content')
    if story_div:
        profile_datastore[email]['story'] = unicode(story_div).encode('utf-8')
    # key publication
    key_pub = detail_page_soup.find(string = re.compile('Key publication (.+)'))
    if key_pub:
        num_key_pub = key_pub.strip()[:-1].split('(')[-1]
        profile_datastore[email]['num_key_pub'] = num_key_pub
    # more_information_block, contains: cv, LinkedIn
    more_info_block = detail_page_soup.find('ul', class_ = 'person-social-links')
    # cv
    try:
        cv = more_info_block.find('span', string = 'Cv').parent['href']
        profile_datastore[email]['cv_url'] = cv
    except AttributeError:
        pass
    # lindked_in
    try:
        linked_in = more_info_block.find('span', string = 'Linkedin').parent['href']
        profile_datastore[email]['linked_in_url'] = linked_in
    except AttributeError:
        pass

write_json_file(profile_datastore, 'profile_datastore_dump')

# build reports
missing_page = []
missing_photo = []
missing_cv = []
missing_linked_in = []
missing_room_tel = []
missing_story = []
missing_key_pub = []
has_photo = []
has_irregular_func = []
has_story = []
has_full_title = []

staff_email = []
staff_data = open(os.path.join(main_dir, input_dir, input_file)).read().splitlines()
for row in staff_data:
    email, dept, last_name = row.split(';')
    email = email.lower()
    staff_email.append(email)

    profile = profile_datastore.get(email)
    # missing_profile
    if not profile:
        missing_page.append('{}, {}, {}'.format(dept, last_name, email))
        continue
    std_output = '{}; {}; {}; {}'.format(dept, last_name, email, profile['detail_page_url'])
    
    # missing_photo & has_photo
    if profile['photo_url'].split('/')[-1] == 'profile-default-image.jpg':
        missing_photo.append(std_output)
    else:
        has_photo.append(('{}, {}'.format(dept, last_name), '{}{}'.format(base_url, profile['photo_url'])))
    # has_irregular_func
    regular_funcs = [
                    'Full Professor',
                    'Endowed Professor',
                    'Associate Professor',
                    'Assistant Professor',
                    'Trainee Assistant Professor',
                    'PhD Candidate',
                    'Teacher Tutor Academy'
                    #'Academic Researcher',
                    #'Lecturer'
                    ]
    if profile['func'] not in regular_funcs:
       has_irregular_func.append('{}\n{}\n'.format(std_output, profile['func']))
    # has_full_title
    if profile['full_title']:
        has_full_title.append('{}\n{}\n'.format(std_output, profile['full_title']))
    # missing cv
    if not profile['cv_url']:
        missing_cv.append(std_output)
    # missing_story & has_story
    if not profile['story']:
        missing_story.append(std_output)
    else:
        has_story.append((std_output, profile['story']))
    # missing_linkedin
    if not profile['linked_in_url']:
        missing_linked_in.append(std_output)
    # missing_room_telnr
    if not profile['room_nr'] or not profile['tel_nr']:
        missing_room_tel.append('{}, room: {}, tel: {}'.format(std_output, profile['room_nr'], profile['tel_nr']))
    # missing_key_pub
    if not profile['num_key_pub']:
        missing_key_pub.append(std_output)

remove_page = []
for email in profile_datastore.keys():
    if email not in staff_email:
        remove_page.append('{}, {}, {}'.format(profile_datastore[email]['name'], email, profile_datastore[email]['detail_page_url']))

# write reports
write_report(remove_page, '1_remove_page')
write_report(missing_page, '2_missing_page')
write_report(missing_detail_page, '3_missing_detail_page')
write_report(missing_photo, '4_missing_photo')
# 5_has_photo: see below
write_report(has_irregular_func, '6_has_irregular_func')
write_report(missing_cv, '7_missing_cv')
write_report(missing_linked_in, '8_missing_LinkedIn')
write_report(missing_room_tel, '9_missing_room_tel')
write_report(missing_story, '10_missing_story')
# 11 has_story: see below
write_report(has_full_title, '12_has_full_title')
write_report(missing_key_pub, '13_missing_key_publication')

# write report 5_has_photo
cnt = 1
table_html = []
table_html.append('<table>')
table_html.append('<tr>')
for photo in sorted(has_photo):
    if table_html[-1] == '</tr>':
        table_html.append('<tr>')
    table_html.append('<td>{}</td>'.format(photo[0])) # std_output_photo = ';'.join(std_output.split(';')[0:2])
    table_html.append('<td><img src=\'{}\'</td>'.format(photo[1]))
    if cnt%4 == 0:
        table_html.append('</tr>')
    cnt += 1
if table_html[-1] != '</tr>':
    table_html.append('/<tr>')
table_html.append('</table>')
html = '\n'.join(table_html)
with open(os.path.join(main_dir, output_dir, '5_has_photo_{}_{}.html'.format(school_name, datetime.date.today())), 'w') as f_out:
    f_out.write(html)

# write report 11_has_story
story_html = ['<head><meta charset="utf-8"/></head>\n']
for story in sorted(has_story):
    story_html.append('<h1>{}</h1><p>{}</p>'.format(story[0], story[1]))
html = '\n'.join(story_html)
with open(os.path.join(main_dir, output_dir, '11_has_story_{}_{}.html'.format(school_name, datetime.date.today())), 'w') as f_out:
    f_out.write(html)