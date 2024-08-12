from PIL import Image, ImageDraw, ImageFont, ImageWin
import subprocess
import os
from airtableRequests import *
from rfidConnect import *
import streamlit as st

# ExampleBarcodeid¡1170296MoreText

a6_width_pixels, a6_height_pixels = int(4.1 * 600), int(5.8 * 600)

with open('config.json', 'r') as config_file:
    font_path = config['Font_Path']
    Group_Ids_Without_Company = config['Group_Ids_Without_Company']


def create_and_print_image(firstname, lastname, company, group_id, printer_type):
    image = Image.new('RGB', (a6_width_pixels, a6_height_pixels), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Fixed font sizes
    font_size_names = 160
    font_size_company = 110

    if len(firstname) > 22 or len(lastname) > 22:
        font_size_names = 85
    elif len(firstname) > 16 or len(lastname) > 16:
        font_size_names = 110
    elif len(firstname) > 14 or len(lastname) > 14:
        font_size_names = 125
    elif len(firstname) > 11 or len(lastname) > 11:
        font_size_names = 140

    if company:
        if len(company) > 40:
            font_size_company = 45
        elif len(company) > 30:
            font_size_company = 57
        elif len(company) > 26:
            font_size_company = 65
        elif len(company) > 23:
            font_size_company = 73
        elif len(company) > 20:
            font_size_company = 80
        elif len(company) > 17:
            font_size_company = 85

    # Load fonts
    font_names = ImageFont.truetype(font_path, font_size_names)
    font_company = ImageFont.truetype(font_path, font_size_company)

    # Adjust for printer type
    if printer_type == 'HP':
        y_position_first_name_adjustment = 250
        right_shift = -620
        bottom_margin = 2345
        if not company or company == '' or group_id in Group_Ids_Without_Company:
            bottom_margin = 2240
        starting_y_position = a6_height_pixels - bottom_margin
        y_position_first_name = starting_y_position - y_position_first_name_adjustment
        y_position_last_name = y_position_first_name + 175
        y_position_company = y_position_last_name + 225
    elif printer_type == 'Samsung':
        y_position_first_name_adjustment = 250
        right_shift = 0
        bottom_margin = 2245
        if not company or company == '' or group_id in Group_Ids_Without_Company:
            bottom_margin = 2165
        starting_y_position = a6_height_pixels - bottom_margin
        y_position_first_name = starting_y_position - y_position_first_name_adjustment
        y_position_last_name = y_position_first_name + 175
        y_position_company = y_position_last_name + 225


    # Centering text
    # Calculate centered x-coordinate for each text
    x_coordinate_first_name, _ = center_text_position(firstname, font_names, draw, y_position_first_name, right_shift)
    x_coordinate_last_name, _ = center_text_position(lastname, font_names, draw, y_position_last_name, right_shift)
    if company and group_id not in Group_Ids_Without_Company:
        x_coordinate_company, _ = center_text_position(company, font_company, draw, y_position_company, right_shift)

    # Drawing centered text
    draw.text((x_coordinate_first_name, y_position_first_name), firstname, font=font_names, fill=(0, 0, 0))
    draw.text((x_coordinate_last_name, y_position_last_name), lastname, font=font_names, fill=(0, 0, 0))
    if company and group_id not in Group_Ids_Without_Company:
        draw.text((x_coordinate_company, y_position_company), company, font=font_company, fill=(0, 0, 0))


    temp_image_path = 'temp_ticket.png'
    image.save(temp_image_path)
    print_image(temp_image_path)
    os.remove(temp_image_path)


def print_image(image_path):
    # Print the image using the lpr command
    try:
        subprocess.run(["lpr", image_path], check=True)
    except subprocess.CalledProcessError as e:
        st.write(f"Failed to print. Error: {e}")
    except Exception as e:
        st.write(f"An unexpected error occurred: {e}")

def center_text_position(text, font, draw, y, x_shift):
    # Calculate the position to center the text
    text_bbox = draw.textbbox((0, 0), text, font)
    text_width = text_bbox[2] - text_bbox[0]
    x = (a6_width_pixels - text_width) / 2
    return x + x_shift, y


def print_ticket(invite_id, printer_type):
    attendee_record = get_attendee_object(invite_id)
    if attendee_record == '':
        st.info('No attendee info found.')
    first_name = attendee_record['fields'].get('Firstname', '')
    last_name = attendee_record['fields'].get('Lastname', '')
    company = attendee_record['fields'].get('Company', '')
    group_id = attendee_record['fields']['GroupId']
    check_station = check_id_in_station(group_id, st.session_state['station_type'])

    if not check_station:
        st.session_state['wrong_station'] = True

    if (st.session_state['action_taken'] or check_station) and st.session_state['already_accredited'] is False:
        # Proceed with the rest only if allowed or after pressing "Continue Anyway"
        try:
            group_id_name = get_group_id_name(group_id)
            st.info(f'Printing ticket for: {first_name} {last_name}, Company: {company}, Group: {group_id_name}, Group ID: {group_id}')
            create_and_print_image(first_name, last_name, company, group_id, printer_type)
            update_accredited_date(invite_id)
            send_get_request(st.session_state['ip_address'], invite_id)
            log_accreditation(invite_id)
            print_attendee_info(invite_id)
            print_log_info(invite_id)
            print_privileges_and_formats(invite_id)
        except Exception as e:
            st.error(f"Error while printing ticket: {e}")
            st.session_state['action_taken'] = False
        finally:
            st.session_state['invite_id'] = ""
            st.session_state['action_taken'] = False
            st.session_state['wrong_station'] = False
            st.session_state['already_accredited'] = False

def manual_print(printer_type):
    api, base, users_table = initialize_table(AccreditationUserTable)

    query_formula = f"{{Username}}='PRINT_MANUALLY'"
    records = users_table.all(formula=query_formula)
    PRINT_PASSWORD = records[0]['fields'].get('Password')

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
            if supporter_password == PRINT_PASSWORD:
                access_granted = True
                st.session_state['password_correct'] = True
                st.success("Access granted.")
            else:
                st.error("Access denied: Incorrect password.")
    if access_granted:
        first_name = st.text_input("Enter first name")
        last_name = st.text_input("Enter last name")
        company_name = st.text_input("Enter company name")
        group_id = 00000

        print_button = st.button("Print")
        if print_button:
            create_and_print_image(first_name, last_name, company_name, group_id,printer_type)

