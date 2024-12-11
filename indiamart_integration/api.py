from __future__ import unicode_literals
import frappe
from frappe.utils import cint, format_datetime, add_days, today, date_diff, getdate, get_last_day, flt, nowdate
from frappe import throw, msgprint, _
from datetime import date
import re
import json
import traceback
import urllib
from urllib.request import urlopen
import requests

india_mart_setting = frappe.get_doc("IndiaMart Setting", "IndiaMart Setting")
@frappe.whitelist()
def sync_india_mart_lead(from_date,to_date):
	try:
		if (not india_mart_setting.url
			# or not india_mart_setting.mobile
			or not india_mart_setting.key):
				frappe.throw(
					msg=_('URL, Key mandatory for Indiamart API Call. Please set them and try again.'),
					title=_('Missing Setting Fields')
				)
		req = get_request_url
		res = requests.post(url=req)
		if res.text:
			count = 0
			for row in json.loads(res.text):
				if not row.get("Error_Message")==None:
					frappe.throw(row["Error_Message"])
				else:
					doc=add_lead(row["SENDERNAME"],row["SENDEREMAIL"],row["MOB"],row["SUBJECT"],row["QUERY_ID"])
					if doc:
						count += 1
			if not count == 0:
				frappe.msgprint(_("{0} Lead Created").format(count))

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("India Mart Sync Error"))

def get_request_url(india_mart_setting):
	#https://mapi.indiamart.com/wservce/crm/crmListing/v2/?glusr_crm_key=mRyzEr9v7XzFTPej4HaK7l6MqlrMnTk=&start_time=14-Oct-202409:00:00&end_time=14-Nov-202416:00:00
	#req = str(india_mart_setting.url)+'/GLUSR_MOBILE_KEY/'+str(india_mart_setting.key)+'/Start_Time/'+str(india_mart_setting.from_date)+'/End_Time/'+str(india_mart_setting.to_date)+'/'
	req = f"{india_mart_setting.url}/?glusr_crm_key={india_mart_setting.key}"
	return req

@frappe.whitelist()
def cron_sync_lead():
	try:
		sync_india_mart_lead(today(),today())
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("India Mart Sync Error"))

@frappe.whitelist()
def add_lead(lead_data):
	try:
		if not frappe.db.exists("Lead",{"india_mart_id":lead_data["QUERY_ID"]}):
			doc = frappe.get_doc(dict(
				doctype="Lead",
				lead_name=lead_data["SENDERNAME"],
				email_id=lead_data["SENDEREMAIL"],
				phone=lead_data["MOB"],
				requirement=lead_data["SUBJECT"],
				india_mart_id=lead_data["QUERY_ID"],
				source="India Mart"           
			)).insert(ignore_permissions = True)
			return doc
	except Exception as e:
		frappe.log_error(frappe.get_traceback())


