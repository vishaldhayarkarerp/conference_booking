// Copyright (c) 2026, e.Soft Techonoligies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Conference Booking", {
	setup(frm) {
		// Filter rooms based on selected date and time
		frm.set_query("conference_room", function () {
			return {
				query: "conference_room_booking.conference_room_booking.doctype.conference_booking.conference_booking.get_available_rooms",
				filters: {
					booking_date: frm.doc.booking_date,
					start_time: frm.doc.start_time,
					end_time: frm.doc.end_time,
					full_day: frm.doc.full_day || 0,
					current_booking: frm.doc.name
				}
			};
		});
	},

	onload(frm) {
		// Store original time values when form loads
		frm._original_start_time = frm.doc.start_time;
		frm._original_end_time = frm.doc.end_time;
	},

	refresh(frm) {
		// Restrict date picker to today and future (disables clicking previous dates)
		frm.set_df_property('booking_date', 'datepicker_options', {
			minDate: new Date()
		});
	},

	booking_date(frm) {
		validate_date(frm);
		refresh_room_selection(frm);
	},

	start_time(frm) {
		// Only show confirmation for existing documents (not new)
		if (frm.doc.name && frm.doc.name !== 'new' && frm._original_start_time && frm.doc.start_time !== frm._original_start_time) {
			// Calculate if it's postpone or prepone
			const is_postpone = frm.doc.start_time > frm._original_start_time;
			const action = is_postpone ? 'postpone' : 'prepone';

			frappe.confirm(
				__('Are you sure you want to change the start time? This will {0} the booking.', [action]),
				() => {
					// User confirmed - update original value and proceed
					frm._original_start_time = frm.doc.start_time;
					refresh_room_selection(frm);
				},
				() => {
					// User cancelled - revert to original value
					frm.set_value('start_time', frm._original_start_time);
				}
			);
		} else {
			refresh_room_selection(frm);
		}
	},

	end_time(frm) {
		// Only show confirmation for existing documents (not new)
		if (frm.doc.name && frm.doc.name !== 'new' && frm._original_end_time && frm.doc.end_time !== frm._original_end_time) {
			// Calculate if it's postpone or prepone
			const is_postpone = frm.doc.end_time > frm._original_end_time;
			const action = is_postpone ? 'postpone' : 'prepone';

			frappe.confirm(
				__('Are you sure you want to change the end time? This will {0} the booking.', [action]),
				() => {
					// User confirmed - update original value and proceed
					frm._original_end_time = frm.doc.end_time;
					refresh_room_selection(frm);
				},
				() => {
					// User cancelled - revert to original value
					frm.set_value('end_time', frm._original_end_time);
				}
			);
		} else {
			refresh_room_selection(frm);
		}
	},

	full_day(frm) {
		refresh_room_selection(frm);
	}
});

function validate_date(frm) {
	if (frm.doc.booking_date && frappe.datetime.get_diff(frm.doc.booking_date, frappe.datetime.nowdate()) < 0) {
		frappe.msgprint(__('Booking Date cannot be in the past'));
		frm.set_value('booking_date', '');
	}
}

function refresh_room_selection(frm) {
	// If date and times are set, clear room if it's no longer available (optional UX)
	// But mainly we just want to ensure the list is fresh when they click it
	if (frm.doc.booking_date && (frm.doc.full_day || (frm.doc.start_time && frm.doc.end_time))) {
		// Room query will handle the filtering when the user clicks the field
	}
}
