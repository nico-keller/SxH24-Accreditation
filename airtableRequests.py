from pyairtable import Api
import json
from datetime import datetime
import streamlit as st
import random
import pandas as pd
import requests

with open('config.json', 'r') as config_file:
    config = json.load(config_file)
    api_key = config['api_key']
    base_id = config['base_id']
    AccreditationUserTable = config['AccreditationUserTable']
    AttendeesTable = config['AttendeesTable']
    LogsTable = config['LogsTable']
    Computer_id = config['Computer_Id']
    ApplicationsTable = config['ApplicationsTable']
    PrivilegesTable = config['PrivilegesTable']
    FormatsTable = config['FormatsTable']


with open('station_config.json', 'r') as station_config_file:
    station_config = json.load(station_config_file)


def load_allowed_ids(station_type):
    return set(station_config.get(station_type, []))


def login(username, password):
    api = Api(api_key)
    base = api.base(base_id)
    table = base.table(AccreditationUserTable)

    query_formula = f"{{Username}}='{username}'"
    records = table.all(formula=query_formula)
    if records:
        stored_password = records[0]['fields'].get('Password')
        user_role = records[0]['fields'].get('Privilege')  # Retrieve user role
        if password == stored_password:
            # Store user role in session state
            st.session_state['user_role'] = user_role
            return True, "Login successful."
        else:
            return False, "Incorrect password. Please try again."
    else:
        return False, "Username not found. Please try again."


