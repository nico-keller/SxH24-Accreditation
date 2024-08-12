from barcodeScanning import *
from printServices import *
from airtableRequests import *
from rfidConnect import *
import streamlit as st

# Initialize session state variables if they don't exist
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'status_message' not in st.session_state:
    st.session_state['status_message'] = ""
if 'station_type' not in st.session_state:
    st.session_state['station_type'] = ""
if 'barcode_input' not in st.session_state:
    st.session_state['barcode_input'] = ""
if 'wrong_station' not in st.session_state:
    st.session_state['wrong_station'] = False
if 'invite_id' not in st.session_state:
    st.session_state['invite_id'] = False
if 'action_taken' not in st.session_state:
    st.session_state['action_taken'] = False
if 'already_accredited' not in st.session_state:
    st.session_state['already_accredited'] = False
if 'ip_address' not in st.session_state:
    st.session_state['ip_address'] = False



# Layout columns, can be adjusted as needed
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.caption("For IT support please contact Nicolas Keller (+41 76 687 75 43) or Athavan T. (+41 79 462 81 39)")
    st.caption("If the application gets bugged, please refresh the window and log in again.")
if st.session_state.get('is_logged_in', False):
    with col2:  # Place the logout button in the second column
        if st.button('Logout'):
            logout()

st.title("START Global - Accreditation")

# Container for login
login_container = st.container()
# Only show login fields if the user is not logged in
if not st.session_state['is_logged_in']:
    with login_container:
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            st.session_state['is_logged_in'], st.session_state['status_message'] = login(username, password)
            login_container.empty()  # Hide login fields after successful login

# Display status message
if st.session_state['status_message']:
    st.info(st.session_state['status_message'])
    st.session_state['status_message'] = ""

st.markdown(
    """
    <style>
        .stRadio > div{margin-bottom: 20px;}
    </style>
    """,
    unsafe_allow_html=True
)

# Show additional options if the user is logged in
if st.session_state['is_logged_in']:
    # Use markdown for flexible spacing options
    st.markdown("""<br>""", unsafe_allow_html=True)  # Adds a bit more space above the options
    
         

    
    with st.sidebar:
        st.caption("Please make sure that the IP address is up to date and select the correct Printer and Station type.")
        st.caption("You can find the phone's IP address under settings -> wifi -> info")
        st.caption("Paste the complete IP address of the Iphone you are using, for example, it should look like this: 10.255.164.36")
        st.session_state['ip_address'] = st.text_input("Enter IP address of the phone")
        printer_type = st.selectbox('Select Printer Type', ['HP', 'Samsung'])
        station_types = get_station_types()
        new_station_type = st.selectbox("Select Station Type", station_types,
                                        index=station_types.index(st.session_state['station_type'])
                                        if st.session_state['station_type'] in station_types else 0)
        if new_station_type != st.session_state.get('station_type', ''):
            st.session_state['station_type'] = new_station_type
            st.info('Station changed to: {}'.format(new_station_type))
            st.info(f"Allowed Group_Id's: {load_allowed_ids(new_station_type)}")
        options = ["Scan and Print Ticket", "Info desk - specific tickets", "AirTable Data / Look for Attendee", "Create new Attendee", "Manual Print"]
        selected_option = st.radio("Select an option", options)

    st.markdown("""<br>""", unsafe_allow_html=True)  # Adds space after the options

    if selected_option == "Scan and Print Ticket":
        st.text_input('Scan a barcode:', value="", key='barcode_input', on_change=on_barcode_scan(printer_type))

    elif selected_option == "Info desk - specific tickets":
        # Layout for ID input and barcode scanning
        invite_id_input, barcode_scan_input = st.columns(2)
        with invite_id_input:
            st.session_state['invite_id'] = st.text_input("Enter the attendee's invite ID", key='invite_id_direct')
        with barcode_scan_input:
            barcode_input = st.text_input('Scan a barcode', key='barcode_input_scan')
        if st.button("Print Ticket"):
            # Determine if an ID was entered directly or needs to be obtained from a barcode
            if st.session_state['invite_id'] != "":
                check_accredited(st.session_state['invite_id'])
                print_ticket(st.session_state['invite_id'], printer_type)
            elif barcode_input:
                barcode = read_barcode(barcode_input)
                # Assuming `read_barcode` returns the ID encoded in the barcode
                if barcode:
                    check_accredited(barcode)
                    print_ticket(barcode, printer_type)
                else:
                    st.error("Invalid barcode.")
            else:
                st.error("Please enter an attendee ID or scan a barcode.")

    elif selected_option == "AirTable Data / Look for Attendee":
        print_airtable_data()

    elif selected_option == "Create new Attendee":
        create_new_attendee()

    elif selected_option == "Manual Print":
        manual_print(printer_type)

    if st.session_state['wrong_station'] or st.session_state['already_accredited']:
        st.info("If you want to continue, press the Continue Anyway button, otherwise Abort.")
        col1, col2, col3 = st.columns(3)
        # Place each button in its own column
        with col1:
            continue_button = st.button("Continue Anyway")
        with col2:
            abort_button = st.button("Abort")
        with col3:
            nfc_button = st.button("RFID Write")
        if continue_button:
            if 'barcode_input' in globals():
                barcode = read_barcode(barcode_input)
            st.session_state['wrong_station'] = False
            st.session_state['action_taken'] = True
            st.session_state['already_accredited'] = False
            print_ticket(st.session_state['invite_id'], printer_type)
        if abort_button:
            st.session_state['wrong_station'] = False
            st.error("Aborting. The ticket will not be printed.")
            st.rerun()
        if nfc_button:
            send_get_request(st.session_state['ip_address'], st.session_state['invite_id'])