@frappe.whitelist(allow_guest=True)
def create_lead_indiamart(data):
    try:
        indiamart_lead = frappe.get_doc({
            "doctype": "IndiaMart Lead",
            "unique_query_id": data.get("UNIQUE_QUERY_ID"),
            "query_type": data.get("QUERY_TYPE"),
            "query_time": data.get("QUERY_TIME"),
            "sender_name": data.get("SENDER_NAME"),
            "sender_mobile": data.get("SENDER_MOBILE"),
            "sender_email": data.get("SENDER_EMAIL"),
            "subject": data.get("SUBJECT"),
            "sender_company": data.get("SENDER_COMPANY"),
            "sender_address": data.get("SENDER_ADDRESS"),
            "sender_city": data.get("SENDER_CITY"),
            "sender_state": data.get("SENDER_STATE"),
            "sender_pincode": data.get("SENDER_PINCODE"),
            "sender_country_iso": data.get("SENDER_COUNTRY_ISO"),
            "sender_mobile_alt": data.get("SENDER_MOBILE_ALT"),
            "sender_phone": data.get("SENDER_PHONE"),
            "sender_phone_alt": data.get("SENDER_PHONE_ALT"),
            "sender_email_alt": data.get("SENDER_EMAIL_ALT"),
            "query_product_name": data.get("QUERY_PRODUCT_NAME"),
            "query_message": data.get("QUERY_MESSAGE"),
            "query_mcat_name": data.get("QUERY_MCAT_NAME"),
            "call_duration": data.get("CALL_DURATION"),
            "receiver_mobile": data.get("RECEIVER_MOBILE"),
            "receiver_catalog": data.get("RECEIVER_CATALOG"),
        })
        indiamart_lead.insert()
        frappe.db.commit()
        print(f"IndiaMart Lead saved for {data.get('SENDER_NAME')}")
    except Exception as e:
        print(f"Error saving IndiaMart Lead for {data.get('SENDER_NAME')}: {str(e)}")

    # Save data to the Lead doctype in CRM
    url = "http://one.localhost:8000/api/resource/Lead"
    payload = json.dumps({
        "lead_name": data.get("SENDER_NAME"),
        "email_id": data.get("SENDER_EMAIL"),
        "phone": data.get("SENDER_MOBILE"),
        "source": "India Mart",
        "company_name": data.get("SENDER_COMPANY"),
        "city": data.get("SENDER_CITY"),
        "state": data.get("SENDER_STATE"),
        "indiamart_unique_query_id": data.get("UNIQUE_QUERY_ID"),
        "query_type": data.get("QUERY_TYPE"),
        "subject": data.get("SUBJECT"),
        "enquired_product_name": data.get("QUERY_PRODUCT_NAME"),
        "sub_category": data.get("QUERY_MCAT_NAME"),
        "message": data.get("QUERY_MESSAGE"),
    })
    headers = {
        "Authorization": "token fafd6c847e1bcab:1845a7e3472fb50",
        "Content-Type": "application/json",
        "Cookie": "full_name=Guest; sid=Guest; system_user=no; user_id=Guest; user_image="
    }
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            print(f"Success: Lead created for {data.get('SENDER_NAME')}")
        else:
            print(f"Error: Failed to create lead for {data.get('SENDER_NAME')}. Status code: {response.status_code}")
            print("Error Details:", response.text)
    except requests.exceptions.RequestException as e:
        print("Exception:", str(e))

@frappe.whitelist(allow_guest=True)
def fetch_and_create_leads():
    url1 = india_mart_setting.url
    key = india_mart_setting.key
    url = f"{url1}?glusr_crm_key={key}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(data, "Data #########")

            # Loop through each lead in the response and create a lead in CRM
            for lead_data in data.get("RESPONSE", []):
                create_lead_indiamart(lead_data)  # Call create_lead for each entry
                print(lead_data, "creating a lead for indiamart")
        else:
            print(f"Error: Failed to fetch data. Status code: {response.status_code}")
            print("Error Details:", response.text)

    except requests.exceptions.RequestException as e:
        print("Exception:", str(e))

@frappe.whitelist(allow_guest=True)
def webhook_listener():
    try:
        payload = frappe.local.request.get_data(as_text=True)
        data = json.loads(payload)
        print(data,"DATAAAAA ********")

        # Validate payload structure
        if data.get("CODE") != 200 or data.get("STATUS") != "SUCCESS":
            frappe.throw("Invalid webhook payload")

        response_data = data.get("body", {}).get("RESPONSE", {})
        print(response_data,"RESPONSE DATA#########")
        if not response_data:
            frappe.throw("Missing RESPONSE in webhook payload")

        # Extract lead details from webhook response
        create_lead_indiamart(response_data)  # Reuse the existing function to create a lead

        return {"status": "success", "message": "Lead created successfully"}
    except Exception as e:
        frappe.log_error(f"Webhook listener error: {str(e)}", "IndiaMART Webhook")
        return {"status": "error", "message": str(e)}

