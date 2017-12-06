# Checkscript for ESE profile pages
# Pieter Vreeburg, 6-12-2017

# new version for Drupal profile pages

# imports
import os # from std. library, os interactions
import datetime # from std.library, time functions
from time import sleep # from std. library, sleep script (do not overload the server)
import string # from std. library, string functions
import json # from std library, import / export JSON

import requests # for HTTP requests
import bs4 # HTML parsing

# dirs + URLs
main_dir = r'C:\git_repos\perspage_parser'
input_file = 'input.txt'
report_dir = 'output'
base_url = 'https://beta.eur.nl/'
listview_url = 'people?f[0]=researcher_profiles_organisation%3A14&page='
photo_url = 'typo3temp/pics/'

# eraskop = 'https://beta.eur.nl/modules/custom/eur_people_pages/img/profile-default-image.jpg'
# foto alfons = 'https://beta.eur.nl/sites/corporate/files/styles/profile/public/externals/972540dbcc07cdb662a12ce14eb9df91.jpg?itok=ziQlgrwd'

# functions
def write_report(data, report_name):
    data = sorted(data)
    with open(os.path.join(main_dir, report_dir, '{}_{}.txt'.format(report_name, datetime.date.today())), 'w') as f_out:
        for item in data:
            line = item + '\n'
            f_out.write(line)

def write_json_file(dict, file_name):
    outfile = open(os.path.join(main_dir, report_dir, '{}_{}.json'.format(file_name, datetime.date.today())), 'w')
    json.dump(dict, outfile, indent = 4)

detail_url_list = []
char = 20
# build profile_datastore dictionary
# use listview to build profile_datastore and get detail_page_url
while True:
    request_url = '{}{}{}'.format(base_url, listview_url, char)
    print request_url
    listview_page = requests.get(request_url).text
    sleep(1)
    listview_page_soup = bs4.BeautifulSoup(listview_page, 'lxml')
    check_overview_list = listview_page_soup.find('ul', class_ = 'overview__list')
    if not check_overview_list:
        break
    profile_divs = listview_page_soup.find_all('div', class_ = 'field field--name-node-title field--type-ds field--label-hidden')
    for profile_div in profile_divs:
        name_link = profile_div.find('a')
        detail_page_url = name_link['href']
        detail_url_list.append(detail_page_url)
    char += 1

quit() # debug

# detail pages

# photo_div = profile.find('div', class_ = 'headshot')
# links = listing_div.find_all('a')
# email = links[1]['href'].split(':')[-1]
# func = listing_div.find('h5').string
# photo_url = photo_div.find('img')['src'] # typo3temp/pics/2f243ef8bd.jpg

# profile_datastore = {}
# profile_datastore[email] = {'name' : name,
                        # 'func' : None,
                        # 'photo_url' : None,
                        # 'detail_page_url' : detail_page_url,
                        # 'has_detail_page' : None,
                        # 'research_progs' : None,
                        # 'cv' : None,
                        # 'linked_in' : None,
                        # 'room_nr': None,
                        # 'tel_nr' : None,
                        # 'story' : None}


for email, profile in profile_datastore.items():
    print 'Downloading: ', profile['name']
    sleep(1)
    detail_page = requests.get(profile['detail_page_url']).text
    # missing_detail_page
    if 'In contact with experts' in detail_page:
        profile_datastore[email]['has_detail_page'] = False # some people are included in the listview, but have no detail page
        continue
    else:
        profile_datastore[email]['has_detail_page'] = True # some people are included in the listview, but have no detail page
    detail_page_soup = bs4.BeautifulSoup(detail_page, 'lxml')
    # story
    story_div = detail_page_soup.find('div', class_ = 'panel-body') # Eerste div met class panel-body voor story & cv
    story = []
    for item in story_div:
        if isinstance(item, bs4.element.Tag):
            if item.name == 'p' and len(item.contents) > 0:
                story.append(unicode(item))
    if len(story) > 0:
        story = ''.join(story).encode('utf-8')
        profile_datastore[email]['story'] = story
    # cv
    cv_div = detail_page_soup.find('div', class_ = 'alsoseerow')
    if cv_div:
        profile_datastore[email]['cv'] = True
    # research_programmes (can be 0, 1 or more)
    research_progs_div = detail_page_soup.find('div', id = 'research')
    if research_progs_div:
        research_progs_div = research_progs_div.descendants
        research_progs = []
        for item in research_progs_div:
            if isinstance(item, bs4.element.Tag):
                if item.name == 'h2' and len(item.contents) > 0:
                    research_progs.append(unicode(item.string))
        if len(research_progs) > 0:
            research_progs = ', '.join(research_progs).encode('utf-8')
            profile_datastore[email]['research_progs'] = research_progs
    # LinkedIn
    linked_in = detail_page_soup.find('a', title = 'LinkedIN')
    if linked_in:
        linked_in = linked_in['href']
        profile_datastore[email]['linked_in'] = linked_in
    # room number & tel number
    detail_profile_div = detail_page_soup.find('div', id = 'people-profile').strings
    for item in detail_profile_div:
        if item.startswith('Room'):
            item = item.split(':')[-1].strip()
            if not item == '-':
                profile_datastore[email]['room_nr'] = item
        if item.startswith('+31'):
            profile_datastore[email]['tel_nr'] = item