def logout():
    st.session_state['is_logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['status_message'] = ""
    st.session_state['station_type'] = ""
    st.rerun()


def check_id_in_station(group_id, station):
    if group_id in set(station_config.get(station, [])):
        return True
    else:
        st.warning(f"Warning: Attendee is at the incorrect accreditation station. This attendee is in the group: {get_group_id_name(group_id)}")
        return False


def get_station_types():
    return list(station_config.keys())


def log_accreditation(invite_id):
    api, base, table = initialize_table(LogsTable)
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    log_data = {
        "Id": invite_id,
        "PrivilegesId": "3",
        "Amount": "1",
        "Created": current_datetime,
        "Responsible": Computer_id
    }
    try:
        table.create(log_data)
    except Exception as e:
        print(f"Error logging accreditation: {e}")


def get_attendee_field_info(invite_id, field):
    api, base, table = initialize_table(AttendeesTable)
    query_formula = f"{{Id}}='{invite_id}'"
    try:
        records = table.all(formula=query_formula)
        if records:
            attendee_record = records[0]
            group_id = attendee_record['fields'].get(field)
            return group_id
    except Exception as error:
        print('Error:', error)


def get_attendee_object(invite_id):
    api, base, table = initialize_table(AttendeesTable)
    query_formula = f"{{Id}}='{invite_id}'"
    try:
        records = table.all(formula=query_formula)
        if records:
            attendee_record = records[0]
            return attendee_record
        else:
            st.warning(f"No attendee found with ID {invite_id}. Please check the ID and try again.")
            return ''
    except Exception as error:
        print('Error:', error)


def initialize_table(table_name):
    api = Api(api_key)
    base = api.base(base_id)
    table = base.table(table_name)
    return api, base, table


def get_group_id_name(group_id):
    for station_type, group_ids in station_config.items():
        # Check if the provided group_id is in the list of group IDs for the current station type
        if group_id in group_ids:
            group_id_name = station_type.replace("Station", "")
            return group_id_name
        # Return None or a default value if the group_id does not match any station type
    return None


def update_accredited_date(invite_id):
    api, base, table = initialize_table(AttendeesTable)
    try:
        records = table.all(formula=f"{{Id}}='{invite_id}'")
        if records:
            # Format the datetime in ISO 8601 format
            current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            record_id = records[0]['id']
            table.update(record_id, {'Accredited': True, 'Accredited_date': current_datetime})
            st.success("Accredited date and time updated to now.")
        else:
            st.error("No record found with the specified ID to update.")
    except Exception as error:
        st.write(f'Error updating accredited date and time: {error}')


def create_new_attendee():
    api, base, users_table = initialize_table(AccreditationUserTable)

    query_formula = f"{{Username}}='CREATE_NEW_ATTENDEE'"
    records = users_table.all(formula=query_formula)
    SUPPORTER_PASSWORD = records[0]['fields'].get('Password')

    is_master = 'user_role' in st.session_state and st.session_state['user_role'] == "Master"
    is_supporter = 'user_role' in st.session_state and st.session_state['user_role'] == "Supporter"
    access_granted = False

    if is_master:
        access_granted = True
    elif is_supporter:
        # Prompt for password if the user is a Supporter
        if 'password_correct' not in st.session_state:
            st.session_state['password_correct'] = False
        supporter_password = st.text_input("Enter access password:", type="password", key='supporter_access_password',
                                           placeholder='Access denied: Ask your supervisor for the password!')
        if supporter_password:
            if supporter_password == SUPPORTER_PASSWORD:
                access_granted = True
                st.session_state['password_correct'] = True
                st.success("Access granted.")
            else:
                st.error("Access denied: Incorrect password.")
    if access_granted:
        attendees_table = base.table(AttendeesTable)
        # List all fields excluding "Created_on_Event" since we'll set it manually
        fields = [ "Mail", "Firstname", "Lastname", "University", "Field of Study", "Level of Study",
                  "Expected graduation", "Company"]
        # Collect data for each field using Streamlit's text input
        new_attendee_data = {}
        for field in fields:
            value = st.text_input(f"{field}:", key=f'input_{field}').strip()  # Unique key for each input
            if value:  # Only add data if the user entered something
                new_attendee_data[field] = value
        # Manually set "Created_on_Event" to True
        new_attendee_data["Created_on_Event"] = True
        
        # Generate a unique random ID
        new_attendee_id = random.randint(10000, 11000)
        new_attendee_data["Id"] = str(new_attendee_id)
        new_attendee_data["GroupId"] = "15863"
        # Button to create new attendee
        if st.button("Add New Attendee", key='add_attendee'):
            if new_attendee_data:  # Check if data is entered
                try:
                    # Create new attendee record
                    attendees_table.create(new_attendee_data)
                    st.success("New attendee added successfully.")
                except Exception as error:
                    st.error(f"Error creating new attendee: {error}")
            else:
                st.warning("No data entered. Please fill out the fields before adding.")
    else:
        if not (is_master or is_supporter):
            st.error("Access denied: You do not have permissions to add new attendees.")


def check_accredited(invite_id):
    api, base, table = initialize_table(AttendeesTable)

    # Fetch record by attendee ID
    query_formula = f"{{Id}}='{invite_id}'"
    records = table.all(formula=query_formula)

    if records:
        accredited = records[0]['fields'].get('Accredited', False)

        if not accredited:
            st.session_state['already_accredited'] = False
            return True
        else:
            st.warning("Warning: Attendee has already been accredited.")
            st.session_state['already_accredited'] = True
            return False
    else:
        st.warning("No record found with the specified ID.")
        return False


def print_airtable_data():
    api, base, table = initialize_table(AttendeesTable)
    try:
        records = table.all()
        if records:
            # Collect fields from all records
            available_fields = set()
            for record in records:
                available_fields.update(record['fields'].keys())

            # Search boxes for first name, last name, and ID
            id_search_query = st.text_input("Search by ID", "")
            firstname_search_query = st.text_input("Search by First Name", "")
            lastname_search_query = st.text_input("Search by Last Name", "")

            # Filter records based on search queries if provided
            filtered_records = records
            if firstname_search_query:
                filtered_records = [record for record in filtered_records if
                                    firstname_search_query.lower() in record['fields'].get("Firstname", "").lower()]
            if lastname_search_query:
                filtered_records = [record for record in filtered_records if
                                    lastname_search_query.lower() in record['fields'].get("Lastname", "").lower()]
            if id_search_query:
                filtered_records = [record for record in filtered_records if
                                    id_search_query.lower() in record['fields'].get("Id", "").lower()]

            # Sort field selection
            sort_field = st.selectbox("Select the field to sort by", sorted(available_fields), index=0)

            # Adjusted sorting logic to handle boolean values as strings
            sorted_records = sorted(filtered_records, key=lambda r: str(r['fields'].get(sort_field, '')).lower())

            # Ask user for the maximum number of records to display
            max_records = st.number_input("Maximum number of records to display", min_value=1, value=10, step=1)

            # Apply the limit to the sorted records
            limited_sorted_records = sorted_records[:max_records]

            # Predefine your column order here
            column_order = ["Id", "Firstname", "Lastname", "Mail", "GroupId", "Ticket", "Company", "University", "Level of Study", "Registered for Formats", "Accredited",
                            "Accredited_date"]

            # Ensure all predefined columns are in available_fields
            column_order = [col for col in column_order if col in available_fields]

            # Convert sorted (and limited) records to a format suitable for display in a table
            table_data = []
            for record in limited_sorted_records:
                row = {}
                for key in column_order:
                    value = record['fields'].get(key, '')
                    if isinstance(value, bool):  # Convert boolean to "True" or "False"
                        row[key] = "True" if value else "False"
                    else:
                        row[key] = str(value)
                table_data.append(row)

            # Convert to DataFrame using predefined column order
            df = pd.DataFrame(table_data, columns=column_order)

            # Display table
            st.table(df)
        else:
            st.write("No records found.")
    except Exception as error:
        st.error(f'Error: {error}')


def print_attendee_info(invite_id):
    api, base, table = initialize_table(AttendeesTable)
    try:
        records = table.all(formula=f"{{Id}}='{invite_id}'")
        # Filter records to find the one with the matching invite_id
        filtered_records = [record for record in records if
                            record['fields'].get("Id", "") == invite_id]

        if filtered_records:
            # Predefine your column order here
            column_order = ["Id", "Firstname", "Lastname", "Mail", "GroupId", "Ticket", "Company", "University", "Level of Study",
                            "Field of Study", "Registered for Formats", "Accredited",
                            "Accredited_date"]
            # Convert filtered record to a format suitable for display in a table
            table_data = []
            for record in filtered_records:
                row = {key: str(record['fields'].get(key, '')) for key in column_order if
                       key in record['fields']}  # Convert all values to string
                table_data.append(row)
            # Convert to DataFrame using predefined column order
            df = pd.DataFrame(table_data, columns=[col for col in column_order if col in table_data[0]])

            # Display table
            st.subheader('Attendee Info')
            st.table(df)
        else:
            st.write("No records found.")
    except Exception as error:
        st.error(f'Error: {error}')

def print_log_info(invite_id):
    api, base, table = initialize_table(LogsTable)
    try:
        # Corrected the formula by adding the missing curly brace and quotation mark
        records = table.all(formula=f"{{Id}}='{invite_id}'")
        # Filter records to find the one with the matching invite_id
        filtered_records = [record for record in records if
                            record['fields'].get("Id", "") == invite_id]

        if filtered_records:
            # Predefine your column order here
            column_order = ["Privilege", "Amount", "Created", "Responsible"]
            # Convert filtered record to a format suitable for display in a table
            table_data = []
            for record in filtered_records:
                row = {key: str(record['fields'].get(key, '')) for key in column_order if
                       key in record['fields']}  # Convert all values to string
                table_data.append(row)
            # Convert to DataFrame using predefined column order
            df = pd.DataFrame(table_data, columns=[col for col in column_order if col in table_data[0]])

            # Display table
            st.subheader('Accreditation Logs')
            st.table(df)
        else:
            pass
    except Exception as error:
        st.error(f'Error: {error}')



# these functions are still in the works and not ready
def get_formats_table(format_ids):
    api, base, formats_table = initialize_table(FormatsTable)
    format_types, companies, format_names, rooms, dates = [], [], [], [], []
    for format_id in format_ids:
        query_formula_formats = f"{{Id}}='{format_id}'"
        try:
            formats_records = formats_table.all(formula=query_formula_formats)
            if formats_records:
                for formats_record in formats_records:
                    format_type = formats_record['fields'].get("Format Type", "N/A")
                    company = formats_record['fields'].get("Company (Host)", "N/A")
                    format_name = formats_record['fields'].get("Name", "N/A")
                    room = formats_record['fields'].get("Room", "N/A")  # Assuming 'Room' is the field name
                    date = formats_record['fields'].get("Date", "N/A")  # Assuming 'Date' is the field name
                    format_types.append(format_type)
                    companies.append(company)
                    format_names.append(format_name)
                    rooms.append(room)
                    dates.append(date)
        except Exception as error:
            st.error(f'Error: {error}')
            format_types.append("N/A")
            companies.append("N/A")
            format_names.append("N/A")
            rooms.append("N/A")
            dates.append("N/A")
    return format_types, companies, format_names, rooms, dates


def get_applications_table(attendee_id):
    api, base, applications_table = initialize_table(ApplicationsTable)
    query_formula_applications = f"{{AttendeeId}}='{attendee_id}'"
    format_ids = []
    try:
        applications_records = applications_table.all(formula=query_formula_applications)
        for application_record in applications_records:
            status = application_record['fields'].get("Status", "N/A")
            if status == "Accepted":  
                format_id = application_record['fields'].get("FormatId", "N/A")
                format_ids.append(format_id)
        return format_ids
    except Exception as error:
        st.error(f'Error: {error}')
    return ["N/A"]


def print_privileges_and_formats(invite_id):
    Id = get_attendee_field_info(invite_id, 'AttendeeId')
    format_ids = get_applications_table(Id)
    if format_ids == ["N/A"]:  
        return
    format_types, companies, format_names, rooms, dates = get_formats_table(format_ids)
    # Updated data structure to include Room and Date
    data = {
        'Format Type': format_types,
        'Format Name': format_names,
        'Company': companies,
        'Room': rooms, 
        'Date': dates   
    } 
    # Create and display DataFrame
    df = pd.DataFrame(data)
    if not df.empty:
        st.subheader('Workshop Applications')
        st.table(df)
    else:
        return

