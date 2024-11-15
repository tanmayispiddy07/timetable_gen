import streamlit as st
import numpy as np
import random

# Streamlit UI for input
st.title("Timetable Generator")

# Taking dynamic input for classes
c = st.number_input("Enter the number of classes:", min_value=1, step=1)
classes = []
for i in range(c):
    class_name = st.text_input(f"Enter class name {i + 1}:")

    # Ensure the class name is not empty
    if class_name.strip():  # Check if it's not empty or just spaces
        classes.append(class_name)
    else:
        st.warning("Class name cannot be empty! Please provide a valid name.")

# Taking dynamic input for subjects
s = st.number_input("Enter the number of subjects:", min_value=1, step=1)
subject_hours_per_week = {}
for class_name in classes:
    st.subheader(f"Enter subject details for {class_name}:")
    subject_hours_per_week[class_name] = {}

    for i in range(s):
        subject = st.text_input(f"Enter subject name for {class_name}:", key=f"{class_name}_subject_{i}")
        hours = st.number_input(f"Enter hours per week for {subject}:", min_value=1, step=1,
                                key=f"{class_name}_hours_{i}")

        # Ensure the subject name is not empty before adding to the dictionary
        if subject.strip():
            subject_hours_per_week[class_name][subject] = hours
        else:
            st.warning(f"Subject name for {class_name} cannot be empty! Please provide a valid name.")

# Taking dynamic input for labs
l = st.number_input("Enter the number of labs:", min_value=0, step=1)
labs = [st.text_input(f"Enter lab name {i + 1}:") for i in range(l)]
lh = st.number_input("Enter number of consecutive lab hours:", min_value=1, step=1)

# Taking dynamic input for teachers
num_teachers = st.number_input("Enter the number of teachers:", min_value=1, step=1)
teacher_data = []
for _ in range(num_teachers):
    teacher_name = st.text_input("Enter teacher name:", key=f"teacher_name_{_}")
    subject = st.text_input(f"Enter subject that {teacher_name} teaches:", key=f"teacher_subject_{_}")
    teaching_hours = st.number_input(f"Enter teaching hours per week for {teacher_name}:", min_value=1, step=1, key=f"teaching_hours_{_}")

    unavailable = {}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
        unavailable_hours = st.text_input(f"Enter unavailable hours for {teacher_name} on {day} (comma separated, leave blank if available all day):", key=f"{teacher_name}unavailable{day}")
        if unavailable_hours:
            unavailable[day] = list(map(int, unavailable_hours.split(",")))

    teacher_data.append({"name": teacher_name, "subject": subject, "teaching_hours": teaching_hours, "unavailable": unavailable})

# Number of working hours per day and days per week
h = st.number_input("Enter number of hours per day (including lunch break):", min_value=1, step=1)
w = st.number_input("Enter number of working days:", min_value=1, step=1)

# Teacher class definition
class Teacher:
    def __init__(self, name, subject, w, h, th):
        self.name = name
        self.subject = subject
        self.availability = np.ones((w, h))  # Availability matrix (1: available, 0: unavailable)
        self.teaching_hours = th
        self.assigned_hours = 0
        self.daily_hours = np.zeros(w)  # Track daily teaching hours for each teacher
        self.assigned_classes = []  # Track the classes assigned to this teacher

    def update_availability(self, day, hour):
        """Mark the teacher as unavailable for a specific time slot"""
        self.availability[day][hour] = 0

    def can_teach_today(self, day):
        """Check if teacher can teach more today (max 3 hours per day)"""
        return self.daily_hours[day] < 3

# Create teacher objects and update their availability
teachers = [Teacher(name=data['name'], subject=data['subject'], w=w, h=h, th=data.get('teaching_hours', 0)) for data in teacher_data]

# Update availability for each teacher based on the 'unavailable' data
for i, data in enumerate(teacher_data):
    if 'unavailable' in data:
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for day, hours in data['unavailable'].items():
            if day in days_of_week:
                day_index = days_of_week.index(day)
                for hour in hours:
                    if 0 <= hour < h:
                        teachers[i].update_availability(day_index, hour)