write_json_file(profile_datastore, 'profile_datastore_dump')

# build reports
remove_page = []
missing_page = []
missing_detail_page = []
missing_photo = []
missing_cv = []
missing_linked_in = []
missing_room_tel = []
missing_story = []
has_photo = []
has_research_programmes = []
has_irregular_staff = []
has_story = []

staff_data = open(os.path.join(main_dir, input_file)).read().splitlines()
staff_email = []
for item in staff_data:
    email, dept = item.split(';')
    email = email.lower()
    staff_email.append(email)
    profile = profile_datastore.get(email)
    # missing_profile
    if not profile:
        missing_page.append(email)
        continue
    std_output = '{}, {}, {}, {}'.format(dept, profile['name'], email, profile['detail_page_url'])
    # missing_photo & has_photo
    if profile['photo_url'].split('/')[-1] == '0424775dd8.jpg':
        missing_photo.append(std_output)
    else:
        has_photo.append((profile['name'], '{}{}'.format(base_url, profile['photo_url'])))
    # missing_detail_page
    if profile['has_detail_page'] == False:
        missing_detail_page.append(std_output)
        continue
    # has_research_programmes
    if profile['research_progs']:
        has_research_programmes.append(std_output)
    # has_irregular_staff
    if profile['func'] == 'Irregular Staff':
       has_irregular_staff.append(std_output)
    # missing cv
    if not profile['cv']:
        missing_cv.append(std_output)
    # missing_story & has_story
    if not profile['story']:
        missing_story.append(std_output)
    else:
        has_story.append('{}\n{}\n'.format(std_output, profile['story']))
    # missing_linkedin
    if not profile['linked_in']:
        missing_linked_in.append(std_output)
    # missing_room_telnr
    if not profile['room_nr'] or not profile['tel_nr']:
        missing_room_tel.append('{}, room: {}, tel: {}'.format(std_output, profile['room_nr'], profile['tel_nr']))

for email in profile_datastore.keys():
    if email not in staff_email:
        remove_page.append(email)

# write reports
write_report(remove_page, '1_remove_page_ESE_profile_pages')
write_report(missing_page, '2_missing_page_ESE_profile_pages')
write_report(missing_detail_page, '3_missing_detail_page_ESE_profile_pages')
write_report(missing_photo, '4_missing_photos_ESE_profile_pages')
write_report(has_research_programmes, '6_has_research_programme_ESE_profile_pages')
write_report(has_irregular_staff, '7_has_irregular_staff_ESE_profile_pages')
write_report(missing_cv, '8_missing_cv_ESE_profile_pages')
write_report(missing_cv, '9_missing_LinkedIn_ESE_profile_pages')
write_report(missing_room_tel, '10_missing_room_tel_ESE_profile_pages')
write_report(missing_story, '11_missing_story_ESE_profile_pages')
write_report(has_story, '12_has_story_ESE_profile_pages')

# write report 5_has_photo_ESE_profile_pages
cnt = 1
table_html = []
table_html.append('<table>')
table_html.append('<tr>')
for photo in has_photo:
    if table_html[-1] == '</tr>':
        table_html.append('<tr>')
    table_html.append('<td>{}</td>'.format(photo[0]))
    table_html.append('<td><img src=\'{}\'</td>'.format(photo[1]))
    if cnt%4 == 0:
        table_html.append('</tr>')
    cnt += 1
if table_html[-1] != '</tr>':
    table_html.append('/<tr>')
table_html.append('</table>')
html = '\n'.join(table_html)
with open(os.path.join(main_dir, report_dir, '5_has_photo_ESE_profile_pages_{}.html'.format(datetime.date.today())), 'w') as f_out:
    f_out.write(html)