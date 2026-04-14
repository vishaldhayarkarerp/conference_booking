# Copyright (c) 2026, e.Soft Techonoligies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, get_time, get_datetime


class ConferenceBooking(Document):

    def validate(self):

        self.set_defaults()
        self.set_calendar_datetimes()
        self.validate_management_reserved_room()
        self.validate_booking_time()
        self.validate_overlapping_booking()


    def set_calendar_datetimes(self):
        if self.booking_date and self.start_time:
            self.starts_on = get_datetime(f"{self.booking_date} {self.start_time}")

        if self.booking_date and self.end_time:
            self.ends_on = get_datetime(f"{self.booking_date} {self.end_time}")

# ----------------------------------------------------
# DEFAULT VALUES (Future-proofing)
# ----------------------------------------------------

    def set_defaults(self):
        # Auto set booked by
        if not self.booked_by:
            self.booked_by = frappe.session.user


# ----------------------------------------------------
# Reserved Room Permission Check
# ----------------------------------------------------

    def validate_management_reserved_room(self):

        if not self.conference_room:
            return

        room = frappe.get_doc("Conference Room", self.conference_room)

        if not room.is_active:
            frappe.throw("This conference room is inactive and cannot be booked.")

        if not room.reserved_for_management:
            return

        allowed_roles = ["HR Manager", "Administrator", "System Manager"]
        user_roles = frappe.get_roles(frappe.session.user)

        if not any(role in user_roles for role in allowed_roles):
            frappe.throw(
                "This conference room is reserved for office/management use only. "
                "Only HR Manager, Administrator, or System Manager can book it."
            )

# ----------------------------------------------------
# Date & Time Validation
# ----------------------------------------------------

    def validate_booking_time(self):

        # Cannot book in the past
        if self.booking_date and getdate(self.booking_date) < getdate(nowdate()):
            frappe.throw("You cannot book a conference room in the past.")

        # Full day booking support
        if self.full_day:
            self.start_time = "00:00:00"
            self.end_time = "23:59:59"
            return
        
        # Start & End Time mandatory
        if not self.start_time or not self.end_time:
            frappe.throw("Start Time and End Time are required.")

        start_time = get_time(self.start_time)
        end_time = get_time(self.end_time)

        #  End time must be after start time
        if end_time <= start_time:
            frappe.throw("End Time must be after Start Time.")

        # #  Optional: Office hours restriction (future ready)
        # office_start = get_time("09:00:00")
        # office_end = get_time("19:00:00")

        # if start_time < office_start or end_time > office_end:
        #     frappe.throw("Bookings are allowed only between 9 AM and 7 PM.")