# Function to divide classes among teachers for each subject
def divide_classes_among_teachers():
    subject_teacher_map = {}

    # Group teachers by subject
    for teacher in teachers:
        if teacher.subject not in subject_teacher_map:
            subject_teacher_map[teacher.subject] = []
        subject_teacher_map[teacher.subject].append(teacher)

    # Divide classes among teachers for each subject
    for subject, subject_teachers in subject_teacher_map.items():
        num_teachers = len(subject_teachers)
        classes_per_teacher = len(classes) // num_teachers
        extra_classes = len(classes) % num_teachers

        class_index = 0
        for teacher in subject_teachers:
            # Allocate classes evenly, distributing extra classes if needed
            num_classes_to_assign = classes_per_teacher + (1 if extra_classes > 0 else 0)
            extra_classes -= 1
            teacher.assigned_classes = classes[class_index:class_index + num_classes_to_assign]
            class_index += num_classes_to_assign
            st.write(f"Teacher {teacher.name} (subject: {teacher.subject}) assigned to classes: {teacher.assigned_classes}")

# Initialize the student timetables before calling assign_labs
student_timetables = {class_name: np.empty((w, h), dtype=object) for class_name in classes}

# Function to assign labs, ensuring every class has each lab once a week
def assign_labs():
    for lab_name in labs:
        for class_name in classes:
            assigned = False
            while not assigned:
                day = random.randint(0, w - 1)
                start_hour = random.randint(0, h - lh)

                # Ensure labs are only scheduled before hour 4 (lunch break) or after hour 5
                if start_hour + lh <= 4 or start_hour >= 5:
                    # Check if the slot is free for consecutive lab hours
                    if all(student_timetables[class_name][day][start_hour + hour] is None for hour in range(lh)):
                        # Assign consecutive lab hours
                        for hour in range(start_hour, start_hour + lh):
                            student_timetables[class_name][day][hour] = lab_name
                        st.write(f"Assigned lab {lab_name} to {class_name} on Day {day + 1}, hours {start_hour}-{start_hour + lh - 1}")
                        assigned = True

# Function to check if a subject is assigned consecutively more than twice
def has_consecutive_periods(timetable, day, hour, subject):
    if hour > 1:
        if timetable[day][hour-1] == subject and timetable[day][hour-2] == subject:
            return True
    return False

# Function to check if a subject has been assigned more than 2 hours in a day
def has_exceeded_daily_limit(timetable, day, subject):
    return np.count_nonzero(timetable[day] == subject) >= 2

# Function to assign subjects and teachers to classes in a structured manner
def assign_subjects():
    for class_name in classes:
        for subject, required_hours in subject_hours_per_week[class_name].items():
            while required_hours > 0:
                # Find a teacher for the subject who is available and not over their teaching limit
                available_teachers = [teacher for teacher in teachers if
                                      teacher.subject == subject and teacher.teaching_hours > 0]

                if not available_teachers:
                    st.error(f"No available teachers for subject {subject} in class {class_name}. Cannot assign hours.")
                    break  # Exit the loop or handle this case appropriately

                assigned = False
                while not assigned:
                    day = random.randint(0, w - 1)
                    hour = random.randint(0, h - 1)

                    # Skip lunch break hour (hour 4)
                    if hour == 4:
                        continue

                    if student_timetables[class_name][day][hour] is None and not has_consecutive_periods(
                            student_timetables[class_name], day, hour, subject) and not has_exceeded_daily_limit(
                            student_timetables[class_name], day, subject):
                        # Assign the subject to the timetable and decrement the required hours
                        student_timetables[class_name][day][hour] = subject
                        required_hours -= 1
                        assigned = True

                        # Update the teacher's teaching hours and daily hours
                        available_teachers[0].teaching_hours -= 1
                        available_teachers[0].daily_hours[day] += 1
                        st.write(f"Assigned {subject} to {class_name} on Day {day + 1}, Hour {hour}")

# Call functions to assign labs and subjects
assign_labs()
assign_subjects()

# Display the generated timetable for each class
st.header("Generated Timetables")
for class_name in classes:
    st.write(f"Timetable for {class_name}:")
    st.table(student_timetables[class_name])