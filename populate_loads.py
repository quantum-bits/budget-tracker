import os
import csv
import subprocess


#
# process for using this file:
# - copy data into a csv file
# - first row in csv file is assumed to be headers; data starts in second row
# - make sure course numbers follow "L" convention for labs (BIO 101L for the lab, etc.)
# - easiest to go in ahead of time and assign loads for labs by hand, rather than leaving them as "zeros"
# - need to create a "load" column in column "Q"...the column beside credit hours.  Can just copy the credit column
# - if there are any shared (co-taught) courses, make sure that exactly one section appears in csv file; shared courses need to be put in by hand later
# - instructors will be created if they do not already exist in the db
# - subjects and buildings need to be created ahead of time
# - rooms will be created if they do not already exist in the db
# - make sure room numbers use the same abbreviations as the db is using for them ('ESC' for Euler, 'NS' for Nussbaum, etc.)
# - blank entries for the BUILDING or ROOM in the csv file are replaced by 'TBD'
# - accepts begin and end times in either the '0950' or '950' format; in the latter case, it prepends '0'
# - to run this file, type python populate_loads.py

# to make it simple, just check if there are any course offerings that
# currently have no instructor and no weekly schedule; if so, assign it.
# it's not a perfect system, but it's not worth it to get too complicated....

# Here is a typical sequence of commands to create a course and schedule the profs, etc.:
#
# ./manage.py create_instructor Hank Voss 'Taylor University' MAT 0001 Full
# ./manage.py create_room ESC 241 24
# 
#
#................... need to go into the csv file and change ESC back to EULER.................................
#
#
#
#
#
# ./manage.py create_course PHY 124 'clarinet for physicists' 2 Spring E
# ./manage.py create_course_offerings PHY 124 J-Term 2014 [3,2,1] 32
#   Note: - makes sure there are a total of 3 offerings in J-Term of the 2013-14 academic year
#           - if some sections exist already, creates new ones as needed
#         - 3, 2 and 1 load hours, 32 students max enrollment
# ./manage.py add_instructor_schedule PHY 124 J-Term 2014 Hank Voss MWF 0900 1250 ESC 125
#   Note: - looks for "open" course sections (no prof yet, no daily meetings yet), then adds the above schedule to them
#         - in the above example, we would be looking at J-Term of the 2013-14 academic year


with open('EDU_courses_2013-14.csv', 'rU') as csvfile:
    tempdata = csv.reader(csvfile)
    data=[]
    for row in tempdata:
        data.append(row)

course_loads_dict={}
course_offerings_dict={}
instructors_dict={}
rooms_dict={}
courses_dict={}
# drop data in first row
for course in data[1:]:
    subject = course[4]
    number = """'"""+course[5]+"""'"""
    title = """'"""+course[7]+"""'"""
    credit_hours = course[15]
    semester_key=course[0]
    load = max(float(course[16]),0.5)

    if course[0][-2:]=='20':
        semester = 'Spring'
    elif course[0][-2:]=='10':
        semester = 'J-Term'
    elif course[0][-2:]=='90':
        semester = 'Fall'
    else:
        print "Huh?!?  Can not figure out the semester!!!!"
        print subject, number, title
    normal_year = 'B'
    year = course[0][:4]
    max_enrollment = course[17]

    professor_last_name = (course[14]).split()[-1]
    professor_first_name = (course[14]).split()[0]
    department_abbrev = course[3]

    building = course[11]
    if building == 'EULER':
        building = 'ESC'
    room = course[12]
    if building == '':
        building = 'TBD'
    if room == '':
        room = 'TBD'
    room = """'"""+room+"""'"""

    capacity = course[17]

    instructors_dict[course[14]]=[professor_first_name, professor_last_name, department_abbrev]
    rooms_dict[building+room]=[building, room, capacity]
    courses_dict[subject+number]=[subject, number, title, credit_hours, semester, normal_year]

    try:
        course_loads_dict[subject+number+semester_key] = course_loads_dict[subject+number+semester_key]+str(load)+','
    except KeyError:
        course_loads_dict[subject+number+semester_key] = '['+str(load)+','
# another dictionary with parallel keys.... (probably a bad idea!!!)
    course_offerings_dict[subject+number+semester_key] = [subject, number, semester, year, max_enrollment]

for key in course_loads_dict.keys():
    course_loads_dict[key] = course_loads_dict[key][:-1]+']'

for key in instructors_dict.keys():
    command_string0 = './manage.py create_instructor '+instructors_dict[key][0]+' '+instructors_dict[key][1]+""" 'Taylor University' """+instructors_dict[key][2]+' 0001 Full'
    os.system(command_string0)

for key in rooms_dict.keys():
    command_string0a = './manage.py create_room '+rooms_dict[key][0]+' '+rooms_dict[key][1]+' '+rooms_dict[key][2]
    os.system(command_string0a)

for key in courses_dict.keys():
    command_string = './manage.py create_course '+courses_dict[key][0]+' '+courses_dict[key][1]+' '+courses_dict[key][2]+' '+courses_dict[key][3]+' '+courses_dict[key][4]+' '+courses_dict[key][5]
    os.system(command_string)

for key in course_loads_dict.keys():
    command_string2 = './manage.py create_course_offerings '+course_offerings_dict[key][0]+' '+course_offerings_dict[key][1]+' '+course_offerings_dict[key][2]+' '+course_offerings_dict[key][3]+' '+course_loads_dict[key]+' '+course_offerings_dict[key][4]
    os.system(command_string2)


# drop data in first row
for course in data[1:]:

# in the following, the triple quotes are needed, b/c we actually need to pass
# a single quote if the title contains more than one word

# repeating all of the following from above....BAD!!!
    subject = course[4]
    number = """'"""+course[5]+"""'"""
    title = """'"""+course[7]+"""'"""
    credit_hours = course[15]
    semester_key=course[0]
    if course[0][-2:]=='20':
        semester = 'Spring'
    elif course[0][-2:]=='10':
        semester = 'J-Term'
    elif course[0][-2:]=='90':
        semester = 'Fall'
    else:
        print "Huh?!?  Can not figure out the semester!!!!"
        print subject, number, title
    normal_year = 'B'
    year = course[0][:4]


    building = course[11]
    if building == 'EULER':
        building = 'ESC'
    room = course[12]
    if building == '':
        building = 'TBD'
    if room == '':
        room = 'TBD'
    room = """'"""+room+"""'"""

    days = course[10]
    begin_time = course[8]
    end_time = course[9]
    if len(begin_time) == 3:
        begin_time = '0'+begin_time
    if len(end_time) == 3:
        end_time = '0'+end_time

    professor_last_name = (course[14]).split()[-1]
    professor_first_name = (course[14]).split()[0]

#    command_string2 = './manage.py create_course_offerings '+subject+' '+number+' '+semester+' '+year+' '+course_loads_dict[subject+number+semester_key]+' '+max_enrollment
#    print command_string2
#    os.system(command_string2)

    command_string3 = './manage.py add_instructor_schedule '+subject+' '+number+' '+semester+' '+year+' '+professor_first_name+' '+professor_last_name+' '+days+' '+begin_time+' '+end_time+' '+building+' '+ room
    print command_string3
    os.system(command_string3)

