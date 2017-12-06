# Checkscript for ESE profile pages
# Pieter Vreeburg, 6-12-2017 (New version for Drupal profile pages)

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

detail_page_url_list = []
char = 20
# build profile_datastore dictionary
# use listview to build profile_datastore and get detail_page_url
while True:
    request_url = '{}{}{}'.format(base_url, listview_url, char)
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
        detail_page_url_list.append(detail_page_url)
    char += 1

# use detail pages to fill profile_datastore
profile_datastore = {}
for detail_page_url in detail_page_url_list:
    print 'Downloading:', detail_page_url
    sleep(1)
    detail_page_url = '{}{}'.format(base_url, detail_page_url)
    detail_page = requests.get(detail_page_url).text
    # missing_detail_page, add this later
    # if 'In contact with experts' in detail_page:
        # profile_datastore[email]['has_detail_page'] = False # some people are included in the listview, but have no detail page
        # continue
    # else:
        # profile_datastore[email]['has_detail_page'] = True # some people are included in the listview, but have no detail page
    detail_page_soup = bs4.BeautifulSoup(detail_page, 'lxml')
    # info-block, contains: photo, func, room, tel, e-mail
    info_block = detail_page_soup.find('div', class_ = 'person__info-block background--dark l-column-left')
    email = info_block.find('a').string
    profile_datastore[email] = {'name' : None,
                            'func' : None,
                            'photo_url' : None,
                            'detail_page_url' : detail_page_url,
                            'has_detail_page' : None,
                            'cv' : None,
                            'linked_in' : None,
                            'room_nr': None,
                            'tel_nr' : None,
                            'story' : None}
    # photo
    photo_url = info_block.find('img')['src']
    if photo_url:
        profile_datastore[email]['photo_url'] = photo_url
    # room number
    room_nr = info_block.find('dt', string = 'Room').find_next_sibling('dd').string
    if room_nr:
        profile_datastore[email]['room_nr'] = room_nr
    # tel number
    tel_nr = info_block.find('dt', string = 'Telephone').find_next_sibling('dd').string
    if tel_nr:
        profile_datastore[email]['tel_nr'] = tel_nr
    # name
    name = detail_page_soup.find('span', class_ = 'person__fullname').string
    if name:
        profile_datastore[email]['name'] = name
    # story, NOG EVEN OVER NADENKEN
    story_div = detail_page_soup.find('div', class_ = 'person__description')
    story = []
    # EXAMPLE    
    # <div class="person__description"><p><p>Ran Xing is affiliated to the Finance Group of Erasmus School of Economics (Erasmus University Rotterdam). He got his Ph.D from Tilburg University, and he has been a visiting scholar at The Wharton School.</p><p>Ran conducts theoretical and empirical research in asset pricing. His current work focuses on the skill of mutual funds and the pricing of liquidity risk.</p><p>You can find more information on his personal website: <a href="https://sites.google.com/view/xingran">https://sites.google.com/view/xingran</a></p><p> </p><p> </p></p></div>
    for item in story_div.descendants:
        if isinstance(item, bs4.element.Tag):
            if len(item.contents) > 0:
                story.append(unicode(item))
    if len(story) > 0:
        story = ''.join(story).encode('utf-8')
        profile_datastore[email]['story'] = story
    # cv
    # cv_div = detail_page_soup.find('div', class_ = 'alsoseerow')
    # if cv_div:
        # profile_datastore[email]['cv'] = True
    # LinkedIn
    # linked_in = detail_page_soup.find('a', title = 'LinkedIN')['href']
    # if linked_in:
        # profile_datastore[email]['linked_in'] = linked_in

    write_json_file(profile_datastore, 'profile_datastore_dump') # debug
    quit() # debug

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
    if profile['photo_url'].split('/')[-1] == 'profile-default-image.jpg':
        missing_photo.append(std_output)
    else:
        has_photo.append((profile['name'], '{}{}'.format(base_url, profile['photo_url'])))
    # missing_detail_page
    # if profile['has_detail_page'] == False:
        # missing_detail_page.append(std_output)
        # continue
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
# 5_has_photo_ESE_profile_pages: see below
write_report(missing_photo, '4_missing_photos_ESE_profile_pages')
write_report(has_irregular_staff, '6_has_irregular_staff_ESE_profile_pages')
write_report(missing_cv, '7_missing_cv_ESE_profile_pages')
write_report(missing_cv, '8_missing_LinkedIn_ESE_profile_pages')
write_report(missing_room_tel, '9_missing_room_tel_ESE_profile_pages')
write_report(missing_story, '10_missing_story_ESE_profile_pages')
write_report(has_story, '11_has_story_ESE_profile_pages')

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