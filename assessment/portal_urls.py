from django.urls import path

from . import portal_views


urlpatterns = [
    path("login", portal_views.login_page, name="portal-login"),
    path("auth/login", portal_views.auth_login, name="portal-auth-login"),
    path("auth/logout", portal_views.auth_logout, name="portal-auth-logout"),
    path("clinics", portal_views.clinics_api, name="portal-clinics"),
    path("doctors", portal_views.doctors_api, name="portal-doctors"),
    path("doctors/<int:doctor_id>", portal_views.doctors_api, name="portal-doctor-detail"),
    path("patients", portal_views.patients_api, name="portal-patients"),
    path("patients/<int:patient_id>", portal_views.patients_api, name="portal-patient-detail"),
    path("assessment/patient/<int:patient_id>", portal_views.assessment_patient_api, name="portal-assessment-patient"),
    path("assessment/<int:assessment_id>/details", portal_views.assessment_details_api, name="portal-assessment-details"),
    path("appointments/booking-page", portal_views.booking_page, name="portal-booking-page"),
    path("appointments/slots", portal_views.appointment_slots_api, name="portal-appointment-slots"),
    path("appointments/book", portal_views.appointment_book_api, name="portal-appointment-book"),
    path("consultations", portal_views.consultation_save_api, name="portal-consultation-create"),
    path("consultations/doctor/dashboard", portal_views.doctor_dashboard_page, name="portal-doctor-dashboard"),
    path("consultations/doctor/calendar", portal_views.doctor_calendar_page, name="portal-doctor-calendar"),
    path("consultations/doctor/calendar-data", portal_views.doctor_calendar_data_api, name="portal-doctor-calendar-data"),
    path("consultations/doctor/day-slots", portal_views.doctor_day_slots_api, name="portal-doctor-day-slots"),
    path("consultations/doctor/appointments", portal_views.doctor_appointments_page, name="portal-doctor-appointments"),
    path("consultations/doctor/appointment/<int:appointment_id>", portal_views.doctor_appointment_page, name="portal-doctor-appointment"),
    path("consultations/doctor/patient/<int:patient_id>", portal_views.doctor_patient_detail_page, name="portal-doctor-patient-detail"),
    path(
        "consultations/doctor/appointment/<int:appointment_id>/save",
        portal_views.consultation_save_api,
        name="portal-doctor-consultation-save",
    ),
    path("consultations/patient/my-consultations", portal_views.patient_consultations_page, name="portal-patient-consultations"),
    path("consultations/<int:consultation_id>", portal_views.consultation_detail_api, name="portal-consultation-detail"),
    path("reports/generate", portal_views.report_generate_api, name="portal-report-generate"),
    path("admin/dashboard", portal_views.admin_dashboard_page, name="portal-admin-dashboard"),
    path("admin/doctors", portal_views.admin_doctors_page, name="portal-admin-doctors"),
    path("admin/patients", portal_views.admin_patients_page, name="portal-admin-patients"),
    path("admin/appointments", portal_views.admin_appointments_page, name="portal-admin-appointments"),
    path("admin/doctors/<int:doctor_id>/leave", portal_views.admin_mark_leave_api, name="portal-admin-doctor-leave"),
]
