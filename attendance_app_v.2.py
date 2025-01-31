import streamlit as st
import pandas as pd
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

# Constants
EMPLOYEE_CSV = "employees.csv"
ATTENDANCE_CSV = "attendance.csv"
LEAVE_CSV = "leaves.csv"
ADMIN_EMAIL = "vysakharaghavan@gmail.com"

# Constants for email reminder
REMINDER_THRESHOLD = timedelta(hours=10)  # 10 hours threshold

# Load CSV files
def load_data():
    employees = pd.read_csv(EMPLOYEE_CSV, dtype={"passkey": str})  # Force passkey as string
    attendance = pd.read_csv(ATTENDANCE_CSV)
    leaves = pd.read_csv(LEAVE_CSV)
    
    # Strip any leading/trailing spaces from column names
    employees.columns = employees.columns.str.strip()
    attendance.columns = attendance.columns.str.strip()
    leaves.columns = leaves.columns.str.strip()
    
    return employees, attendance, leaves

# Save data back to CSV
def save_data(df, filename):
    df.to_csv(filename, index=False)

# Send email notification
def send_email(to_email, subject, body):
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("rshm.jp07@gmail.com", "sipw aiba yfcr elkd")
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail("rshm.jp07@gmail.com", to_email, message)
    except Exception as e:
        st.error(f"Email error: {e}")

# Load data
employees, attendance, leaves = load_data()

# Function to send reminder emails if needed
def send_clock_out_reminder(employee, attendance):
    today = datetime.now().strftime("%Y-%m-%d")
    user_attendance = attendance[(attendance["name"] == employee["name"]) & (attendance["clock_in"].str.startswith(today))]
    
    if not user_attendance.empty:
        last_clock_in_time_str = user_attendance.iloc[-1]["clock_in"]
        last_clock_in_time = datetime.strptime(last_clock_in_time_str, "%H:%M")
        
        current_time = datetime.now()
        if current_time - last_clock_in_time > REMINDER_THRESHOLD:
            if pd.isna(user_attendance.iloc[-1]["clock_out"]):
                send_email(
                    employee["email"],
                    "Reminder: Clock-Out Pending",
                    f"Dear {employee['name']},\n\n"
                    f"This is a reminder that you haven't clocked out yet.\n"
                    f"Clock-In Time: {last_clock_in_time_str}\n"
                    f"Current Time: {current_time.strftime('%H:%M')}\n\n"
                    "Please make sure to clock out as soon as possible.\n\n"
                    "Thank you!"
                )
                st.success(f"Reminder sent to {employee['name']} for not clocking out after 10 hours.")

# Check for clock-out reminders for all employees when the app loads or every time they interact
for _, employee in employees.iterrows():
    send_clock_out_reminder(employee, attendance)

# Title for the app
st.title("Attendance and Leave Management System")
st.header("Qurocare - ALMS Tool")

# Employee Login Section
name_options = ["Select Your Name"] + list(employees["name"].unique())
name = st.selectbox("Select Your Name", name_options)
passkey = st.text_input("Enter Passkey", type="password")

if name != "Select Your Name" and passkey:
    # Fetch user details
    user = employees[(employees["name"] == name) & (employees["passkey"] == passkey)]
    
    if not user.empty:
        user = user.iloc[0]  # Extract the first matching row
        actual_clock_in = user["actual_clock_in"]
        today = datetime.now().strftime("%Y-%m-%d")
        user_attendance = attendance[(attendance["name"] == name) & (attendance["clock_in"].str.startswith(today))]
        
        # Show welcome message
        st.subheader(f"Welcome, {user['name']}!")
        st.subheader("Kindly mark your attendance")
        
        # Clock In/Out Section (single toggle button)
        clocked_in = False
        if user_attendance.empty or pd.isna(user_attendance.iloc[-1]["clock_out"]):
            if 'clock_in_time' not in st.session_state:
                st.session_state.clock_in_time = None
                st.session_state.clock_out_time = None

            # Display the button (Clock In/Clock Out)
            if st.session_state.clock_in_time is None:
                # Clock In action
                if st.button("Clock In"):
                    clock_in_time = datetime.now().strftime("%H:%M")
                    status = "Half Day" if datetime.strptime(clock_in_time, "%H:%M") > (datetime.strptime(actual_clock_in, "%H:%M") + timedelta(minutes=10)) else "Full Day"
                    new_entry = pd.DataFrame({
                        "id": [len(attendance) + 1],
                        "name": [name],
                        "email": [user["email"]],
                        "registered_id": [user["registered_id"]],
                        "clock_in": [clock_in_time],
                        "clock_out": [None],
                        "duration": [None],
                        "status": [status]
                    })
                    attendance = pd.concat([attendance, new_entry], ignore_index=True)
                    save_data(attendance, ATTENDANCE_CSV)
                    st.session_state.clock_in_time = clock_in_time
                    st.session_state.status = status
                    st.success(f"Clocked in at {clock_in_time}. Status: {status}")
            
            elif st.session_state.clock_in_time is not None and st.session_state.clock_out_time is None:
                # Clock Out action
                if st.button("Clock Out"):
                    clock_out_time = datetime.now().strftime("%H:%M")
                    clock_in_time = st.session_state.clock_in_time
                    duration = (datetime.strptime(clock_out_time, "%H:%M") - datetime.strptime(clock_in_time, "%H:%M")).seconds / 3600
                    attendance.loc[attendance["clock_in"] == clock_in_time, ["clock_out", "duration"]] = [clock_out_time, duration]
                    save_data(attendance, ATTENDANCE_CSV)
                    st.session_state.clock_out_time = clock_out_time
                    st.session_state.duration = duration
                    st.success(f"Clocked out at {clock_out_time}. Worked for {duration:.2f} hours.")
                    
                    # Display clock-out time and duration
                    st.write(f"Clocked out at: {clock_out_time}")
                    st.write(f"Total duration: {duration:.2f} hours")

            # Re-enable Clock In after clocking out
            if st.session_state.clock_out_time is not None:
                st.session_state.clock_in_time = None
                st.session_state.clock_out_time = None

       # Leave Application Section
        st.subheader("Apply for Leave")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        reason = st.text_area("Reason")
        
        if st.button("Apply Leave"):
            new_leave = pd.DataFrame({
                "id": [len(leaves) + 1],
                "name": [name],
                "email": [user["email"]],
                "registered_id": [user["registered_id"]],
                "start_date": [start_date],
                "end_date": [end_date],
                "reason": [reason]
            })
            leaves = pd.concat([leaves, new_leave], ignore_index=True)
            save_data(leaves, LEAVE_CSV)
            #send_email(ADMIN_EMAIL, "New Leave Request", f"{name} applied for leave from {start_date} to {end_date}.")
            send_email(
               ADMIN_EMAIL, 
               "New Leave Request", 
               f"Employee Name: {name}\n"
               f"Email: {user['email']}\n"
               f"Start Date: {start_date}\n"
               f"End Date: {end_date}\n"
               f"Reason: {reason}\n\n"
               "Kindly respond to this leave application."
            )
            st.success("Leave Applied Successfully! Notification sent to Admin.")
                
        # Logout Button
        if st.button("Logout"):
            st.experimental_rerun()  # This will refresh the page for re-login
        
else:
    if name == "Select Your Name":
        st.error("Please select a valid name.")
    elif not passkey:
        st.error("Please enter your passkey.")