# ----------------------------------------------------
# Overlapping Booking Validation
# ----------------------------------------------------


    def validate_overlapping_booking(self):
        
        if not self.conference_room or not self.booking_date:
            return
        
        # Skip cancelled & draft bookings
        if self.status in ["Cancelled", "Draft"]:
            return
        

        # ------------------------------------------------
        # FULL DAY CONFLICT CHECK (NEW)
        # ------------------------------------------------
  
        # Case 1: Existing FULL DAY booking blocks everything

        full_day_conflict = frappe.db.exists(
            "Conference Booking",
            {
                "conference_room": self.conference_room,
                "booking_date": self.booking_date,
                "status": ["in", ["Confirmed", "Reserved"]],
                "name": ["!=", self.name],
                "full_day": 1,
            }
        )

        if full_day_conflict:
            frappe.throw("Room already booked for the selected date (Full Day Booking).")

        # Case 2: If CURRENT booking is full day → no other bookings allowed

        if self.full_day:
            any_booking_exists = frappe.db.exists(
                "Conference Booking",
                {
                    "conference_room": self.conference_room,
                    "booking_date": self.booking_date,
                    "status": ["in", ["Confirmed", "Reserved"]],
                    "name": ["!=", self.name],
                }
            )


            if any_booking_exists:
                frappe.throw(
                    "Cannot book full day because the room already has bookings."
                )

            # Full day validated → skip time overlap logic
            return
        

        # ------------------------------------------------
        # PARTIAL TIME OVERLAP CHECK (EXISTING + BUFFER)
        # ------------------------------------------------

        room = frappe.get_doc("Conference Room", self.conference_room)
        buffer_minutes = room.buffer_minutes or 0


        def time_to_minutes(t):
            t = get_time(t)
            return t.hour * 60 + t.minute
        
        start_minutes = time_to_minutes(self.start_time) - buffer_minutes
        end_minutes = time_to_minutes(self.end_time) + buffer_minutes




        overlapping_booking = frappe.db.sql(
            """
            SELECT name
            FROM `tabConference Booking`
            WHERE
                conference_room = %s
                AND booking_date = %s
                AND status IN ('Confirmed', 'Reserved')
                AND name != %s
                AND (
                    (TIME_TO_SEC(start_time) / 60) < %s
                    AND (TIME_TO_SEC(end_time) / 60) > %s
                )
            """,
            (
                self.conference_room,
                self.booking_date,
                self.name,
                end_minutes,
                start_minutes,
            ),
        )

        if overlapping_booking:
            frappe.throw(
                "Room already booked or buffer time conflict exists for the selected slot."
            )




    # def validate_overlapping_booking(self):

    #     if not self.conference_room or not self.booking_date:
    #         return

    #     # Skip cancelled & draft bookings
    #     if self.status in ["Cancelled", "Draft"]:
    #         return

    #     room = frappe.get_doc("Conference Room", self.conference_room)
    #     buffer_minutes = room.buffer_minutes or 0

    #     def time_to_minutes(t):
    #         t = get_time(t)
    #         return t.hour * 60 + t.minute

    #     start_minutes = time_to_minutes(self.start_time) - buffer_minutes
    #     end_minutes = time_to_minutes(self.end_time) + buffer_minutes

    #     overlapping_booking = frappe.db.sql(
    #         """
    #         SELECT name
    #         FROM `tabConference Booking`
    #         WHERE
    #             conference_room = %s
    #             AND booking_date = %s
    #             AND status IN ('Confirmed', 'Reserved')
    #             AND name != %s
    #             AND (
    #                 (TIME_TO_SEC(start_time) / 60) < %s
    #                 AND (TIME_TO_SEC(end_time) / 60) > %s
    #             )
    #         """,
    #         (
    #             self.conference_room,
    #             self.booking_date,
    #             self.name,
    #             end_minutes,
    #             start_minutes,
    #         ),
    #     )

    #     if overlapping_booking:
    #         frappe.throw(
    #             "Room already booked or buffer time conflict exists for the selected slot."
    #         )



    # def validate_overlapping_booking(self):

    #     # If required fields missing → skip
    #     if not self.conference_room or not self.booking_date:
    #         return

    #     # Skip cancelled & draft bookings
    #     if self.status in ["Cancelled", "Draft"]:
    #         return
        

    #     overlapping_booking = frappe.db.exists(
    #         "Conference Booking",
    #         {
    #             "conference_room": self.conference_room,
    #             "booking_date": self.booking_date,
    #             "status": ["in", ["Confirmed", "Reserved"]],
    #             "name": ["!=", self.name],
    #             "start_time": ["<", self.end_time],
    #             "end_time": [">", self.start_time],
    #         }
    #     )

    #     if overlapping_booking:
    #         frappe.throw("Room already booked for the selected time slot.")








@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_rooms(doctype, txt, searchfield, start, page_len, filters):
    booking_date = filters.get("booking_date")
    start_time = filters.get("start_time")
    end_time = filters.get("end_time")
    full_day = frappe.utils.cint(filters.get("full_day"))
    current_booking = filters.get("current_booking")

    if not booking_date:
        return []

    # 1. Identify occupied rooms for the given slot
    occupied_rooms_query = """
        SELECT DISTINCT conference_room
        FROM `tabConference Booking`
        WHERE
            booking_date = %s
            AND status IN ('Confirmed', 'Reserved','Completed')
            AND name != %s
            AND (
                full_day = 1
                OR %s = 1
                OR (
                    start_time < %s
                    AND end_time > %s
                )
            )
    """

    # If full_day is current selection, we check against ANY booking
    # Otherwise we check against full_day bookings OR overlapping time bookings
    check_start = end_time if not full_day else "23:59:59"
    check_end = start_time if not full_day else "00:00:00"

    occupied_rooms = frappe.db.sql(occupied_rooms_query, (
        booking_date,
        current_booking or "",
        full_day,
        check_start,
        check_end
    ), as_dict=True)

    occupied_room_names = [d.conference_room for d in occupied_rooms]

    # 2. Get all active rooms that are NOT in the occupied list
    rooms_filter = {"is_active": 1}
    if txt:
        rooms_filter["name"] = ["like", f"%{txt}%"]
    
    if occupied_room_names:
        rooms_filter["name"] = ["not in", occupied_room_names]

    return frappe.get_all(
        "Conference Room",
        filters=rooms_filter,
        fields=["name", "room_name"],
        as_list=True
    )
